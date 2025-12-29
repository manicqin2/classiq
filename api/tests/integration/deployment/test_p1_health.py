"""Priority 1: Service health validation tests.

These tests verify that all system components (API, database, RabbitMQ)
are running and responding correctly.
"""

import pytest
import time


@pytest.mark.p1
@pytest.mark.asyncio
async def test_api_health_check(api_client):
    """Verify API health endpoint responds correctly within timeout."""
    start_time = time.time()
    health = await api_client.check_health()
    response_time = (time.time() - start_time) * 1000

    assert response_time < 2000, f"Health check took {response_time}ms (expected < 2000ms)"
    assert health["status"] == "healthy", f"API status is {health['status']}"
    assert health["database_status"] == "connected", "Database not connected"
    assert health["queue_status"] == "connected", "Queue not connected"


@pytest.mark.p1
@pytest.mark.asyncio
async def test_database_connectivity(db_client):
    """Verify database accepts connections and executes queries."""
    result = await db_client.pool.fetchval("SELECT 1")
    assert result == 1, "Database query failed"


@pytest.mark.p1
@pytest.mark.asyncio
async def test_rabbitmq_connectivity(queue_client):
    """Verify RabbitMQ Management API is accessible."""
    response = await queue_client.http_client.get("/api/queues")
    assert response.status_code == 200, f"RabbitMQ API returned {response.status_code}"
