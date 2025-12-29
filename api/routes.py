"""
API route handlers for quantum circuit task management.

All endpoints are stubbed for parallel development - actual task execution
and persistence will be added in future features.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
import aio_pika

from datetime import datetime, timezone

from models import (
    TaskSubmitRequest,
    TaskSubmitResponse,
    TaskStatus,
    TaskStatusResponse,
    StatusHistoryEntry,
    HealthStatus,
    HealthCheckResponse,
)
from middleware import get_correlation_id
from utils import validate_uuid
from src.db.repository import TaskRepository
from src.db.session import get_db
from src.services.task_service import TaskService
from src.queue import check_rabbitmq_health

logger = structlog.get_logger(__name__)

# Create API router
router = APIRouter()


# ===== User Story 1: Task Submission =====

@router.post("/tasks", response_model=TaskSubmitResponse, tags=["tasks"])
async def submit_task(
    request: TaskSubmitRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Submit a quantum circuit task for asynchronous execution.

    Args:
        request: Task submission request with circuit definition
        db: Database session dependency

    Returns:
        Task submission response with task_id and confirmation message

    Raises:
        HTTPException: 503 if database connection fails
    """
    correlation_id = get_correlation_id()

    try:
        # Create task service and submit task (persists to DB and publishes to queue)
        service = TaskService(db)
        task = await service.submit_task(request.circuit, shots=request.shots or 1024)

        logger.info(
            "Task submitted",
            task_id=str(task.task_id),
            circuit_length=len(request.circuit),
            shots=request.shots or 1024,
        )

        return TaskSubmitResponse(
            task_id=str(task.task_id),
            message="Task submitted successfully.",
            submitted_at=task.submitted_at,
            correlation_id=correlation_id,
        )

    except aio_pika.AMQPException as e:
        logger.error(
            "Queue error during task submission",
            error=str(e),
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Service temporarily unavailable. Queue connection failed.",
                "correlation_id": correlation_id,
            }
        )
    except SQLAlchemyError as e:
        logger.error(
            "Database error during task submission",
            error=str(e),
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Service temporarily unavailable. Database connection failed.",
                "correlation_id": correlation_id,
            }
        )


# ===== User Story 2: Task Status Retrieval =====

@router.get("/tasks/{task_id}", response_model=TaskStatusResponse, tags=["tasks"])
async def get_task_status(
    task_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve the status and results of a submitted task.

    Args:
        task_id: Unique task identifier (UUID v4 format)
        db: Database session dependency

    Returns:
        Task status response with current state

    Raises:
        HTTPException: 400 if task_id is not a valid UUID format
        HTTPException: 404 if task not found
        HTTPException: 503 if database connection fails
    """
    # Validate UUID format
    validated_task_id = validate_uuid(task_id)
    correlation_id = get_correlation_id()

    try:
        # Query task from database with status history
        repository = TaskRepository(db)
        task = await repository.get_task_with_history(validated_task_id)

        if task is None:
            logger.warning(
                "Task not found",
                task_id=str(validated_task_id),
            )
            raise HTTPException(
                status_code=404,
                detail={
                    "message": f"Task {task_id} not found.",
                    "correlation_id": correlation_id,
                }
            )

        logger.info(
            "Task status queried",
            task_id=str(validated_task_id),
            status=task.current_status.value,
        )

        # Map database TaskStatus (uppercase) to API TaskStatus (lowercase)
        # Database uses: PENDING, PROCESSING, COMPLETED, FAILED
        # API uses: pending, processing, completed, failed
        api_status = TaskStatus(task.current_status.value.lower())

        # Generate appropriate message based on status
        status_messages = {
            TaskStatus.PENDING: "Task is still in progress.",
            TaskStatus.PROCESSING: "Task is being processed.",
            TaskStatus.COMPLETED: "Task completed successfully.",
            TaskStatus.FAILED: "Task execution failed.",
        }

        # Convert ORM StatusHistory objects to Pydantic StatusHistoryEntry models
        # Sort by transitioned_at ascending (chronological order)
        status_history = [
            StatusHistoryEntry(
                status=TaskStatus(entry.status.value.lower()),
                transitioned_at=entry.transitioned_at,
                notes=entry.notes
            )
            for entry in sorted(task.status_history, key=lambda e: e.transitioned_at)
        ]

        return TaskStatusResponse(
            task_id=str(task.task_id),
            status=api_status,
            submitted_at=task.submitted_at,
            message=status_messages.get(api_status, "Task status unknown."),
            result=task.result,
            status_history=status_history,
            correlation_id=correlation_id,
        )

    except HTTPException:
        # Re-raise HTTP exceptions (404)
        raise
    except SQLAlchemyError as e:
        logger.error(
            "Database error during task status retrieval",
            task_id=str(validated_task_id),
            error=str(e),
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Service temporarily unavailable. Database connection failed.",
                "correlation_id": correlation_id,
            }
        )


# ===== User Story 3: Health Check =====

@router.get("/health", response_model=HealthCheckResponse, tags=["health"])
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint for monitoring and orchestration.

    Checks database and message queue connectivity.

    Args:
        db: Database session dependency

    Returns:
        Health check response with status, timestamp, database status, and queue status
    """
    correlation_id = get_correlation_id()

    # Check database connectivity
    database_status = "disconnected"
    try:
        # Execute simple query to verify database connection
        await db.execute(text("SELECT 1"))
        database_status = "connected"
    except SQLAlchemyError as e:
        logger.error(
            "Health check failed - database unreachable",
            error=str(e),
            correlation_id=correlation_id,
        )

    # Check queue connectivity
    queue_connected = await check_rabbitmq_health()
    queue_status = "connected" if queue_connected else "disconnected"

    # Overall status is healthy only if BOTH db and queue are connected
    overall_status = HealthStatus.HEALTHY if (database_status == "connected" and queue_status == "connected") else HealthStatus.UNHEALTHY

    logger.info(
        "Health check completed",
        database_status=database_status,
        queue_status=queue_status,
        overall_status=overall_status.value,
    )

    return HealthCheckResponse(
        status=overall_status,
        timestamp=datetime.now(timezone.utc).isoformat(),
        database_status=database_status,
        queue_status=queue_status,
    )
