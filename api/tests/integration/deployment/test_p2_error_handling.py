"""Priority 2: API error handling validation tests.

These tests verify that the API properly validates inputs and returns
appropriate error responses with correct HTTP status codes and messages.
"""

import httpx
import pytest


def has_error_info(response_data):
    """Check if response contains error information in any common format."""
    return (
        "detail" in response_data
        or "details" in response_data
        or "error" in response_data
        or "message" in response_data
    )


@pytest.mark.p2
@pytest.mark.asyncio
async def test_submit_task_with_empty_circuit(api_client):
    """Test that submitting a task with empty circuit returns 400 Bad Request."""
    try:
        response = await api_client.client.post("/tasks", json={"circuit": ""})
        # Should get 400 or 422 (Unprocessable Entity)
        assert response.status_code in [
            400,
            422,
        ], f"Expected 400/422 for empty circuit, got {response.status_code}"

        error_data = response.json()
        assert has_error_info(error_data), "Error response missing error information"

    except httpx.HTTPStatusError as e:
        # If client raises error, verify it's the expected status
        assert e.response.status_code in [
            400,
            422,
        ], f"Expected 400/422 for empty circuit, got {e.response.status_code}"


@pytest.mark.p2
@pytest.mark.asyncio
async def test_submit_task_missing_circuit_field(api_client):
    """Test that submitting a task without circuit field returns 400/422."""
    try:
        response = await api_client.client.post("/tasks", json={"not_circuit": "some value"})
        assert response.status_code in [
            400,
            422,
        ], f"Expected 400/422 for missing circuit field, got {response.status_code}"

        error_data = response.json()
        assert has_error_info(error_data), "Error response missing error information"

    except httpx.HTTPStatusError as e:
        assert e.response.status_code in [
            400,
            422,
        ], f"Expected 400/422 for missing circuit field, got {e.response.status_code}"


@pytest.mark.p2
@pytest.mark.asyncio
async def test_submit_task_with_invalid_json(api_client):
    """Test that submitting invalid JSON returns 400/422."""
    try:
        response = await api_client.client.post(
            "/tasks", content="this is not json", headers={"Content-Type": "application/json"}
        )
        assert response.status_code in [
            400,
            422,
        ], f"Expected 400/422 for invalid JSON, got {response.status_code}"

    except httpx.HTTPStatusError as e:
        assert e.response.status_code in [
            400,
            422,
        ], f"Expected 400/422 for invalid JSON, got {e.response.status_code}"


@pytest.mark.p2
@pytest.mark.asyncio
async def test_get_task_status_nonexistent_task(api_client):
    """Test that querying status for non-existent task returns 404 Not Found."""
    # Use a valid UUID format that doesn't exist in database
    nonexistent_task_id = "00000000-0000-0000-0000-000000000000"

    try:
        response = await api_client.client.get(f"/tasks/{nonexistent_task_id}")
        assert (
            response.status_code == 404
        ), f"Expected 404 for non-existent task, got {response.status_code}"

        error_data = response.json()
        assert has_error_info(error_data), "Error response missing error information"

        # Check for "not found" message in any error field
        error_text = str(error_data).lower()
        assert (
            "not found" in error_text
        ), f"Error message should mention 'not found', got: {error_data}"

    except httpx.HTTPStatusError as e:
        assert (
            e.response.status_code == 404
        ), f"Expected 404 for non-existent task, got {e.response.status_code}"


@pytest.mark.p2
@pytest.mark.asyncio
async def test_get_task_status_invalid_uuid_format(api_client):
    """Test that querying status with invalid UUID format returns 400/422."""
    invalid_task_ids = [
        "not-a-uuid",
        "12345",
        "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    ]

    for invalid_id in invalid_task_ids:
        try:
            response = await api_client.client.get(f"/tasks/{invalid_id}")
            # Should get 400 or 422 for invalid UUID format
            # Some frameworks may return 404 for invalid path params
            assert response.status_code in [
                400,
                422,
                404,
            ], f"Expected 400/422/404 for invalid UUID '{invalid_id}', got {response.status_code}"

            error_data = response.json()
            assert has_error_info(
                error_data
            ), f"Error response missing error information for UUID '{invalid_id}'"

        except httpx.HTTPStatusError as e:
            assert e.response.status_code in [
                400,
                422,
                404,
            ], f"Expected 400/422/404 for invalid UUID '{invalid_id}', got {e.response.status_code}"


@pytest.mark.p2
@pytest.mark.asyncio
async def test_error_response_includes_details(api_client):
    """Test that error responses include helpful detail messages.

    Verify that validation errors provide enough information for
    clients to understand and fix the problem.
    """
    # Test with missing circuit field
    try:
        response = await api_client.client.post("/tasks", json={})
        error_data = response.json()

        # Verify error information exists and is informative
        assert has_error_info(error_data), "Error response missing error information"

        # Get the error content (could be detail, details, error, or message)
        error_content = (
            error_data.get("detail")
            or error_data.get("details")
            or error_data.get("error")
            or error_data.get("message")
        )

        # Error content should be either a string or a dict with information
        if isinstance(error_content, str):
            assert len(error_content) > 0, "Error message is empty"
        elif isinstance(error_content, dict):
            assert len(error_content) > 0, "Error details are empty"
        elif isinstance(error_content, list):
            # FastAPI validation errors return list of error objects
            assert len(error_content) > 0, "Error list is empty"
        else:
            # Some other error format is acceptable as long as it has error info
            assert has_error_info(error_data), f"Unexpected error format: {type(error_content)}"

    except httpx.HTTPStatusError as e:
        # If error was raised, verify response has error information
        error_data = e.response.json()
        assert has_error_info(error_data), "Error response missing error information"


@pytest.mark.p2
@pytest.mark.asyncio
async def test_unsupported_http_methods(api_client):
    """Test that unsupported HTTP methods return 405 Method Not Allowed."""
    # Try PUT on /tasks (only POST should be supported)
    try:
        response = await api_client.client.put("/tasks", json={"circuit": "test"})
        assert (
            response.status_code == 405
        ), f"Expected 405 for PUT /tasks, got {response.status_code}"
    except httpx.HTTPStatusError as e:
        assert (
            e.response.status_code == 405
        ), f"Expected 405 for PUT /tasks, got {e.response.status_code}"

    # Try POST on /tasks/{task_id} (only GET should be supported)
    try:
        response = await api_client.client.post(
            "/tasks/00000000-0000-0000-0000-000000000000", json={}
        )
        assert (
            response.status_code == 405
        ), f"Expected 405 for POST /tasks/{{id}}, got {response.status_code}"
    except httpx.HTTPStatusError as e:
        assert (
            e.response.status_code == 405
        ), f"Expected 405 for POST /tasks/{{id}}, got {e.response.status_code}"


@pytest.mark.p2
@pytest.mark.asyncio
async def test_nonexistent_endpoint_returns_404(api_client):
    """Test that accessing non-existent endpoints returns 404."""
    try:
        response = await api_client.client.get("/nonexistent/endpoint")
        assert (
            response.status_code == 404
        ), f"Expected 404 for non-existent endpoint, got {response.status_code}"
    except httpx.HTTPStatusError as e:
        assert (
            e.response.status_code == 404
        ), f"Expected 404 for non-existent endpoint, got {e.response.status_code}"
