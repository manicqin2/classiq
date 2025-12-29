"""
Worker entrypoint for consuming queue messages and processing quantum tasks.

This worker consumes messages from the RabbitMQ queue, processes quantum circuit
compilation tasks, and updates their status in the database. It implements
idempotency checks and comprehensive error handling.
"""

import asyncio
import signal
import sys
import types
import uuid

import structlog

from qiskit.qasm3 import QASM3ImporterError
from qiskit_aer.aererror import AerError

from db.models import TaskStatus
from db.repository import TaskRepository
from db.session import AsyncSessionLocal, close_db
from messaging.consumer import QueueConsumer
from messaging import cleanup_rabbitmq
from execution.qiskit_validator import validate_qiskit
from execution.qiskit_executor import QiskitExecutor
from execution.result_formatter import ResultFormatter

logger = structlog.get_logger()

# Global shutdown event for coordinating graceful shutdown
_shutdown_event: asyncio.Event | None = None


async def process_task(message: dict[str, object]) -> None:
    """
    Process a quantum circuit compilation task from the queue.

    This function implements the complete task processing lifecycle:
    1. Idempotency check: Skip if already processed
    2. Status transition: PENDING → PROCESSING → COMPLETED
    3. Mock quantum circuit execution with simulated delay
    4. Error handling: Transition to FAILED on exceptions

    Args:
        message: Queue message containing task_id and other metadata

    Requirements:
        - T030: Task processing logic
        - T031: Idempotency check
        - T032: Error handling
    """
    # Extract task_id from message
    task_id_str = message.get("task_id")
    if not task_id_str:
        logger.error("Message missing task_id field", message=message)
        return

    try:
        task_id = uuid.UUID(task_id_str)
    except ValueError as e:
        logger.error(
            "Invalid task_id format",
            task_id=task_id_str,
            error=str(e)
        )
        return

    logger.info("Processing task", task_id=str(task_id))

    # Create database session for this task
    async with AsyncSessionLocal() as session:
        repository = TaskRepository(session)

        try:
            # T031: Idempotency check
            # Get current task status before processing
            task = await repository.get_task(task_id)

            if task is None:
                logger.error("Task not found", task_id=str(task_id))
                return

            # Check if task is already processed or being processed
            if task.current_status in (
                TaskStatus.PROCESSING,
                TaskStatus.COMPLETED,
                TaskStatus.FAILED
            ):
                logger.info(
                    "Task already processed, skipping (idempotent behavior)",
                    task_id=str(task_id),
                    current_status=task.current_status.value
                )
                return

            # T030: Task processing logic
            # Step 1: Transition from PENDING to PROCESSING
            logger.info(
                "Transitioning task to PROCESSING",
                task_id=str(task_id)
            )
            success = await repository.update_task_status(
                task_id=task_id,
                from_status=TaskStatus.PENDING,
                to_status=TaskStatus.PROCESSING,
                notes="Worker started processing"
            )

            if not success:
                logger.warning(
                    "Failed to transition task to PROCESSING (already changed by another worker)",
                    task_id=str(task_id)
                )
                return

            logger.info(
                "Task transitioned to PROCESSING",
                task_id=str(task_id)
            )

            # Step 2: Execute quantum circuit with Qiskit
            # Get circuit and shots from task (T023)
            circuit_string = task.circuit
            shots = task.shots if task.shots else 1024  # Default to 1024 if not specified

            # Initialize executor and formatter
            executor = QiskitExecutor()
            formatter = ResultFormatter()

            # Execute circuit with error handling
            try:
                # Execute circuit with configurable shots (T024, T025, T027)
                logger.info(
                    "Executing quantum circuit with Qiskit",
                    task_id=str(task_id),
                    circuit_length=len(circuit_string),
                    shots=shots
                )

                # Run in thread pool to avoid blocking asyncio loop
                # (Qiskit execution is CPU-bound synchronous operation)
                loop = asyncio.get_event_loop()
                counts = await loop.run_in_executor(
                    None,
                    executor.execute,
                    circuit_string,
                    shots  # Use configured shots parameter
                )

                # Format and validate result
                result = formatter.format_counts(counts)

                logger.info(
                    "Quantum circuit execution completed",
                    task_id=str(task_id),
                    result=result
                )

            except QASM3ImporterError as e:
                # Circuit parse errors
                error_message = formatter.format_error(e, "Circuit parse error")
                logger.error(
                    "Circuit parse error",
                    task_id=str(task_id),
                    error=error_message,
                    exc_info=True
                )

                # Transition to FAILED
                success = await repository.update_task_status(
                    task_id=task_id,
                    from_status=TaskStatus.PROCESSING,
                    to_status=TaskStatus.FAILED,
                    error_message=error_message,
                    notes=f"Circuit parse error: {str(e)}"
                )

                if success:
                    logger.info(
                        "Task transitioned to FAILED due to parse error",
                        task_id=str(task_id)
                    )
                return

            except (AerError, MemoryError) as e:
                # Execution errors: AerError or MemoryError
                error_message = formatter.format_error(e, "Execution error")
                logger.error(
                    "Circuit execution error",
                    task_id=str(task_id),
                    error=error_message,
                    exc_info=True
                )

                # Transition to FAILED
                success = await repository.update_task_status(
                    task_id=task_id,
                    from_status=TaskStatus.PROCESSING,
                    to_status=TaskStatus.FAILED,
                    error_message=error_message,
                    notes=f"Circuit execution error: {str(e)}"
                )

                if success:
                    logger.info(
                        "Task transitioned to FAILED due to execution error",
                        task_id=str(task_id)
                    )
                return

            except Exception as e:
                # Unexpected errors during circuit execution
                error_message = formatter.format_error(e, "Unexpected error")
                logger.error(
                    "Unexpected error during circuit execution",
                    task_id=str(task_id),
                    error=error_message,
                    exc_info=True
                )

                # Transition to FAILED
                success = await repository.update_task_status(
                    task_id=task_id,
                    from_status=TaskStatus.PROCESSING,
                    to_status=TaskStatus.FAILED,
                    error_message=error_message,
                    notes=f"Unexpected error: {str(e)}"
                )

                if success:
                    logger.info(
                        "Task transitioned to FAILED due to unexpected error",
                        task_id=str(task_id)
                    )
                return

            # Step 3: Transition from PROCESSING to COMPLETED
            logger.info(
                "Transitioning task to COMPLETED",
                task_id=str(task_id)
            )
            success = await repository.update_task_status(
                task_id=task_id,
                from_status=TaskStatus.PROCESSING,
                to_status=TaskStatus.COMPLETED,
                result=result,
                notes="Task completed successfully"
            )

            if not success:
                logger.warning(
                    "Failed to transition task to COMPLETED (status changed unexpectedly)",
                    task_id=str(task_id)
                )
                return

            logger.info(
                "Task successfully completed",
                task_id=str(task_id),
                result=result
            )

        except Exception as e:
            # T032: Error handling
            # Catch all exceptions during task execution
            logger.error(
                "Error processing task, transitioning to FAILED",
                task_id=str(task_id),
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )

            try:
                # Attempt to transition to FAILED status
                # Note: We don't know the current status, so try both PENDING and PROCESSING
                success = await repository.update_task_status(
                    task_id=task_id,
                    from_status=TaskStatus.PROCESSING,
                    to_status=TaskStatus.FAILED,
                    error_message=f"{type(e).__name__}: {str(e)}",
                    notes=f"Task failed during processing: {type(e).__name__}: {str(e)}"
                )

                if not success:
                    # Try from PENDING status
                    success = await repository.update_task_status(
                        task_id=task_id,
                        from_status=TaskStatus.PENDING,
                        to_status=TaskStatus.FAILED,
                        error_message=f"{type(e).__name__}: {str(e)}",
                        notes=f"Task failed before processing: {type(e).__name__}: {str(e)}"
                    )

                if success:
                    logger.info(
                        "Task transitioned to FAILED",
                        task_id=str(task_id)
                    )
                else:
                    logger.error(
                        "Failed to transition task to FAILED status",
                        task_id=str(task_id)
                    )

            except Exception as update_error:
                logger.error(
                    "Error updating task status to FAILED",
                    task_id=str(task_id),
                    error=str(update_error),
                    exc_info=True
                )

            # Always acknowledge message (don't requeue on application errors)
            # The message will be acknowledged by the consumer's context manager


def handle_shutdown_signal(signum: int, frame: types.FrameType | None) -> None:
    """
    Signal handler for SIGINT and SIGTERM.

    Sets the global shutdown event to trigger graceful shutdown.

    Args:
        signum: Signal number
        frame: Current stack frame
    """
    signal_name = signal.Signals(signum).name
    logger.info(f"Received {signal_name} signal, initiating graceful shutdown")
    if _shutdown_event:
        _shutdown_event.set()


async def main() -> None:
    """
    Main worker function that starts message consumption.

    This function initializes the QueueConsumer with the process_task callback
    and starts consuming messages indefinitely. It handles graceful shutdown
    on keyboard interrupt and system signals (SIGTERM, SIGINT).

    Graceful shutdown ensures:
    1. In-flight messages are acknowledged before shutdown
    2. Database connections are closed properly
    3. RabbitMQ connections are closed properly

    Requirements:
        - T029: Worker entrypoint
        - T050: Graceful shutdown handling
    """
    global _shutdown_event
    _shutdown_event = asyncio.Event()

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, handle_shutdown_signal)
    signal.signal(signal.SIGTERM, handle_shutdown_signal)

    logger.info("Starting quantum task worker")

    # Validate Qiskit availability before consuming messages
    if not validate_qiskit():
        logger.error("Qiskit validation failed, worker cannot start")
        sys.exit(1)

    logger.info("Graceful shutdown enabled (SIGINT, SIGTERM)")

    # Create consumer with process_task callback
    consumer = QueueConsumer(callback=process_task)

    try:
        # Start consuming messages in a background task
        consume_task = asyncio.create_task(consumer.consume_messages())

        # Wait for either consumption to complete or shutdown signal
        done, pending = await asyncio.wait(
            [consume_task, asyncio.create_task(_shutdown_event.wait())],
            return_when=asyncio.FIRST_COMPLETED
        )

        # If shutdown was triggered, cancel the consumption task
        if _shutdown_event.is_set():
            logger.info("Shutdown signal received, stopping message consumption")

            # Cancel the consume task and wait for it to complete
            if not consume_task.done():
                consume_task.cancel()
                try:
                    await consume_task
                except asyncio.CancelledError:
                    logger.info("Message consumption task cancelled")

            logger.info("All in-flight messages have been acknowledged")

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, stopping worker")
    except Exception as e:
        logger.error(
            "Fatal error in worker",
            error=str(e),
            exc_info=True
        )
        raise
    finally:
        # Cleanup resources
        logger.info("Starting worker cleanup")

        try:
            # Close RabbitMQ connections
            await cleanup_rabbitmq()
            logger.info("RabbitMQ connections closed")
        except Exception as e:
            logger.error(
                "Error during RabbitMQ cleanup",
                error=str(e),
                exc_info=True
            )

        try:
            # Close database connections
            await close_db()
            logger.info("Database connections closed")
        except Exception as e:
            logger.error(
                "Error during database cleanup",
                error=str(e),
                exc_info=True
            )

        logger.info("Worker shutdown complete")


if __name__ == "__main__":
    # T029: Use asyncio.run(main()) for entry point
    asyncio.run(main())
