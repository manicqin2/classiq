# Data Model: Standalone API Server

**Created:** 2025-12-28
**Feature:** Standalone API Server with Docker Setup
**Purpose:** Define request/response schemas and validation rules

---

## Overview

This document defines all data structures used in the API, including request payloads, response formats, and validation rules. Since this is a stubbed implementation with no persistence, entities are ephemeral and generated on-demand.

---

## Request Models

### TaskSubmitRequest

**Purpose:** Payload for submitting a quantum circuit task

**Fields:**

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `circuit` | string | Yes | Non-empty string | Quantum circuit definition in text format (QASM3 or other) |

**Validation Rules:**
- `circuit` must be present (required field)
- `circuit` must be a string type
- `circuit` must contain at least 1 character (non-empty)
- `circuit` format validation deferred to future feature (accept any non-empty string for now)

**Example:**
```json
{
  "circuit": "OPENQASM 3; qubit q; h q; measure q;"
}
```

**Pydantic Model (Python):**
```python
from pydantic import BaseModel, Field

class TaskSubmitRequest(BaseModel):
    circuit: str = Field(..., min_length=1, description="Quantum circuit definition")

    class Config:
        json_schema_extra = {
            "example": {
                "circuit": "OPENQASM 3; qubit q; h q; measure q;"
            }
        }
```

---

## Response Models

### TaskSubmitResponse

**Purpose:** Response after successful task submission

**Fields:**

| Field | Type | Always Present | Description |
|-------|------|----------------|-------------|
| `task_id` | string (UUID v4) | Yes | Unique identifier for the submitted task |
| `message` | string | Yes | Human-readable confirmation message |
| `correlation_id` | string (UUID v4) | Yes | Request correlation ID for tracing |

**Example:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Task submitted successfully.",
  "correlation_id": "abc123-def456-789012"
}
```

**Pydantic Model (Python):**
```python
from pydantic import BaseModel
from uuid import UUID

class TaskSubmitResponse(BaseModel):
    task_id: str  # UUID v4 as string
    message: str
    correlation_id: str

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "message": "Task submitted successfully.",
                "correlation_id": "abc123-def456-789012"
            }
        }
```

---

### TaskStatusResponse

**Purpose:** Response for task status query

**Fields:**

| Field | Type | Always Present | Description |
|-------|------|----------------|-------------|
| `status` | string (enum) | Yes | Current task state: "pending", "processing", "completed", "failed" |
| `message` | string | No | Human-readable status description (present when status is "pending" or "failed") |
| `result` | object | No | Task execution results (present only when status is "completed") |
| `correlation_id` | string (UUID v4) | Yes | Request correlation ID for tracing |

**Status Values:**
- `"pending"`: Task submitted but not yet processed
- `"processing"`: Task currently being executed (future state)
- `"completed"`: Task execution finished successfully
- `"failed"`: Task execution failed (future state)

**Stub Behavior:**
- All task IDs return status `"pending"` with message "Task is still in progress."
- Future implementation will return actual status from database

**Example (Pending):**
```json
{
  "status": "pending",
  "message": "Task is still in progress.",
  "correlation_id": "xyz789-uvw456-123789"
}
```

**Example (Completed - Stub):**
```json
{
  "status": "completed",
  "result": {"0": 512, "1": 512},
  "correlation_id": "xyz789-uvw456-123789"
}
```

**Pydantic Model (Python):**
```python
from pydantic import BaseModel
from typing import Optional, Dict, Any
from enum import Enum

class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskStatusResponse(BaseModel):
    status: TaskStatus
    message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    correlation_id: str

    class Config:
        json_schema_extra = {
            "example": {
                "status": "pending",
                "message": "Task is still in progress.",
                "correlation_id": "xyz789-uvw456-123789"
            }
        }
```

---

### HealthCheckResponse

**Purpose:** Health check status indicator

**Fields:**

| Field | Type | Always Present | Description |
|-------|------|----------------|-------------|
| `status` | string (enum) | Yes | Service health: "healthy", "degraded", "unavailable" |
| `timestamp` | string (ISO 8601) | Yes | UTC timestamp of health check |

**Status Values:**
- `"healthy"`: Service is fully operational
- `"degraded"`: Service is operational but experiencing issues (future)
- `"unavailable"`: Service cannot process requests (future)

**Stub Behavior:**
- Always returns `"healthy"` while server is running

**Example:**
```json
{
  "status": "healthy",
  "timestamp": "2025-12-28T12:00:00Z"
}
```

**Pydantic Model (Python):**
```python
from pydantic import BaseModel
from enum import Enum
from datetime import datetime

class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"

class HealthCheckResponse(BaseModel):
    status: HealthStatus
    timestamp: str  # ISO 8601 UTC

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2025-12-28T12:00:00Z"
            }
        }
```

---

### ErrorResponse

**Purpose:** Standard error response structure for all errors

**Fields:**

| Field | Type | Always Present | Description |
|-------|------|----------------|-------------|
| `error` | string | Yes | Brief error description |
| `details` | object | No | Field-specific validation errors (present for 400 validation errors) |
| `correlation_id` | string (UUID v4) | Yes | Request correlation ID for log tracing |

**Error Types:**

**400 Bad Request - Validation Error:**
```json
{
  "error": "Validation failed",
  "details": {
    "circuit": "Field required"
  },
  "correlation_id": "abc123-def456"
}
```

**400 Bad Request - Invalid Format:**
```json
{
  "error": "Invalid task ID format. Expected UUID.",
  "correlation_id": "abc123-def456"
}
```

**404 Not Found:**
```json
{
  "error": "Task not found.",
  "correlation_id": "abc123-def456"
}
```

**500 Internal Server Error:**
```json
{
  "error": "Internal server error",
  "correlation_id": "abc123-def456"
}
```

**Pydantic Model (Python):**
```python
from pydantic import BaseModel
from typing import Optional, Dict, Any

class ErrorResponse(BaseModel):
    error: str
    details: Optional[Dict[str, Any]] = None
    correlation_id: str

    class Config:
        json_schema_extra = {
            "example": {
                "error": "Validation failed",
                "details": {"circuit": "Field required"},
                "correlation_id": "abc123-def456"
            }
        }
```

---

## Path Parameters

### TaskID

**Purpose:** Unique identifier for task status queries

**Type:** string (UUID v4 format)

**Validation:**
- Must match UUID v4 pattern: `[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}`
- Case-insensitive
- Hyphens required

**Valid Examples:**
- `550e8400-e29b-41d4-a716-446655440000`
- `123e4567-e89b-12d3-a456-426614174000`

**Invalid Examples:**
- `not-a-uuid` (not UUID format)
- `550e8400e29b41d4a716446655440000` (missing hyphens)
- `550e8400-e29b-51d4-a716-446655440000` (version 5, not version 4)

**Python Validation:**
```python
from uuid import UUID
from fastapi import Path, HTTPException

def validate_task_id(task_id: str = Path(...)) -> str:
    try:
        uuid_obj = UUID(task_id, version=4)
        return str(uuid_obj)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid task ID format. Expected UUID v4."
        )
```

---

## Headers

### Request Headers

| Header | Required | Description | Example |
|--------|----------|-------------|---------|
| `Content-Type` | Yes (POST) | Request content type | `application/json` |
| `X-Correlation-ID` | No | Client-provided correlation ID | `client-abc-123` |
| `User-Agent` | No | Client identification | `quantum-client/1.0` |

### Response Headers

| Header | Always Present | Description | Example |
|--------|----------------|-------------|---------|
| `Content-Type` | Yes | Response content type | `application/json` |
| `X-Correlation-ID` | Yes | Correlation ID (from request or generated) | `abc123-def456` |

---

## Validation Rules Summary

### Field-Level Validation

| Field | Rule | Error Message |
|-------|------|---------------|
| `circuit` (required) | Must be present | "Field required" |
| `circuit` (type) | Must be string | "Input should be a valid string" |
| `circuit` (length) | Length >= 1 | "String should have at least 1 character" |
| `task_id` (format) | Must be UUID v4 | "Invalid task ID format. Expected UUID v4." |

### Request-Level Validation

| Rule | Error Code | Error Message |
|------|------------|---------------|
| Invalid JSON syntax | 400 | "Invalid JSON" |
| Wrong Content-Type | 415 | "Unsupported Media Type" |
| Extra unknown fields | Ignored | (Pydantic ignores by default) |

---

## Data Flow

### Task Submission Flow

```
Client Request:
POST /tasks
Content-Type: application/json
{
  "circuit": "OPENQASM 3; qubit q; h q; measure q;"
}

↓ Validation (Pydantic)
↓ Generate task_id = uuid.uuid4()
↓ Generate correlation_id (or use from header)

Server Response:
200 OK
Content-Type: application/json
X-Correlation-ID: abc123-def456
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Task submitted successfully.",
  "correlation_id": "abc123-def456"
}
```

### Task Status Flow

```
Client Request:
GET /tasks/550e8400-e29b-41d4-a716-446655440000

↓ Validate task_id format (UUID v4)
↓ Generate mock status response
↓ Extract/generate correlation_id

Server Response:
200 OK
Content-Type: application/json
X-Correlation-ID: xyz789-uvw456
{
  "status": "pending",
  "message": "Task is still in progress.",
  "correlation_id": "xyz789-uvw456"
}
```

---

## Stub Data Generation

### Task ID Generation

```python
import uuid

def generate_task_id() -> str:
    """Generate unique task ID using UUID v4"""
    return str(uuid.uuid4())
```

### Status Response Generation

```python
def generate_mock_status(task_id: str) -> TaskStatusResponse:
    """Generate mock status response (always pending in stub phase)"""
    return TaskStatusResponse(
        status=TaskStatus.PENDING,
        message="Task is still in progress.",
        correlation_id=get_correlation_id()
    )
```

### Correlation ID Handling

```python
from contextvars import ContextVar
import uuid

correlation_id_var: ContextVar[str] = ContextVar("correlation_id")

def get_correlation_id() -> str:
    """Get correlation ID from context or generate new one"""
    return correlation_id_var.get(str(uuid.uuid4()))

def set_correlation_id(cid: str):
    """Set correlation ID in context"""
    correlation_id_var.set(cid)
```

---

## Future Enhancements

### Database Schema (Out of Scope for Stub)

When database integration is added, the Task entity will be persisted:

```sql
CREATE TABLE tasks (
    id UUID PRIMARY KEY,
    circuit TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    result JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    CONSTRAINT status_check CHECK (status IN ('pending', 'processing', 'completed', 'failed'))
);

CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_created_at ON tasks(created_at);
```

### Additional Fields (Future)

Potential fields to add in future iterations:
- `created_at`: Task creation timestamp
- `updated_at`: Last status update timestamp
- `error_message`: Error details for failed tasks
- `execution_time_ms`: Task processing duration
- `circuit_metadata`: Parsed circuit information (qubit count, gate count, etc.)

---

## Document History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-12-28 | Initial data model definition | Claude |
