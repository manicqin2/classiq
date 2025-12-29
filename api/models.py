"""
Pydantic models for request/response validation.

All models use snake_case naming convention as per project standards.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error response structure for all errors."""

    error: str = Field(..., description="Brief error description")
    details: dict[str, object] | None = Field(
        None, description="Field-specific validation errors (present for 400 errors)"
    )
    correlation_id: str = Field(..., description="Request correlation ID for log tracing")

    class Config:
        json_schema_extra = {
            "example": {
                "error": "Validation failed",
                "details": {"circuit": "Field required"},
                "correlation_id": "abc123-def456",
            }
        }


# ===== User Story 1: Task Submission Models =====

class TaskSubmitRequest(BaseModel):
    """Request model for submitting a quantum circuit task."""

    circuit: str = Field(..., min_length=1, description="Quantum circuit definition")
    shots: int | None = Field(
        1024,
        ge=1,
        le=100000,
        description="Number of circuit executions (default: 1024, range: 1-100,000)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "circuit": "OPENQASM 3; qubit q; h q; measure q;",
                "shots": 1024
            }
        }


class TaskSubmitResponse(BaseModel):
    """Response model after successful task submission."""

    task_id: str = Field(..., description="Unique identifier for the submitted task")
    message: str = Field(..., description="Human-readable confirmation message")
    submitted_at: datetime = Field(..., description="Task submission timestamp in ISO 8601 format")
    correlation_id: str = Field(..., description="Request correlation ID for tracing")

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "message": "Task submitted successfully.",
                "submitted_at": "2025-12-28T14:30:00.123Z",
                "correlation_id": "abc123-def456-789012",
            }
        }


# ===== User Story 2: Task Status Models =====

class TaskStatus(str, Enum):
    """Enum for task status values."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class StatusHistoryEntry(BaseModel):
    """Model representing a single status history entry."""

    status: TaskStatus = Field(..., description="Task status at this point in time")
    transitioned_at: datetime = Field(..., description="Timestamp when this status was recorded in ISO 8601 format")
    notes: str | None = Field(None, description="Optional notes about the status transition")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "pending",
                "transitioned_at": "2025-12-28T14:30:00.123Z",
                "notes": "Task created"
            }
        }


class TaskStatusResponse(BaseModel):
    """Response model for task status query."""

    task_id: str = Field(..., description="Unique identifier for the task")
    status: TaskStatus = Field(..., description="Current task state")
    submitted_at: datetime = Field(..., description="Task submission timestamp in ISO 8601 format")
    message: str | None = Field(
        None, description="Human-readable status description (present for pending/failed states)"
    )
    result: dict[str, object] | None = Field(
        None, description="Task execution results (present only for completed tasks)"
    )
    status_history: list[StatusHistoryEntry] = Field(
        ..., description="Chronological list of status transitions for this task"
    )
    correlation_id: str = Field(..., description="Request correlation ID for tracing")

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "pending",
                "submitted_at": "2025-12-28T14:30:00.123Z",
                "message": "Task is still in progress.",
                "status_history": [
                    {
                        "status": "pending",
                        "transitioned_at": "2025-12-28T14:30:00.123Z",
                        "notes": "Task created"
                    }
                ],
                "correlation_id": "xyz789-uvw456",
            }
        }


# ===== User Story 3: Health Check Models =====

class HealthStatus(str, Enum):
    """Enum for health status values."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class HealthCheckResponse(BaseModel):
    """Response model for health check endpoint."""

    status: HealthStatus = Field(..., description="Service health status")
    timestamp: str = Field(..., description="UTC timestamp of health check in ISO 8601 format")
    database_status: str | None = Field(
        None, description="Database connectivity status (connected/disconnected)"
    )
    queue_status: str | None = Field(
        None, description="Message queue connectivity status (connected/disconnected)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2025-12-28T12:00:00Z",
                "database_status": "connected",
                "queue_status": "connected",
            }
        }
