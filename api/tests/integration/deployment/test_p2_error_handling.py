"""Priority 2: API error handling validation tests.

These tests verify that the API properly validates inputs and returns
appropriate error responses with correct HTTP status codes and messages.
"""

import pytest
import httpx


@pytest.mark.p2
@pytest.mark.asyncio
async def test_submit_task_with_empty_circuit(api_client):
    """Test that submitting a task with empty circuit returns 400 Bad Request."""
    try:
        response = await api_client.client.post(
            "/tasks",
            json={"circuit": ""}
        )
        # Should get 400 or 422 (Unprocessable Entity)
        assert response.status_code in [400, 422], \
            f"Expected 400/422 for empty circuit, got {response.status_code}"

        error_data = response.json()
        assert "detail" in error_data, "Error response missing 'detail' field"

    except httpx.HTTPStatusError as e:
        # If client raises error, verify it's the expected status
        assert e.response.status_code in [400, 422], \
            f"Expected 400/422 for empty circuit, got {e.response.status_code}"


@pytest.mark.p2
@pytest.mark.asyncio
async def test_submit_task_missing_circuit_field(api_client):
    """Test that submitting a task without circuit field returns 400/422."""
    try:
        response = await api_client.client.post(
            "/tasks",
            json={"not_circuit": "some value"}
        )
        assert response.status_code in [400, 422], \
            f"Expected 400/422 for missing circuit field, got {response.status_code}"

        error_data = response.json()
        assert "detail" in error_data, "Error response missing 'detail' field"

    except httpx.HTTPStatusError as e:
        assert e.response.status_code in [400, 422], \
            f"Expected 400/422 for missing circuit field, got {e.response.status_code}"


@pytest.mark.p2
@pytest.mark.asyncio
async def test_submit_task_with_invalid_json(api_client):
    """Test that submitting invalid JSON returns 400/422."""
    try:
        response = await api_client.client.post(
            "/tasks",
            content="this is not json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code in [400, 422], \
            f"Expected 400/422 for invalid JSON, got {response.status_code}"

    except httpx.HTTPStatusError as e:
        assert e.response.status_code in [400, 422], \
            f"Expected 400/422 for invalid JSON, got {e.response.status_code}"


@pytest.mark.p2
@pytest.mark.asyncio
async def test_get_task_status_nonexistent_task(api_client):
    """Test that querying status for non-existent task returns 404 Not Found."""
    # Use a valid UUID format that doesn't exist in database
    nonexistent_task_id = "00000000-0000-0000-0000-000000000000"

    try:
        response = await api_client.client.get(f"/tasks/{nonexistent_task_id}")
        assert response.status_code == 404, \
            f"Expected 404 for non-existent task, got {response.status_code}"

        error_data = response.json()
        assert "detail" in error_data, "Error response missing 'detail' field"
        assert "not found" in error_data["detail"].lower(), \
            f"Error message should mention 'not found', got: {error_data['detail']}"

    except httpx.HTTPStatusError as e:
        assert e.response.status_code == 404, \
            f"Expected 404 for non-existent task, got {e.response.status_code}"


@pytest.mark.p2
@pytest.mark.asyncio
async def test_get_task_status_invalid_uuid_format(api_client):
    """Test that querying status with invalid UUID format returns 400/422."""
    invalid_task_ids = [
        "not-a-uuid",
        "12345",
        "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        ""
    ]

    for invalid_id in invalid_task_ids:
        try:
            response = await api_client.client.get(f"/tasks/{invalid_id}")
            # Should get 400 or 422 for invalid UUID format
            assert response.status_code in [400, 422], \
                f"Expected 400/422 for invalid UUID '{invalid_id}', got {response.status_code}"

            error_data = response.json()
            assert "detail" in error_data, \
                f"Error response missing 'detail' field for UUID '{invalid_id}'"

        except httpx.HTTPStatusError as e:
            assert e.response.status_code in [400, 422], \
                f"Expected 400/422 for invalid UUID '{invalid_id}', got {e.response.status_code}"


@pytest.mark.p2
@pytest.mark.asyncio
async def test_error_response_includes_details(api_client):
    """Test that error responses include helpful detail messages.

    Verify that validation errors provide enough information for
    clients to understand and fix the problem.
    """
    # Test with missing circuit field
    try:
        response = await api_client.client.post(
            "/tasks",
            json={}
        )
        error_data = response.json()

        # Verify detail field exists and is informative
        assert "detail" in error_data, "Error response missing 'detail' field"

        detail = error_data["detail"]

        # Detail should be either a string or a list of validation errors
        if isinstance(detail, str):
            assert len(detail) > 0, "Detail message is empty"
        elif isinstance(detail, list):
            # FastAPI validation errors return list of error objects
            assert len(detail) > 0, "Detail list is empty"
            # Each error should have type, loc, and msg
            for error in detail:
                assert "type" in error or "msg" in error, \
                    f"Validation error missing required fields: {error}"
        else:
            pytest.fail(f"Unexpected detail type: {type(detail)}")

    except httpx.HTTPStatusError as e:
        # If error was raised, verify response has detail
        error_data = e.response.json()
        assert "detail" in error_data, "Error response missing 'detail' field"


@pytest.mark.p2
@pytest.mark.asyncio
async def test_unsupported_http_methods(api_client):
    """Test that unsupported HTTP methods return 405 Method Not Allowed."""
    # Try PUT on /tasks (only POST should be supported)
    try:
        response = await api_client.client.put(
            "/tasks",
            json={"circuit": "test"}
        )
        assert response.status_code == 405, \
            f"Expected 405 for PUT /tasks, got {response.status_code}"
    except httpx.HTTPStatusError as e:
        assert e.response.status_code == 405, \
            f"Expected 405 for PUT /tasks, got {e.response.status_code}"

    # Try POST on /tasks/{task_id} (only GET should be supported)
    try:
        response = await api_client.client.post(
            "/tasks/00000000-0000-0000-0000-000000000000",
            json={}
        )
        assert response.status_code == 405, \
            f"Expected 405 for POST /tasks/{{id}}, got {response.status_code}"
    except httpx.HTTPStatusError as e:
        assert e.response.status_code == 405, \
            f"Expected 405 for POST /tasks/{{id}}, got {e.response.status_code}"


@pytest.mark.p2
@pytest.mark.asyncio
async def test_nonexistent_endpoint_returns_404(api_client):
    """Test that accessing non-existent endpoints returns 404."""
    try:
        response = await api_client.client.get("/nonexistent/endpoint")
        assert response.status_code == 404, \
            f"Expected 404 for non-existent endpoint, got {response.status_code}"
    except httpx.HTTPStatusError as e:
        assert e.response.status_code == 404, \
            f"Expected 404 for non-existent endpoint, got {e.response.status_code}"
