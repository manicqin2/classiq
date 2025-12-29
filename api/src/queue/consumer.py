import json
import uuid
from datetime import datetime, timezone
from typing import Callable, Awaitable, Any

import aio_pika
import structlog

from src.queue import get_rabbitmq_channel

logger = structlog.get_logger(__name__)


class QueueConsumer:
    """Consumer for processing messages from RabbitMQ queue."""

    def __init__(self, callback: Callable[[dict[str, Any]], Awaitable[None]]):
        """
        Initialize the QueueConsumer.

        Args:
            callback: Async function to process decoded messages
        """
        self.callback = callback

    async def consume_messages(self) -> None:
        """
        Consume messages from the quantum_tasks queue.

        Gets a RabbitMQ channel, declares the queue, and processes messages
        by calling the callback function. Handles acknowledgments and errors.
        """
        logger.info("Starting message consumer")

        try:
            # Get RabbitMQ channel
            channel = await get_rabbitmq_channel()
            logger.info("Connected to RabbitMQ channel")

            # Declare the queue as durable
            queue = await channel.declare_queue(
                "quantum_tasks",
                durable=True
            )
            logger.info("Declared quantum_tasks queue", queue_name=queue.name)

            # Set prefetch count for fair distribution
            await channel.set_qos(prefetch_count=1)
            logger.info("Set QoS prefetch_count=1")

            # Consume messages using async iterator
            async with queue.iterator() as queue_iter:
                logger.info("Started consuming messages from queue")
                async for message in queue_iter:
                    async with message.process():
                        # Extract or generate correlation ID
                        correlation_id = message.correlation_id or str(uuid.uuid4())

                        # Bind correlation ID to logging context for this message
                        structlog.contextvars.clear_contextvars()
                        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

                        try:
                            # Decode message body
                            message_body = message.body.decode()

                            # Parse JSON message to extract task_id
                            decoded_message = json.loads(message_body)
                            task_id = decoded_message.get("task_id", "unknown")

                            # Log message receipt with full context
                            logger.info(
                                "message_received",
                                task_id=task_id,
                                correlation_id=correlation_id,
                                timestamp=datetime.now(timezone.utc).isoformat(),
                                message_id=message.message_id,
                                queue="quantum_tasks"
                            )

                            # Call callback function with decoded message
                            await self.callback(decoded_message)

                            # Log successful processing and acknowledgment
                            logger.info(
                                "message_acknowledged",
                                task_id=task_id,
                                correlation_id=correlation_id,
                                timestamp=datetime.now(timezone.utc).isoformat(),
                                message_id=message.message_id
                            )
                            # Message is automatically acknowledged when exiting the context manager

                        except json.JSONDecodeError as e:
                            logger.error(
                                "message_rejected_json_error",
                                correlation_id=correlation_id,
                                timestamp=datetime.now(timezone.utc).isoformat(),
                                error=str(e),
                                message_body=message_body,
                                message_id=message.message_id
                            )
                            # Message will be nacked when exception is raised in context manager
                            raise

                        except Exception as e:
                            # Try to extract task_id if available
                            task_id = "unknown"
                            try:
                                decoded_message = json.loads(message.body.decode())
                                task_id = decoded_message.get("task_id", "unknown")
                            except Exception:
                                pass

                            logger.error(
                                "message_rejected_processing_error",
                                task_id=task_id,
                                correlation_id=correlation_id,
                                timestamp=datetime.now(timezone.utc).isoformat(),
                                error=str(e),
                                message_id=message.message_id,
                                error_type=type(e).__name__,
                                exc_info=True
                            )
                            # Message will be nacked when exception is raised in context manager
                            raise

        except Exception as e:
            logger.error(
                "Fatal error in message consumer",
                error=str(e),
                exc_info=True
            )
            raise
