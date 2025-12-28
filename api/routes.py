"""
API route handlers for quantum circuit task management.

All endpoints are stubbed for parallel development - actual task execution
and persistence will be added in future features.
"""

import uuid

from fastapi import APIRouter
import structlog

from datetime import datetime, timezone

from models import (
    TaskSubmitRequest,
    TaskSubmitResponse,
    TaskStatus,
    TaskStatusResponse,
    HealthStatus,
    HealthCheckResponse,
)
from middleware import get_correlation_id
from utils import validate_uuid

logger = structlog.get_logger(__name__)

# Create API router
router = APIRouter()


# ===== User Story 1: Task Submission =====

@router.post("/tasks", response_model=TaskSubmitResponse, tags=["tasks"])
async def submit_task(request: TaskSubmitRequest):
    """
    Submit a quantum circuit task for asynchronous execution.

    **Stub Behavior:** Generates a UUID for the task but does not persist or execute it.
    Actual task processing will be implemented when database and worker integration is added.

    Args:
        request: Task submission request with circuit definition

    Returns:
        Task submission response with task_id and confirmation message
    """
    # Generate unique task ID
    task_id = str(uuid.uuid4())
    correlation_id = get_correlation_id()

    logger.info(
        "Task submitted",
        task_id=task_id,
        circuit_length=len(request.circuit),
    )

    return TaskSubmitResponse(
        task_id=task_id,
        message="Task submitted successfully.",
        correlation_id=correlation_id,
    )


# ===== User Story 2: Task Status Retrieval =====

@router.get("/tasks/{task_id}", response_model=TaskStatusResponse, tags=["tasks"])
async def get_task_status(task_id: str):
    """
    Retrieve the status and results of a submitted task.

    **Stub Behavior:** Always returns status "pending" for any valid UUID.
    Actual status lookup from database will be implemented in future features.

    Args:
        task_id: Unique task identifier (UUID v4 format)

    Returns:
        Task status response with current state

    Raises:
        HTTPException: 400 if task_id is not a valid UUID format
    """
    # Validate UUID format
    validated_task_id = validate_uuid(task_id)
    correlation_id = get_correlation_id()

    logger.info(
        "Task status queried",
        task_id=validated_task_id,
    )

    # Return stubbed "pending" status
    return TaskStatusResponse(
        status=TaskStatus.PENDING,
        message="Task is still in progress.",
        correlation_id=correlation_id,
    )


# ===== User Story 3: Health Check =====

@router.get("/health", response_model=HealthCheckResponse, tags=["health"])
async def health_check():
    """
    Health check endpoint for monitoring and orchestration.

    **Stub Behavior:** Always returns "healthy" status while server is running.
    Future versions will check database and message queue connectivity.

    Returns:
        Health check response with status and UTC timestamp
    """
    return HealthCheckResponse(
        status=HealthStatus.HEALTHY,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
