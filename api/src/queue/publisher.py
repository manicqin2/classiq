"""
RabbitMQ task publisher module.

Provides async task publishing capabilities for the quantum tasks queue.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

import aio_pika
import structlog

from src.queue import get_rabbitmq_channel

logger = structlog.get_logger(__name__)


def _get_correlation_id() -> str:
    """
    Get correlation ID from context or generate a new one.

    Attempts to extract correlation_id from structlog context.
    If not available, generates a new UUID.

    Returns:
        str: Correlation ID for message tracking
    """
    try:
        # Try to get correlation_id from structlog context
        from api.middleware import get_correlation_id
        correlation_id = get_correlation_id()
        if correlation_id:
            return correlation_id
    except (ImportError, Exception):
        pass

    # Generate new correlation ID if not in context
    return str(uuid.uuid4())


class QueuePublisher:
    """
    Publisher for quantum task messages to RabbitMQ.

    Handles publishing task messages to the quantum_tasks queue with
    proper error handling, persistence, and logging.
    """

    def __init__(self, channel: Optional[aio_pika.Channel] = None):
        """
        Initialize the QueuePublisher.

        Args:
            channel: Optional RabbitMQ channel. If not provided, will be
                    obtained via get_rabbitmq_channel() when needed.
        """
        self._channel = channel

    async def publish_task_message(self, task_id: UUID, circuit: str) -> bool:
        """
        Publish a task message to the quantum_tasks queue.

        Creates a JSON message containing the task_id and circuit, and publishes
        it to the quantum_tasks queue with durability and persistence settings
        to ensure message reliability.

        Args:
            task_id: UUID of the task to be processed
            circuit: Circuit definition/code to be executed

        Returns:
            bool: True if message was published successfully, False otherwise

        Example:
            >>> publisher = QueuePublisher()
            >>> task_id = uuid.uuid4()
            >>> success = await publisher.publish_task_message(
            ...     task_id=task_id,
            ...     circuit="qc = QuantumCircuit(2)"
            ... )
        """
        # Get or generate correlation ID for tracking
        correlation_id = _get_correlation_id()
        circuit_length = len(circuit)
        timestamp = datetime.now(timezone.utc).isoformat()

        # Log before publishing
        logger.info(
            "publish_start",
            task_id=str(task_id),
            circuit_length=circuit_length,
            correlation_id=correlation_id,
            timestamp=timestamp,
            queue="quantum_tasks"
        )

        try:
            # Get channel if not provided in constructor
            if self._channel is None:
                self._channel = await get_rabbitmq_channel()

            # Declare queue with durability to survive broker restarts
            queue = await self._channel.declare_queue(
                "quantum_tasks",
                durable=True
            )

            # Create message payload
            message_data = {
                "task_id": str(task_id),
                "circuit": circuit
            }
            message_body = json.dumps(message_data).encode()

            # Create message with persistence and correlation ID
            message = aio_pika.Message(
                body=message_body,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,  # delivery_mode=2
                content_type="application/json",
                message_id=str(uuid.uuid4()),
                correlation_id=correlation_id,  # Add correlation ID for tracking
                timestamp=datetime.now(timezone.utc)
            )

            # Publish message to the queue
            await self._channel.default_exchange.publish(
                message,
                routing_key=queue.name
            )

            # Log successful publish
            logger.info(
                "publish_success",
                task_id=str(task_id),
                circuit_length=circuit_length,
                correlation_id=correlation_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                queue="quantum_tasks",
                message_id=message.message_id
            )

            return True

        except aio_pika.exceptions.AMQPConnectionError as e:
            logger.error(
                "publish_error_connection",
                task_id=str(task_id),
                circuit_length=circuit_length,
                correlation_id=correlation_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                error=str(e),
                error_type="connection_error"
            )
            return False

        except aio_pika.exceptions.AMQPChannelError as e:
            logger.error(
                "publish_error_channel",
                task_id=str(task_id),
                circuit_length=circuit_length,
                correlation_id=correlation_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                error=str(e),
                error_type="channel_error"
            )
            return False

        except Exception as e:
            logger.error(
                "publish_error_unexpected",
                task_id=str(task_id),
                circuit_length=circuit_length,
                correlation_id=correlation_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                error=str(e),
                error_type=type(e).__name__
            )
            return False


__all__ = ["QueuePublisher"]
