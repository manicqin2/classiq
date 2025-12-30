"""RabbitMQ inspection helper for integration tests."""

import httpx


class QueueClient:
    """RabbitMQ inspection helper for integration tests."""

    def __init__(self, rabbitmq_url: str, mgmt_url: str, mgmt_user: str, mgmt_pass: str):
        self.rabbitmq_url = rabbitmq_url
        self.mgmt_url = mgmt_url
        self.mgmt_auth = httpx.BasicAuth(mgmt_user, mgmt_pass)
        self.http_client = httpx.AsyncClient(base_url=mgmt_url, auth=self.mgmt_auth)

    async def get_queue_info(self, queue_name: str) -> dict[str, object]:
        """Get queue metadata from RabbitMQ Management API.

        Args:
            queue_name: Name of the queue

        Returns:
            Dict with queue metadata (messages, consumers, durable, etc.)

        Raises:
            httpx.HTTPStatusError: If queue not found or API error
        """
        response = await self.http_client.get(f"/api/queues/%2F/{queue_name}")
        response.raise_for_status()
        return response.json()

    async def check_queue_exists(self, queue_name: str) -> bool:
        """Check if queue exists.

        Args:
            queue_name: Name of the queue

        Returns:
            True if queue exists, False if 404
        """
        try:
            await self.get_queue_info(queue_name)
            return True
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return False
            raise

    async def get_consumer_count(self, queue_name: str) -> int:
        """Get number of active consumers for queue.

        Args:
            queue_name: Name of the queue

        Returns:
            Number of active consumers
        """
        info = await self.get_queue_info(queue_name)
        return info.get("consumers", 0)

    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()
