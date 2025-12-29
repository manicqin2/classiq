"""
Integration test for the quantum task worker.

This test verifies that the worker correctly consumes messages from RabbitMQ,
processes tasks, and updates the database with proper status transitions.

Test Scenario:
1. Connect to database and RabbitMQ
2. Create a task directly in database (bypass API) with status=pending
3. Publish message to quantum_tasks queue with task_id and circuit
4. Wait up to 30 seconds for worker to process
5. Poll database every 2 seconds checking task status
6. Verify status transitions: pending → processing → completed
7. Verify status_history has 3 entries with correct timestamps
8. Verify result field is populated (non-null)
9. Clean up: close connections

Requirements:
- T049: Integration test for worker message consumption and status updates
"""

import asyncio
import json
import os
import uuid
from datetime import datetime
from typing import Optional

import aio_pika
import asyncpg
import pytest

# Test configuration from environment variables with defaults
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/quantum_circuits"
)
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")

# Test constants
QUEUE_NAME = "quantum_tasks"
POLL_INTERVAL = 2  # seconds
MAX_WAIT_TIME = 30  # seconds
TEST_CIRCUIT = """
from qiskit import QuantumCircuit
qc = QuantumCircuit(2)
qc.h(0)
qc.cx(0, 1)
"""


@pytest.mark.asyncio
async def test_worker_processes_task_and_updates_status():
    """
    Test that the worker consumes messages and updates task status correctly.

    This integration test verifies the complete task processing flow:
    - Message consumption from RabbitMQ queue
    - Database status transitions (PENDING → PROCESSING → COMPLETED)
    - Status history tracking with timestamps
    - Result population upon completion

    The test assumes a worker process is running in the background.
    """
    db_conn = None
    rabbitmq_connection = None
    rabbitmq_channel = None
    task_id = None

    try:
        # Step 1: Connect to database
        print(f"Connecting to database: {DATABASE_URL}")
        db_conn = await asyncpg.connect(DATABASE_URL)
        assert db_conn is not None, "Failed to connect to database"
        print("✓ Database connection established")

        # Step 2: Connect to RabbitMQ
        print(f"Connecting to RabbitMQ: {RABBITMQ_URL}")
        rabbitmq_connection = await aio_pika.connect_robust(RABBITMQ_URL)
        assert rabbitmq_connection is not None, "Failed to connect to RabbitMQ"
        rabbitmq_channel = await rabbitmq_connection.channel()
        assert rabbitmq_channel is not None, "Failed to create RabbitMQ channel"
        print("✓ RabbitMQ connection established")

        # Step 3: Create a task directly in database with status=pending
        task_id = uuid.uuid4()
        print(f"Creating task in database: {task_id}")

        await db_conn.execute(
            """
            INSERT INTO tasks (task_id, circuit, current_status, submitted_at)
            VALUES ($1, $2, $3, NOW())
            """,
            task_id,
            TEST_CIRCUIT,
            "PENDING",
        )

        # Create initial status history entry
        await db_conn.execute(
            """
            INSERT INTO status_history (task_id, status, transitioned_at, notes)
            VALUES ($1, $2, NOW(), $3)
            """,
            task_id,
            "PENDING",
            "Task created for integration test",
        )

        # Verify task was created
        task_record = await db_conn.fetchrow(
            "SELECT task_id, current_status FROM tasks WHERE task_id = $1", task_id
        )
        assert task_record is not None, "Task was not created in database"
        assert task_record["current_status"] == "PENDING", "Task status should be PENDING"
        print(f"✓ Task created with status PENDING: {task_id}")

        # Step 4: Publish message to quantum_tasks queue
        print("Declaring queue and publishing message")
        queue = await rabbitmq_channel.declare_queue(QUEUE_NAME, durable=True)

        message_data = {"task_id": str(task_id), "circuit": TEST_CIRCUIT}
        message_body = json.dumps(message_data).encode()

        message = aio_pika.Message(
            body=message_body,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            content_type="application/json",
            message_id=str(uuid.uuid4()),
        )

        await rabbitmq_channel.default_exchange.publish(message, routing_key=QUEUE_NAME)
        print(f"✓ Message published to queue: {QUEUE_NAME}")

        # Step 5: Wait up to 30 seconds for worker to process
        # Step 6: Poll database every 2 seconds checking task status
        print(f"Polling database every {POLL_INTERVAL}s for up to {MAX_WAIT_TIME}s...")

        start_time = asyncio.get_event_loop().time()
        task_completed = False
        final_status = None

        while (asyncio.get_event_loop().time() - start_time) < MAX_WAIT_TIME:
            # Query current task status
            task_record = await db_conn.fetchrow(
                "SELECT current_status, result, error_message FROM tasks WHERE task_id = $1",
                task_id,
            )

            if task_record:
                current_status = task_record["current_status"]
                print(f"  Current status: {current_status}")

                # Check if task reached terminal state
                if current_status == "COMPLETED":
                    task_completed = True
                    final_status = current_status
                    print(f"✓ Task completed successfully")
                    break
                elif current_status == "FAILED":
                    error_msg = task_record["error_message"]
                    pytest.fail(f"Task transitioned to FAILED status. Error: {error_msg}")

            # Wait before next poll
            await asyncio.sleep(POLL_INTERVAL)

        # Verify task completed within timeout
        assert task_completed, (
            f"Task did not complete within {MAX_WAIT_TIME} seconds. "
            f"Final status: {final_status or 'Unknown'}. "
            "Ensure the worker is running."
        )

        # Step 7: Verify status transitions: pending → processing → completed
        print("Verifying status history...")
        status_history = await db_conn.fetch(
            """
            SELECT status, transitioned_at, notes
            FROM status_history
            WHERE task_id = $1
            ORDER BY transitioned_at ASC
            """,
            task_id,
        )

        # Verify we have exactly 3 status history entries
        assert len(status_history) == 3, (
            f"Expected 3 status history entries, got {len(status_history)}. "
            f"Entries: {[record['status'] for record in status_history]}"
        )
        print(f"✓ Found {len(status_history)} status history entries")

        # Verify status transitions are in correct order
        expected_statuses = ["PENDING", "PROCESSING", "COMPLETED"]
        actual_statuses = [record["status"] for record in status_history]
        assert actual_statuses == expected_statuses, (
            f"Status transitions incorrect. Expected {expected_statuses}, " f"got {actual_statuses}"
        )
        print(f"✓ Status transitions verified: {' → '.join(actual_statuses)}")

        # Step 8: Verify status_history has 3 entries with correct timestamps
        print("Verifying timestamps are in ascending order...")
        for i in range(len(status_history) - 1):
            current_time = status_history[i]["transitioned_at"]
            next_time = status_history[i + 1]["transitioned_at"]
            assert current_time < next_time, (
                f"Timestamps not in ascending order: "
                f"{status_history[i]['status']} at {current_time} >= "
                f"{status_history[i + 1]['status']} at {next_time}"
            )
        print("✓ Timestamps are in correct chronological order")

        # Verify notes are populated
        for i, record in enumerate(status_history):
            assert (
                record["notes"] is not None and len(record["notes"]) > 0
            ), f"Status history entry {i} ({record['status']}) missing notes"
        print("✓ All status history entries have notes")

        # Step 9: Verify result field is populated (non-null)
        print("Verifying task result...")
        final_task = await db_conn.fetchrow(
            "SELECT result, completed_at FROM tasks WHERE task_id = $1", task_id
        )

        assert final_task is not None, "Task not found in final verification"
        assert final_task["result"] is not None, "Task result is NULL"
        assert isinstance(final_task["result"], dict), "Task result is not a dictionary"
        assert len(final_task["result"]) > 0, "Task result is empty"
        print(f"✓ Task result populated: {final_task['result']}")

        # Verify completed_at is set
        assert final_task["completed_at"] is not None, "completed_at is NULL"
        assert isinstance(final_task["completed_at"], datetime), "completed_at is not a datetime"
        print(f"✓ Task completed_at set: {final_task['completed_at']}")

        # All assertions passed
        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
        print(f"Task ID: {task_id}")
        print(f"Status transitions: {' → '.join(actual_statuses)}")
        print(f"Result: {final_task['result']}")
        print(f"Completed at: {final_task['completed_at']}")
        print("=" * 60)

    except AssertionError:
        # Re-raise assertion errors from pytest
        raise

    except Exception as e:
        pytest.fail(f"Unexpected error during test: {type(e).__name__}: {str(e)}")

    finally:
        # Step 10: Clean up - close connections
        print("\nCleaning up connections...")

        # Clean up test data from database
        if db_conn and task_id:
            try:
                # Delete status history first (foreign key constraint)
                await db_conn.execute("DELETE FROM status_history WHERE task_id = $1", task_id)
                # Delete task
                await db_conn.execute("DELETE FROM tasks WHERE task_id = $1", task_id)
                print(f"✓ Cleaned up test task: {task_id}")
            except Exception as e:
                print(f"Warning: Failed to clean up test data: {e}")

        # Close database connection
        if db_conn:
            try:
                await db_conn.close()
                print("✓ Database connection closed")
            except Exception as e:
                print(f"Warning: Error closing database connection: {e}")

        # Close RabbitMQ connections
        if rabbitmq_channel:
            try:
                await rabbitmq_channel.close()
                print("✓ RabbitMQ channel closed")
            except Exception as e:
                print(f"Warning: Error closing RabbitMQ channel: {e}")

        if rabbitmq_connection:
            try:
                await rabbitmq_connection.close()
                print("✓ RabbitMQ connection closed")
            except Exception as e:
                print(f"Warning: Error closing RabbitMQ connection: {e}")


if __name__ == "__main__":
    """
    Allow running the test standalone without pytest.

    Usage:
        python test-worker.py

    Or with pytest:
        pytest test-worker.py -v
        pytest test-worker.py -v -s  # with output
    """
    print("Running worker integration test...")
    print(f"Database URL: {DATABASE_URL}")
    print(f"RabbitMQ URL: {RABBITMQ_URL}")
    print()

    # Run the test
    asyncio.run(test_worker_processes_task_and_updates_status())
