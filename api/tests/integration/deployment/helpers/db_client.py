"""Database validation helper for integration tests."""

import asyncpg


class DatabaseClient:
    """Database validation helper for integration tests."""

    def __init__(self, connection_url: str):
        self.connection_url = connection_url
        self.pool: asyncpg.Pool | None = None

    async def connect(self):
        """Establish database connection pool."""
        self.pool = await asyncpg.create_pool(self.connection_url)

    async def check_table_exists(self, table_name: str) -> bool:
        """Check if table exists in database.

        Args:
            table_name: Name of the table to check

        Returns:
            True if table exists, False otherwise
        """
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name=$1)",
                table_name
            )
            return result

    async def get_task(self, task_id: str) -> dict[str, object] | None:
        """Get task by ID from database.

        Args:
            task_id: Task UUID string

        Returns:
            Dict with task data if found, None otherwise
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM tasks WHERE task_id = $1::uuid",
                task_id
            )
            return dict(row) if row else None

    async def get_status_history(self, task_id: str) -> list[dict[str, object]]:
        """Get status history for task.

        Args:
            task_id: Task UUID string

        Returns:
            List of status history entries ordered by transitioned_at
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM status_history WHERE task_id = $1::uuid ORDER BY transitioned_at",
                task_id
            )
            return [dict(row) for row in rows]

    async def close(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
