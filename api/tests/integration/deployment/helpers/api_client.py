"""HTTP client wrapper for API interaction in tests."""

import httpx


class APIClient:
    """HTTP client wrapper for API interaction in tests."""

    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=base_url, timeout=timeout)

    async def submit_task(self, circuit: str) -> dict[str, object]:
        """Submit quantum circuit task.

        Args:
            circuit: OpenQASM 3 circuit string

        Returns:
            Dict with task_id, message, submitted_at, correlation_id

        Raises:
            httpx.HTTPStatusError: If API returns error status
        """
        response = await self.client.post("/tasks", json={"circuit": circuit})
        response.raise_for_status()
        return response.json()

    async def get_task_status(self, task_id: str) -> dict[str, object]:
        """Get task status by ID.

        Args:
            task_id: Task UUID string

        Returns:
            Dict with task status, result, history, etc.

        Raises:
            httpx.HTTPStatusError: If API returns error status
        """
        response = await self.client.get(f"/tasks/{task_id}")
        response.raise_for_status()
        return response.json()

    async def check_health(self) -> dict[str, object]:
        """Check API health endpoint.

        Returns:
            Dict with status, timestamp, database_status, queue_status

        Raises:
            httpx.HTTPStatusError: If API returns error status
        """
        response = await self.client.get("/health")
        response.raise_for_status()
        return response.json()

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
