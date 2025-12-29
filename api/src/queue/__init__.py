"""
RabbitMQ connection manager module.

Provides async connection management for RabbitMQ with:
- Robust connection with automatic reconnection
- Connection retry logic with exponential backoff
- Health check capabilities
- Graceful shutdown support
"""

import asyncio
import logging
from typing import Optional

import aio_pika
from aio_pika import Connection, Channel
from aio_pika.abc import AbstractRobustConnection

from config import settings

logger = logging.getLogger(__name__)

# Global connection and channel instances
_connection: Optional[AbstractRobustConnection] = None
_channel: Optional[Channel] = None


async def get_rabbitmq_connection(
    max_retries: int = 5,
    initial_retry_delay: float = 1.0,
    max_retry_delay: float = 60.0,
    backoff_factor: float = 2.0,
) -> AbstractRobustConnection:
    """
    Get or create a robust RabbitMQ connection with retry logic.

    Uses exponential backoff for connection retries. The connection is cached
    globally and reused across calls.

    Args:
        max_retries: Maximum number of connection attempts (default: 5)
        initial_retry_delay: Initial delay between retries in seconds (default: 1.0)
        max_retry_delay: Maximum delay between retries in seconds (default: 60.0)
        backoff_factor: Multiplier for exponential backoff (default: 2.0)

    Returns:
        AbstractRobustConnection: A robust RabbitMQ connection

    Raises:
        ConnectionError: If connection fails after all retries
    """
    global _connection

    # Return existing connection if available and not closed
    if _connection is not None and not _connection.is_closed:
        return _connection

    retry_delay = initial_retry_delay
    last_exception = None

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(
                f"Attempting to connect to RabbitMQ (attempt {attempt}/{max_retries}): {settings.rabbitmq_url}"
            )

            # Create robust connection with automatic reconnection
            _connection = await aio_pika.connect_robust(
                settings.rabbitmq_url,
                timeout=10.0,
            )

            # Set up connection close callback
            _connection.close_callbacks.add(lambda sender, exc: _on_connection_closed(exc))

            logger.info("Successfully connected to RabbitMQ")
            return _connection

        except Exception as e:
            last_exception = e
            logger.warning(
                f"Failed to connect to RabbitMQ (attempt {attempt}/{max_retries}): {str(e)}"
            )

            if attempt < max_retries:
                logger.info(f"Retrying in {retry_delay:.2f} seconds...")
                await asyncio.sleep(retry_delay)
                # Exponential backoff with max cap
                retry_delay = min(retry_delay * backoff_factor, max_retry_delay)
            else:
                logger.error(
                    f"Failed to connect to RabbitMQ after {max_retries} attempts"
                )
                raise ConnectionError(
                    f"Could not establish RabbitMQ connection after {max_retries} attempts: {str(last_exception)}"
                ) from last_exception

    # This should never be reached, but just in case
    raise ConnectionError("Unexpected error in connection retry logic")


async def get_rabbitmq_channel() -> Channel:
    """
    Get or create a RabbitMQ channel from the global connection.

    Automatically creates a connection if one doesn't exist. The channel is cached
    globally and reused across calls.

    Returns:
        Channel: A RabbitMQ channel

    Raises:
        ConnectionError: If connection cannot be established
        RuntimeError: If channel creation fails
    """
    global _channel

    # Return existing channel if available and not closed
    if _channel is not None and not _channel.is_closed:
        return _channel

    try:
        # Ensure we have a connection
        connection = await get_rabbitmq_connection()

        # Create a new channel
        logger.info("Creating new RabbitMQ channel")
        _channel = await connection.channel()

        # Set QoS for the channel (useful for consumers)
        await _channel.set_qos(prefetch_count=10)

        logger.info("Successfully created RabbitMQ channel")
        return _channel

    except Exception as e:
        logger.error(f"Failed to create RabbitMQ channel: {str(e)}")
        raise RuntimeError(f"Could not create RabbitMQ channel: {str(e)}") from e


async def check_rabbitmq_health() -> bool:
    """
    Check if RabbitMQ connection is healthy.

    Returns:
        bool: True if connection is healthy, False otherwise
    """
    global _connection

    try:
        # Check if connection exists and is not closed
        if _connection is None or _connection.is_closed:
            logger.warning("RabbitMQ health check failed: No active connection")
            return False

        # Try to create a temporary channel to verify connection is working
        try:
            test_channel = await _connection.channel()
            await test_channel.close()
            logger.debug("RabbitMQ health check passed")
            return True
        except Exception as e:
            logger.warning(f"RabbitMQ health check failed during channel test: {str(e)}")
            return False

    except Exception as e:
        logger.error(f"RabbitMQ health check failed with unexpected error: {str(e)}")
        return False


async def close_rabbitmq_channel() -> None:
    """
    Close the global RabbitMQ channel gracefully.

    Safe to call even if channel is already closed or doesn't exist.
    """
    global _channel

    if _channel is not None and not _channel.is_closed:
        try:
            logger.info("Closing RabbitMQ channel")
            await _channel.close()
            logger.info("RabbitMQ channel closed successfully")
        except Exception as e:
            logger.warning(f"Error closing RabbitMQ channel: {str(e)}")
        finally:
            _channel = None
    else:
        logger.debug("RabbitMQ channel already closed or does not exist")
        _channel = None


async def close_rabbitmq_connection() -> None:
    """
    Close the global RabbitMQ connection gracefully.

    Automatically closes the channel first if it exists. Safe to call even if
    connection is already closed or doesn't exist.
    """
    global _connection

    # Close channel first
    await close_rabbitmq_channel()

    if _connection is not None and not _connection.is_closed:
        try:
            logger.info("Closing RabbitMQ connection")
            await _connection.close()
            logger.info("RabbitMQ connection closed successfully")
        except Exception as e:
            logger.warning(f"Error closing RabbitMQ connection: {str(e)}")
        finally:
            _connection = None
    else:
        logger.debug("RabbitMQ connection already closed or does not exist")
        _connection = None


async def cleanup_rabbitmq() -> None:
    """
    Cleanup all RabbitMQ resources gracefully.

    This is the recommended function to call during application shutdown.
    Closes both channel and connection in the proper order.
    """
    logger.info("Starting RabbitMQ cleanup")
    await close_rabbitmq_connection()
    logger.info("RabbitMQ cleanup completed")


def _on_connection_closed(exception: Optional[Exception]) -> None:
    """
    Callback for when connection is closed.

    Args:
        exception: Exception that caused the closure, if any
    """
    if exception:
        logger.error(f"RabbitMQ connection closed with error: {str(exception)}")
    else:
        logger.info("RabbitMQ connection closed normally")


# Export public API
__all__ = [
    "get_rabbitmq_connection",
    "get_rabbitmq_channel",
    "check_rabbitmq_health",
    "close_rabbitmq_channel",
    "close_rabbitmq_connection",
    "cleanup_rabbitmq",
]
