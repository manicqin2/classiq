"""Priority 2: Queue configuration validation tests.

These tests verify that RabbitMQ is configured correctly with the proper
queues, durability settings, and consumers for quantum task processing.
"""

import pytest


@pytest.mark.p2
@pytest.mark.asyncio
async def test_quantum_tasks_queue_exists(queue_client):
    """Verify quantum_tasks queue exists in RabbitMQ."""
    exists = await queue_client.check_queue_exists("quantum_tasks")
    assert exists, "quantum_tasks queue does not exist"


@pytest.mark.p2
@pytest.mark.asyncio
async def test_quantum_tasks_queue_is_durable(queue_client):
    """Verify quantum_tasks queue is configured as durable.

    Durable queues survive broker restarts, ensuring messages
    are not lost during system failures.
    """
    queue_info = await queue_client.get_queue_info("quantum_tasks")

    assert (
        queue_info["durable"] is True
    ), "quantum_tasks queue is not durable (messages will be lost on restart)"


@pytest.mark.p2
@pytest.mark.asyncio
async def test_quantum_tasks_queue_has_consumers(queue_client):
    """Verify quantum_tasks queue has active consumers (worker running).

    At least one worker should be consuming from the queue in a
    properly deployed environment.
    """
    consumer_count = await queue_client.get_consumer_count("quantum_tasks")

    assert (
        consumer_count > 0
    ), f"quantum_tasks queue has {consumer_count} consumers (expected at least 1 worker)"


@pytest.mark.p2
@pytest.mark.asyncio
async def test_queue_message_persistence(queue_client):
    """Verify messages in quantum_tasks queue are configured for persistence.

    Messages should be marked as persistent to survive broker restarts.
    This is indicated by the 'messages_persistent' metric being non-zero
    if there are messages in the queue, or by checking queue arguments.
    """
    queue_info = await queue_client.get_queue_info("quantum_tasks")

    # Check that queue is durable (prerequisite for message persistence)
    assert queue_info["durable"] is True, "Queue must be durable for messages to be persistent"

    # If there are messages in queue, verify they're persistent
    # Note: Individual message persistence is enforced by publisher
    # (delivery_mode=2), not queue configuration
    # We verify queue durability as a proxy for proper persistence setup
    assert "durable" in queue_info, "Queue info missing durability information"


@pytest.mark.p2
@pytest.mark.asyncio
async def test_queue_auto_delete_disabled(queue_client):
    """Verify quantum_tasks queue is not set to auto-delete.

    Auto-delete queues are removed when the last consumer disconnects,
    which would cause message loss during worker restarts.
    """
    queue_info = await queue_client.get_queue_info("quantum_tasks")

    assert (
        queue_info["auto_delete"] is False
    ), "quantum_tasks queue has auto_delete=true (will be deleted when consumers disconnect)"


@pytest.mark.p2
@pytest.mark.asyncio
async def test_queue_arguments(queue_client):
    """Verify quantum_tasks queue has correct configuration arguments.

    Checks for any custom queue arguments that might affect behavior.
    """
    queue_info = await queue_client.get_queue_info("quantum_tasks")

    # Verify queue exists and has expected fields
    assert "name" in queue_info, "Queue info missing name field"
    assert (
        queue_info["name"] == "quantum_tasks"
    ), f"Queue name is '{queue_info['name']}', expected 'quantum_tasks'"

    # Verify vhost (should be default '/')
    assert queue_info["vhost"] == "/", f"Queue vhost is '{queue_info['vhost']}', expected '/'"

    # Queue arguments should be present (may be empty dict)
    assert "arguments" in queue_info, "Queue info missing arguments field"


@pytest.mark.p2
@pytest.mark.asyncio
async def test_rabbitmq_management_api_accessible(queue_client):
    """Verify RabbitMQ Management API is accessible for monitoring.

    The Management API is used for health checks, monitoring, and
    operational tasks. This test verifies the API endpoint is available.
    """
    # This test verifies we can access the management API
    # by checking the overview endpoint
    response = await queue_client.http_client.get("/api/overview")

    assert (
        response.status_code == 200
    ), f"RabbitMQ Management API returned {response.status_code}, expected 200"

    overview = response.json()
    assert "rabbitmq_version" in overview, "Management API response missing rabbitmq_version"
