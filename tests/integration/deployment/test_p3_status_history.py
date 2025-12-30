"""
Priority 3: Task Status History Tracking Tests

Tests that verify status history tracking functionality as defined in:
Feature Specification: Persistence Layer and Message Queue Integration
User Story 3 - Task Status History Tracking (Priority: P3)

These tests verify that each state transition is recorded with a timestamp,
providing visibility into task lifecycle and helping diagnose processing delays.
"""

import asyncio
import time
from datetime import datetime, timedelta, timezone

import pytest

from tests.integration.deployment.helpers.api_client import APIClient
from tests.integration.deployment.helpers.db_client import DatabaseClient


@pytest.mark.p3
class TestStatusHistoryTracking:
    """Test suite for task status history tracking functionality."""

    @pytest.mark.asyncio
    async def test_initial_status_history_on_submission(
        self, api_client: APIClient, db_client: DatabaseClient
    ):
        """
        Test that a newly submitted task has initial status history entry.

        Acceptance Scenario 1:
        Given: A task has been submitted
        When: Retrieving task details
        Then: The response includes a status history showing when the task was created
        """
        # Submit a task
        circuit = 'OPENQASM 3.0;\ninclude "stdgates.inc";\nqubit q;\nbit c;\nh q;\nc = measure q;'
        response = await api_client.submit_task(circuit, shots=100)

        task_id = response["task_id"]

        # Get task status
        status_response = await api_client.get_task_status(task_id)

        assert "status_history" in status_response
        history = status_response["status_history"]

        # Verify initial status history
        assert len(history) >= 1, "Should have at least one history entry"

        first_entry = history[0]
        assert first_entry["status"] == "pending"
        assert "transitioned_at" in first_entry
        assert "notes" in first_entry

        # Verify timestamp is valid ISO format
        transition_time = datetime.fromisoformat(
            first_entry["transitioned_at"].replace("Z", "+00:00")
        )
        assert transition_time.tzinfo is not None, "Timestamp should include timezone"

    @pytest.mark.asyncio
    async def test_status_history_shows_pending_to_processing_transition(
        self, api_client: APIClient, db_client: DatabaseClient
    ):
        """
        Test that status history captures pending → processing transition.

        Acceptance Scenario 2:
        Given: A task transitions from "pending" to "processing"
        When: Retrieving task details
        Then: The status history shows both states with their respective timestamps
        """
        # Submit a task
        circuit = 'OPENQASM 3.0;\ninclude "stdgates.inc";\nqubit q;\nbit c;\nx q;\nc = measure q;'
        response = await api_client.submit_task(circuit, shots=50)

        task_id = response["task_id"]

        # Poll until task is processing or completed
        max_wait = 15
        start_time = time.time()
        found_processing = False

        while time.time() - start_time < max_wait:
            status_response = await api_client.get_task_status(task_id)

            current_status = status_response["status"]

            if current_status in ["processing", "completed"]:
                history = status_response["status_history"]

                # Find pending and processing entries
                pending_entry = next((h for h in history if h["status"] == "pending"), None)
                processing_entry = next(
                    (h for h in history if h["status"] == "processing"), None
                )

                if pending_entry and processing_entry:
                    found_processing = True

                    # Verify both entries exist
                    assert pending_entry is not None, "Should have pending status in history"
                    assert processing_entry is not None, "Should have processing status in history"

                    # Verify timestamps
                    pending_time = datetime.fromisoformat(
                        pending_entry["transitioned_at"].replace("Z", "+00:00")
                    )
                    processing_time = datetime.fromisoformat(
                        processing_entry["transitioned_at"].replace("Z", "+00:00")
                    )

                    # Processing should come after pending
                    assert (
                        processing_time >= pending_time
                    ), "Processing transition should occur after pending"

                    # Verify notes
                    assert "notes" in pending_entry
                    assert "notes" in processing_entry

                    break

            if current_status == "completed":
                # Task completed, check if we captured processing
                break

            await asyncio.sleep(0.5)

        assert (
            found_processing
        ), "Should have found both pending and processing states in history"

    @pytest.mark.asyncio
    async def test_status_history_shows_complete_lifecycle(
        self, api_client: APIClient, db_client: DatabaseClient
    ):
        """
        Test that status history shows complete task lifecycle.

        Acceptance Scenario 3:
        Given: A task completes successfully
        When: Retrieving task details
        Then: The status history shows the complete lifecycle from submission to final state
        """
        # Submit a simple deterministic task
        circuit = 'OPENQASM 3.0;\ninclude "stdgates.inc";\nqubit q;\nbit c;\nx q;\nc = measure q;'
        response = await api_client.submit_task(circuit, shots=100)

        task_id = response["task_id"]

        # Wait for completion
        max_wait = 15
        start_time = time.time()
        completed = False

        while time.time() - start_time < max_wait:
            status_response = await api_client.get_task_status(task_id)

            if status_response["status"] == "completed":
                completed = True

                history = status_response["status_history"]

                # Verify we have all three states
                statuses = [h["status"] for h in history]
                assert "pending" in statuses, "Should have pending state"
                assert "processing" in statuses, "Should have processing state"
                assert "completed" in statuses, "Should have completed state"

                # Verify chronological order
                pending_entry = next(h for h in history if h["status"] == "pending")
                processing_entry = next(h for h in history if h["status"] == "processing")
                completed_entry = next(h for h in history if h["status"] == "completed")

                pending_time = datetime.fromisoformat(
                    pending_entry["transitioned_at"].replace("Z", "+00:00")
                )
                processing_time = datetime.fromisoformat(
                    processing_entry["transitioned_at"].replace("Z", "+00:00")
                )
                completed_time = datetime.fromisoformat(
                    completed_entry["transitioned_at"].replace("Z", "+00:00")
                )

                assert pending_time <= processing_time <= completed_time, (
                    "Status transitions should be in chronological order"
                )

                # Verify all entries have required fields
                for entry in history:
                    assert "status" in entry
                    assert "transitioned_at" in entry
                    assert "notes" in entry

                break

            await asyncio.sleep(0.5)

        assert completed, "Task should complete within timeout"

    @pytest.mark.asyncio
    async def test_status_history_shows_failure_lifecycle(
        self, api_client: APIClient, db_client: DatabaseClient
    ):
        """
        Test that status history tracks failed task lifecycle.

        This verifies that failures are also properly tracked in status history.
        """
        # Submit an invalid circuit that will fail
        invalid_circuit = "INVALID QASM SYNTAX HERE"
        response = await api_client.submit_task(invalid_circuit, shots=100)

        task_id = response["task_id"]

        # Wait for failure
        max_wait = 15
        start_time = time.time()
        failed = False

        while time.time() - start_time < max_wait:
            status_response = await api_client.get_task_status(task_id)

            if status_response["status"] == "failed":
                failed = True

                history = status_response["status_history"]

                # Verify we have pending and failed states
                statuses = [h["status"] for h in history]
                assert "pending" in statuses, "Should have pending state"
                assert "failed" in statuses, "Should have failed state"

                # May or may not have processing depending on when failure occurred
                # But we should definitely have at least 2 states

                assert len(history) >= 2, "Should have at least pending and failed states"

                # Verify chronological order
                pending_entry = next(h for h in history if h["status"] == "pending")
                failed_entry = next(h for h in history if h["status"] == "failed")

                pending_time = datetime.fromisoformat(
                    pending_entry["transitioned_at"].replace("Z", "+00:00")
                )
                failed_time = datetime.fromisoformat(
                    failed_entry["transitioned_at"].replace("Z", "+00:00")
                )

                assert (
                    pending_time <= failed_time
                ), "Failed transition should occur after pending"

                break

            await asyncio.sleep(0.5)

        assert failed, "Task should fail within timeout"

    @pytest.mark.asyncio
    async def test_status_history_persistence_across_queries(
        self, api_client: APIClient, db_client: DatabaseClient
    ):
        """
        Test that status history is consistently returned across multiple queries.

        Verifies that history is persisted and doesn't change on repeated reads.
        """
        # Submit a task
        circuit = 'OPENQASM 3.0;\ninclude "stdgates.inc";\nqubit q;\nbit c;\nh q;\nc = measure q;'
        response = await api_client.submit_task(circuit, shots=100)

        task_id = response["task_id"]

        # Wait for completion
        max_wait = 15
        start_time = time.time()

        while time.time() - start_time < max_wait:
            status_response = await api_client.get_task_status(task_id)
            if status_response["status"] == "completed":
                break
            await asyncio.sleep(0.5)

        # Query multiple times and verify history is consistent
        first_query = await api_client.get_task_status(task_id)
        await asyncio.sleep(1)
        second_query = await api_client.get_task_status(task_id)
        await asyncio.sleep(1)
        third_query = await api_client.get_task_status(task_id)

        first_history = first_query["status_history"]
        second_history = second_query["status_history"]
        third_history = third_query["status_history"]

        # All queries should return the same history
        assert len(first_history) == len(
            second_history
        ), "History length should be consistent"
        assert len(second_history) == len(
            third_history
        ), "History length should be consistent"

        # Compare timestamps to ensure they're identical
        for i, entry in enumerate(first_history):
            assert (
                entry["transitioned_at"] == second_history[i]["transitioned_at"]
            ), "Timestamps should be identical"
            assert (
                entry["status"] == second_history[i]["status"]
            ), "Statuses should be identical"

    @pytest.mark.asyncio
    async def test_status_history_timestamps_are_realistic(
        self, api_client: APIClient, db_client: DatabaseClient
    ):
        """
        Test that status history timestamps are realistic and properly ordered.

        Verifies that timestamps are within reasonable bounds and show expected
        processing time patterns.
        """
        # Submit a task and record submission time
        before_submit = datetime.now(timezone.utc)

        circuit = 'OPENQASM 3.0;\ninclude "stdgates.inc";\nqubit q;\nbit c;\nx q;\nc = measure q;'
        response = await api_client.submit_task(circuit, shots=100)

        after_submit = datetime.now(timezone.utc)

        task_id = response["task_id"]

        # Wait for completion
        max_wait = 15
        start_time = time.time()

        while time.time() - start_time < max_wait:
            status_response = await api_client.get_task_status(task_id)
            if status_response["status"] in ["completed", "failed"]:
                break
            await asyncio.sleep(0.5)

        after_complete = datetime.now(timezone.utc)

        # Get final status
        final_status = await api_client.get_task_status(task_id)
        history = final_status["status_history"]

        # Verify all timestamps are within the test execution window
        for entry in history:
            timestamp = datetime.fromisoformat(entry["transitioned_at"].replace("Z", "+00:00"))

            # Timestamp should be after we started the test
            assert (
                timestamp >= before_submit - timedelta(seconds=5)  # Allow 5 second clock skew tolerance
            ), f"Timestamp {timestamp} should be after submission {before_submit}"

            # Timestamp should be before we completed verification
            assert (
                timestamp <= after_complete + timedelta(seconds=5)  # Allow 5 second clock skew tolerance
            ), f"Timestamp {timestamp} should be before completion {after_complete}"

        # Verify processing time is reasonable (should be < 15 seconds for simple circuit)
        if len(history) >= 2:
            first_time = datetime.fromisoformat(history[0]["transitioned_at"].replace("Z", "+00:00"))
            last_time = datetime.fromisoformat(
                history[-1]["transitioned_at"].replace("Z", "+00:00")
            )

            processing_duration = (last_time - first_time).total_seconds()
            assert (
                processing_duration < 15
            ), "Processing should complete within 15 seconds for simple circuit"

    @pytest.mark.asyncio
    async def test_multiple_tasks_have_independent_status_histories(
        self, api_client: APIClient, db_client: DatabaseClient
    ):
        """
        Test that different tasks maintain independent status histories.

        Verifies that status history tracking doesn't mix data between tasks.
        """
        # Submit two tasks
        circuit1 = 'OPENQASM 3.0;\ninclude "stdgates.inc";\nqubit q;\nbit c;\nh q;\nc = measure q;'
        circuit2 = 'OPENQASM 3.0;\ninclude "stdgates.inc";\nqubit q;\nbit c;\nx q;\nc = measure q;'

        response1 = await api_client.submit_task(circuit1, shots=100)
        response2 = await api_client.submit_task(circuit2, shots=50)

        task_id1 = response1["task_id"]
        task_id2 = response2["task_id"]

        # Ensure they're different tasks
        assert task_id1 != task_id2

        # Wait for both to complete
        max_wait = 15
        start_time = time.time()

        while time.time() - start_time < max_wait:
            status1 = await api_client.get_task_status(task_id1)
            status2 = await api_client.get_task_status(task_id2)

            if (
                status1["status"] in ["completed", "failed"]
                and status2["status"] in ["completed", "failed"]
            ):
                break

            await asyncio.sleep(0.5)

        # Get final status for both
        final1 = await api_client.get_task_status(task_id1)
        final2 = await api_client.get_task_status(task_id2)

        history1 = final1["status_history"]
        history2 = final2["status_history"]

        # Both should have history
        assert len(history1) >= 2, "Task 1 should have status history"
        assert len(history2) >= 2, "Task 2 should have status history"

        # Histories should be independent (timestamps will differ)
        # At least one timestamp should be different between the two histories
        timestamps1 = [h["transitioned_at"] for h in history1]
        timestamps2 = [h["transitioned_at"] for h in history2]

        # Since tasks are submitted at different times, at least pending timestamps should differ
        assert (
            timestamps1[0] != timestamps2[0]
        ), "Different tasks should have different submission timestamps"
