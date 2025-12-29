"""Priority 1: End-to-end task processing workflow tests.

These tests verify the complete task lifecycle from submission through
worker processing to completion.
"""

import pytest
import asyncio


BELL_STATE_CIRCUIT = """OPENQASM 3;
include "stdgates.inc";
qubit[2] q;
bit[2] c;
h q[0];
cx q[0], q[1];
c[0] = measure q[0];
c[1] = measure q[1];"""


@pytest.mark.p1
@pytest.mark.asyncio
async def test_complete_task_workflow(api_client, db_client, cleanup_test_tasks, test_config):
    """Test end-to-end task submission and processing workflow."""

    # 1. Submit task via API
    submit_response = await api_client.submit_task(BELL_STATE_CIRCUIT)
    task_id = submit_response["task_id"]
    cleanup_test_tasks(task_id)  # Register for cleanup

    assert task_id, "Task ID not returned in response"
    assert submit_response["message"] == "Task submitted successfully."

    # 2. Verify task persisted to database
    task = await db_client.get_task(task_id)
    assert task is not None, f"Task {task_id} not found in database"
    # Task may already be processing if worker is very fast, accept pending or processing
    assert task["current_status"] in ["pending", "processing"], \
        f"Expected 'pending' or 'processing', got '{task['current_status']}'"
    assert task["circuit"] == BELL_STATE_CIRCUIT

    # 3. Wait for worker to process task (polling with timeout)
    max_wait = test_config["timeout"]
    poll_interval = test_config["poll_interval"]
    elapsed = 0
    final_status = None

    while elapsed < max_wait:
        status_response = await api_client.get_task_status(task_id)
        if status_response["status"] in ["completed", "failed"]:
            final_status = status_response
            break
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval

    assert final_status is not None, f"Task did not complete within {max_wait}s"
    assert final_status["status"] == "completed", \
        f"Task failed with status: {final_status.get('status')}, message: {final_status.get('message')}"

    # 4. Verify results stored correctly
    assert "result" in final_status, "No result in completed task"
    result = final_status["result"]
    assert isinstance(result, dict), f"Result is not a dict: {type(result)}"
    assert len(result) > 0, "Result is empty"

    # 5. Verify status history recorded
    history = await db_client.get_status_history(task_id)
    assert len(history) >= 3, f"Expected at least 3 status transitions, got {len(history)}"

    statuses = [h["status"] for h in history]
    assert "pending" in statuses, "Missing 'pending' status in history"
    assert "processing" in statuses, "Missing 'processing' status in history"
    assert "completed" in statuses, "Missing 'completed' status in history"

    # Verify chronological order
    for i in range(len(history) - 1):
        assert history[i]["transitioned_at"] <= history[i+1]["transitioned_at"], \
            "Status history not in chronological order"
