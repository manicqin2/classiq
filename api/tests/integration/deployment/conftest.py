"""Shared pytest fixtures for deployment integration tests."""

import os
import pytest
from typing import List


@pytest.fixture(scope="session")
def test_config():
    """Load test configuration from environment variables."""
    return {
        "api_url": os.getenv("TEST_API_URL", "http://localhost:8001"),
        "db_url": os.getenv(
            "TEST_DATABASE_URL",
            "postgresql://quantum_user:quantum_pass@localhost:5432/quantum_db"
        ),
        "rabbitmq_url": os.getenv(
            "TEST_RABBITMQ_URL",
            "amqp://quantum_user:quantum_pass@localhost:5672/"
        ),
        "rabbitmq_mgmt_url": os.getenv("TEST_RABBITMQ_MGMT_URL", "http://localhost:15672"),
        "rabbitmq_user": os.getenv("TEST_RABBITMQ_MGMT_USER", "guest"),
        "rabbitmq_pass": os.getenv("TEST_RABBITMQ_MGMT_PASS", "guest"),
        "timeout": int(os.getenv("TEST_TIMEOUT", "30")),
        "poll_interval": float(os.getenv("TEST_POLL_INTERVAL", "0.5")),
    }


@pytest.fixture
async def cleanup_test_tasks(test_config):
    """Track and cleanup test tasks after each test."""
    from tests.integration.deployment.helpers.db_client import DatabaseClient

    test_task_ids: List[str] = []

    def register_task(task_id: str) -> str:
        """Register a task ID for cleanup."""
        test_task_ids.append(task_id)
        return task_id

    yield register_task

    # Cleanup after test (runs even if test fails)
    if test_task_ids:
        db_client = DatabaseClient(test_config["db_url"])
        await db_client.connect()

        try:
            async with db_client.pool.acquire() as conn:
                for task_id in test_task_ids:
                    # Delete status history first (foreign key constraint)
                    await conn.execute(
                        "DELETE FROM status_history WHERE task_id = $1::uuid",
                        task_id
                    )
                    # Then delete task
                    await conn.execute(
                        "DELETE FROM tasks WHERE task_id = $1::uuid",
                        task_id
                    )
        finally:
            await db_client.close()


@pytest.fixture
async def api_client(test_config):
    """Provide API client instance."""
    from tests.integration.deployment.helpers.api_client import APIClient

    client = APIClient(test_config["api_url"])
    yield client
    await client.close()


@pytest.fixture
async def db_client(test_config):
    """Provide database client instance."""
    from tests.integration.deployment.helpers.db_client import DatabaseClient

    client = DatabaseClient(test_config["db_url"])
    await client.connect()
    yield client
    await client.close()


@pytest.fixture
async def queue_client(test_config):
    """Provide queue client instance."""
    from tests.integration.deployment.helpers.queue_client import QueueClient

    client = QueueClient(
        test_config["rabbitmq_url"],
        test_config["rabbitmq_mgmt_url"],
        test_config["rabbitmq_user"],
        test_config["rabbitmq_pass"]
    )
    yield client
    await client.close()
