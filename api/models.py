"""
Pydantic models for request/response validation.

All models use snake_case naming convention as per project standards.
"""

from typing import Optional, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error response structure for all errors."""

    error: str = Field(..., description="Brief error description")
    details: Optional[Dict[str, Any]] = Field(
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

    class Config:
        json_schema_extra = {
            "example": {"circuit": "OPENQASM 3; qubit q; h q; measure q;"}
        }


class TaskSubmitResponse(BaseModel):
    """Response model after successful task submission."""

    task_id: str = Field(..., description="Unique identifier for the submitted task")
    message: str = Field(..., description="Human-readable confirmation message")
    correlation_id: str = Field(..., description="Request correlation ID for tracing")

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "message": "Task submitted successfully.",
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


class TaskStatusResponse(BaseModel):
    """Response model for task status query."""

    status: TaskStatus = Field(..., description="Current task state")
    message: Optional[str] = Field(
        None, description="Human-readable status description (present for pending/failed states)"
    )
    result: Optional[Dict[str, Any]] = Field(
        None, description="Task execution results (present only for completed tasks)"
    )
    correlation_id: str = Field(..., description="Request correlation ID for tracing")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "pending",
                "message": "Task is still in progress.",
                "correlation_id": "xyz789-uvw456",
            }
        }


# ===== User Story 3: Health Check Models =====

class HealthStatus(str, Enum):
    """Enum for health status values."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class HealthCheckResponse(BaseModel):
    """Response model for health check endpoint."""

    status: HealthStatus = Field(..., description="Service health status")
    timestamp: str = Field(..., description="UTC timestamp of health check in ISO 8601 format")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2025-12-28T12:00:00Z",
            }
        }
