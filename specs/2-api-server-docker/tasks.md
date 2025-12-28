# Implementation Tasks: Standalone API Server with Docker Setup

**Created:** 2025-12-28
**Specification:** [spec.md](./spec.md)
**Plan:** [plan.md](./plan.md)
**Status:** Not Started

---

## Implementation Strategy

**Approach:** Incremental delivery by user story, enabling independent implementation and testing of each API capability.

**MVP Scope:** Complete all three user stories (US1, US2, US3) as they form the minimal viable API foundation. The stubbed implementation allows parallel frontend development while backend persistence is developed separately.

**Delivery Order:**
1. Setup & Foundation (infrastructure, logging, validation framework)
2. US1: Task Submission (POST /tasks)
3. US2: Task Status Retrieval (GET /tasks/{id})
4. US3: Health Check (GET /health)
5. Polish & Documentation

**Parallel Opportunities:** Each user story can be implemented in parallel after foundational tasks complete.

---

## User Story Mapping

### User Story 1: Submit Quantum Circuit Task [US1]
**Actor:** Developer or automated system
**Goal:** Submit a quantum circuit for asynchronous execution
**Priority:** P1 (MVP Critical)
**Components:**
- POST /tasks endpoint
- TaskSubmitRequest model (Pydantic)
- TaskSubmitResponse model (Pydantic)
- UUID generation
- Request validation
- Correlation ID handling

**Independent Test Criteria:**
- [ ] POST /tasks with valid circuit returns 200 with unique task_id
- [ ] POST /tasks without circuit field returns 400 with validation error
- [ ] POST /tasks with empty circuit returns 400 with validation error
- [ ] All responses include correlation_id
- [ ] Each request generates unique task_id (UUID v4 format)

---

### User Story 2: Check Task Status [US2]
**Actor:** Developer or automated system tracking task progress
**Goal:** Retrieve current status and results of a submitted task
**Priority:** P1 (MVP Critical)
**Components:**
- GET /tasks/{task_id} endpoint
- TaskStatusResponse model (Pydantic)
- UUID validation
- Stub status generation

**Independent Test Criteria:**
- [ ] GET /tasks/{valid-uuid} returns 200 with status information
- [ ] GET /tasks/{invalid-uuid} returns 400 with format error
- [ ] Status response includes correlation_id
- [ ] Stubbed implementation returns "pending" status consistently

---

### User Story 3: Health Check Verification [US3]
**Actor:** Infrastructure monitoring system or deployment automation
**Goal:** Verify API server is running and ready to accept requests
**Priority:** P1 (MVP Critical)
**Components:**
- GET /health endpoint
- HealthCheckResponse model (Pydantic)
- Timestamp generation

**Independent Test Criteria:**
- [ ] GET /health returns 200 with "healthy" status
- [ ] Health check responds in < 100ms
- [ ] Health endpoint accessible without authentication
- [ ] Response includes UTC timestamp

---

## Phase 1: Setup & Project Initialization

**Goal:** Create project structure, configure dependencies, and set up Docker containerization

**Tasks:**

- [X] T001 Create api/ directory and initialize project structure
  - Create directories: api/, api/tests/, api/tests/unit/, api/tests/integration/
  - Path: /Users/bzpysmn/work/classiq/api/

- [X] T002 Create requirements.txt with pinned dependencies
  - Add: fastapi==0.104.1, uvicorn[standard]==0.24.0, pydantic==2.5.0, structlog==23.2.0, python-json-logger==2.0.7
  - Add dev deps: pytest==7.4.3, httpx==0.25.2, pytest-asyncio==0.21.1
  - Path: /Users/bzpysmn/work/classiq/api/requirements.txt

- [X] T003 Create Dockerfile with multi-stage build
  - Base image: python:3.11-slim-bookworm
  - Non-root user (appuser, UID 1000)
  - Multi-stage: build stage + runtime stage
  - EXPOSE 8000, HEALTHCHECK instruction
  - Path: /Users/bzpysmn/work/classiq/api/Dockerfile

- [X] T004 Create .dockerignore file
  - Exclude: __pycache__, *.pyc, .pytest_cache, .env, tests/
  - Path: /Users/bzpysmn/work/classiq/api/.dockerignore

- [X] T005 Create config.py for environment variable loading
  - Load: PORT (default 8000), LOG_LEVEL (default INFO), ENVIRONMENT (default development), CORS_ORIGINS (default *)
  - Use pydantic BaseSettings for validation
  - Path: /Users/bzpysmn/work/classiq/api/config.py

**Phase 1 Completion Criteria:**
- [ ] Project structure created
- [ ] Dependencies documented in requirements.txt
- [ ] Dockerfile builds successfully
- [ ] Environment configuration loads from env vars

---

## Phase 2: Foundational Infrastructure

**Goal:** Set up logging, middleware, and core application framework that all user stories depend on

**Tasks:**

- [X] T006 Implement structured logging configuration
  - Configure structlog for JSON output
  - Fields: timestamp, level, message, correlation_id, component, environment
  - Support both JSON (production) and colored (development) output
  - Path: /Users/bzpysmn/work/classiq/api/logging_config.py

- [X] T007 Implement correlation ID middleware
  - Extract X-Correlation-ID header or generate UUID
  - Store in contextvars for access across request lifecycle
  - Inject into all log entries
  - Add X-Correlation-ID to response headers
  - Path: /Users/bzpysmn/work/classiq/api/middleware.py

- [X] T008 Create base FastAPI application
  - Initialize FastAPI app with title, description, version
  - Register CORS middleware with configurable origins
  - Register correlation ID middleware
  - Configure lifespan events (startup/shutdown logging)
  - Path: /Users/bzpysmn/work/classiq/api/app.py

- [X] T009 Implement global exception handlers
  - Handler for validation errors (422 → 400 with ErrorResponse format)
  - Handler for generic exceptions (500 with correlation_id)
  - Handler for HTTP exceptions (preserve status, add correlation_id)
  - Path: /Users/bzpysmn/work/classiq/api/app.py

- [X] T010 Create base Pydantic models for common responses
  - ErrorResponse model (error, details, correlation_id)
  - Correlation ID utility functions
  - Path: /Users/bzpysmn/work/classiq/api/models.py

**Phase 2 Completion Criteria:**
- [ ] FastAPI application initializes without errors
- [ ] Logging outputs structured JSON
- [ ] Correlation IDs generated and propagated
- [ ] Exception handlers return consistent error format

---

## Phase 3: User Story 1 - Task Submission [US1]

**Goal:** Enable clients to submit quantum circuit tasks and receive task IDs

**Tasks:**

- [ ] T011 [P] [US1] Create TaskSubmitRequest Pydantic model
  - Field: circuit (str, min_length=1, required)
  - Add schema example for documentation
  - Path: /Users/bzpysmn/work/classiq/api/models.py

- [ ] T012 [P] [US1] Create TaskSubmitResponse Pydantic model
  - Fields: task_id (str), message (str), correlation_id (str)
  - Add schema example
  - Path: /Users/bzpysmn/work/classiq/api/models.py

- [ ] T013 [US1] Implement POST /tasks endpoint handler
  - Accept TaskSubmitRequest body
  - Generate UUID v4 for task_id
  - Return TaskSubmitResponse with success message
  - Log request with correlation_id
  - Path: /Users/bzpysmn/work/classiq/api/routes.py

- [ ] T014 [US1] Register POST /tasks route in main application
  - Mount route with /tasks path and POST method
  - Tag: "tasks"
  - Include in OpenAPI documentation
  - Path: /Users/bzpysmn/work/classiq/api/app.py

**Phase 3 Test Scenarios:**
```bash
# Valid submission
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"circuit": "OPENQASM 3; qubit q; h q; measure q;"}'
# Expected: 200 with task_id

# Missing circuit field
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{}'
# Expected: 400 with validation error

# Empty circuit
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"circuit": ""}'
# Expected: 400 with validation error
```

**Phase 3 Completion Criteria:**
- [ ] All US1 test criteria pass
- [ ] POST /tasks endpoint functional
- [ ] Request validation working
- [ ] Unique task IDs generated
- [ ] Correlation IDs in all responses

---

## Phase 4: User Story 2 - Task Status Retrieval [US2]

**Goal:** Enable clients to query task status using task IDs

**Tasks:**

- [ ] T015 [P] [US2] Create TaskStatusResponse Pydantic model
  - Fields: status (enum: pending/processing/completed/failed), message (optional), result (optional), correlation_id (str)
  - Add schema examples for each status
  - Path: /Users/bzpysmn/work/classiq/api/models.py

- [ ] T016 [P] [US2] Implement UUID validation utility
  - Function to validate UUID v4 format
  - Raise HTTPException 400 if invalid
  - Path: /Users/bzpysmn/work/classiq/api/utils.py

- [ ] T017 [US2] Implement GET /tasks/{task_id} endpoint handler
  - Accept task_id path parameter
  - Validate UUID format
  - Return stubbed "pending" status (fixed response)
  - Log request with correlation_id
  - Path: /Users/bzpysmn/work/classiq/api/routes.py

- [ ] T018 [US2] Register GET /tasks/{task_id} route in main application
  - Mount route with /tasks/{task_id} path and GET method
  - Tag: "tasks"
  - Include in OpenAPI documentation
  - Path: /Users/bzpysmn/work/classiq/api/app.py

**Phase 4 Test Scenarios:**
```bash
# Valid UUID
curl http://localhost:8000/tasks/550e8400-e29b-41d4-a716-446655440000
# Expected: 200 with status "pending"

# Invalid UUID format
curl http://localhost:8000/tasks/not-a-uuid
# Expected: 400 with format error

# Valid UUID (different)
curl http://localhost:8000/tasks/123e4567-e89b-12d3-a456-426614174000
# Expected: 200 with status "pending"
```

**Phase 4 Completion Criteria:**
- [ ] All US2 test criteria pass
- [ ] GET /tasks/{task_id} endpoint functional
- [ ] UUID validation working
- [ ] Stubbed status returned consistently
- [ ] Correlation IDs in all responses

---

## Phase 5: User Story 3 - Health Check [US3]

**Goal:** Provide health check endpoint for monitoring and orchestration

**Tasks:**

- [ ] T019 [P] [US3] Create HealthCheckResponse Pydantic model
  - Fields: status (enum: healthy/degraded/unavailable), timestamp (str, ISO 8601)
  - Add schema example
  - Path: /Users/bzpysmn/work/classiq/api/models.py

- [ ] T020 [US3] Implement GET /health endpoint handler
  - Return "healthy" status (stubbed - always returns healthy)
  - Include UTC timestamp in ISO 8601 format
  - No correlation ID required (health checks are stateless)
  - Path: /Users/bzpysmn/work/classiq/api/routes.py

- [ ] T021 [US3] Register GET /health route in main application
  - Mount route with /health path and GET method
  - Tag: "health"
  - Include in OpenAPI documentation
  - Path: /Users/bzpysmn/work/classiq/api/app.py

**Phase 5 Test Scenarios:**
```bash
# Health check
curl http://localhost:8000/health
# Expected: 200 with status "healthy" and timestamp

# Measure response time
curl -w "\nTime: %{time_total}s\n" http://localhost:8000/health
# Expected: < 0.1s (100ms)
```

**Phase 5 Completion Criteria:**
- [ ] All US3 test criteria pass
- [ ] GET /health endpoint functional
- [ ] Response time < 100ms
- [ ] UTC timestamp included

---

## Phase 6: Container Integration & Deployment

**Goal:** Containerize application and verify Docker deployment

**Tasks:**

- [ ] T022 Build Docker image
  - Run: docker build -t quantum-api:latest .
  - Verify build completes without errors
  - Image size < 300MB
  - Path: /Users/bzpysmn/work/classiq/api/

- [ ] T023 Test container locally
  - Run: docker run -p 8000:8000 -e LOG_LEVEL=INFO quantum-api:latest
  - Verify container starts within 10 seconds
  - Verify all endpoints accessible
  - Path: /Users/bzpysmn/work/classiq/api/

- [ ] T024 Implement graceful shutdown handling
  - Register SIGTERM handler
  - Drain in-flight requests before exit
  - Log shutdown event
  - Path: /Users/bzpysmn/work/classiq/api/app.py

- [ ] T025 Verify health check in container
  - Add HEALTHCHECK instruction to Dockerfile
  - Test: docker inspect shows healthy status
  - Path: /Users/bzpysmn/work/classiq/api/Dockerfile

**Phase 6 Completion Criteria:**
- [ ] Docker image builds successfully
- [ ] Container starts and serves requests
- [ ] Health check passes
- [ ] Graceful shutdown works

---

## Phase 7: Documentation & Polish

**Goal:** Complete documentation and create operational artifacts

**Tasks:**

- [ ] T026 [P] Create README.md for api directory
  - Setup instructions (local development)
  - Docker build and run commands
  - Environment variables documentation
  - API endpoint summary
  - Path: /Users/bzpysmn/work/classiq/api/README.md

- [ ] T027 [P] Create example .env file
  - Template with all environment variables
  - Comments explaining each variable
  - Default values documented
  - Path: /Users/bzpysmn/work/classiq/api/.env.example

- [ ] T028 [P] Create integration test script
  - Bash script testing all three endpoints
  - Verify response codes and basic structure
  - Use jq for JSON parsing
  - Path: /Users/bzpysmn/work/classiq/api/tests/integration/test-api.sh

- [ ] T029 Verify OpenAPI documentation accessibility
  - Start server and access /docs (Swagger UI)
  - Verify all endpoints documented
  - Test interactive API calls from Swagger
  - Document URL in README

**Phase 7 Completion Criteria:**
- [ ] README complete and accurate
- [ ] Example .env file provided
- [ ] Integration test script passes
- [ ] OpenAPI docs accessible

---

## Dependencies & Execution Order

### Critical Path (Must Complete Sequentially)

```
Phase 1 (Setup)
  ↓
Phase 2 (Foundation)
  ↓
Phase 3 (US1) ←┐
  ↓            │ (Can execute in parallel after Phase 2)
Phase 4 (US2) ←┤
  ↓            │
Phase 5 (US3) ←┘
  ↓
Phase 6 (Container)
  ↓
Phase 7 (Documentation)
```

### Parallel Execution Opportunities

**After Phase 2 Completes:**

**Parallel Track 1 - User Story 1:**
- T011 [P] [US1] Create TaskSubmitRequest model
- T012 [P] [US1] Create TaskSubmitResponse model
- T013 [US1] Implement POST /tasks handler
- T014 [US1] Register POST /tasks route

**Parallel Track 2 - User Story 2:**
- T015 [P] [US2] Create TaskStatusResponse model
- T016 [P] [US2] Implement UUID validation utility
- T017 [US2] Implement GET /tasks/{task_id} handler
- T018 [US2] Register GET /tasks/{task_id} route

**Parallel Track 3 - User Story 3:**
- T019 [P] [US3] Create HealthCheckResponse model
- T020 [US3] Implement GET /health handler
- T021 [US3] Register GET /health route

**After Phase 3-5 Complete (Documentation):**
- T026 [P] Create README.md
- T027 [P] Create .env.example
- T028 [P] Create integration test script

### Dependency Rules

- **Blockers**: Phase 1 and Phase 2 must complete before any user story work
- **Independent Stories**: US1, US2, US3 have no dependencies on each other
- **Parallel Models**: Tasks marked [P] can run concurrently (different files)
- **Sequential Within Story**: Non-parallel tasks within a story must complete in order

---

## Task Summary

**Total Tasks:** 29

**Tasks by Phase:**
- Phase 1 (Setup): 5 tasks
- Phase 2 (Foundation): 5 tasks
- Phase 3 (US1): 4 tasks
- Phase 4 (US2): 4 tasks
- Phase 5 (US3): 3 tasks
- Phase 6 (Container): 4 tasks
- Phase 7 (Documentation): 4 tasks

**Tasks by User Story:**
- User Story 1: 4 tasks
- User Story 2: 4 tasks
- User Story 3: 3 tasks
- Infrastructure/Setup: 10 tasks
- Container/Deployment: 4 tasks
- Documentation: 4 tasks

**Parallel Opportunities:**
- 8 tasks marked [P] (parallelizable)
- 3 user stories can be implemented in parallel after foundation
- 3 documentation tasks can run in parallel

**MVP Scope:** All 29 tasks (complete stubbed API foundation)

**Estimated Effort:**
- Phase 1-2 (Setup/Foundation): 3-4 hours
- Phase 3-5 (User Stories): 4-6 hours (or 2-3 hours if parallel)
- Phase 6 (Container): 1-2 hours
- Phase 7 (Documentation): 1-2 hours
- **Total: 9-14 hours** (sequential) or **7-11 hours** (with parallelization)

---

## Implementation Notes

### Code Generation Guidelines

When implementing tasks, follow these patterns:

**Pydantic Models:**
```python
from pydantic import BaseModel, Field

class TaskSubmitRequest(BaseModel):
    circuit: str = Field(..., min_length=1, description="Quantum circuit definition")

    class Config:
        json_schema_extra = {
            "example": {"circuit": "OPENQASM 3; qubit q; h q; measure q;"}
        }
```

**FastAPI Endpoints:**
```python
from fastapi import APIRouter, HTTPException
import uuid

router = APIRouter()

@router.post("/tasks", response_model=TaskSubmitResponse, tags=["tasks"])
async def submit_task(request: TaskSubmitRequest):
    task_id = str(uuid.uuid4())
    correlation_id = get_correlation_id()

    logger.info("Task submitted", extra={
        "task_id": task_id,
        "correlation_id": correlation_id
    })

    return TaskSubmitResponse(
        task_id=task_id,
        message="Task submitted successfully.",
        correlation_id=correlation_id
    )
```

**Correlation ID Middleware:**
```python
from contextvars import ContextVar
from starlette.middleware.base import BaseHTTPMiddleware
import uuid

correlation_id_var: ContextVar[str] = ContextVar("correlation_id")

class CorrelationIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        cid = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        correlation_id_var.set(cid)

        response = await call_next(request)
        response.headers["X-Correlation-ID"] = cid
        return response
```

### Testing Commands

**Build and Run:**
```bash
cd /Users/bzpysmn/work/classiq/api
docker build -t quantum-api:latest .
docker run -d --name quantum-api -p 8000:8000 quantum-api:latest
```

**Test All Endpoints:**
```bash
# Health check
curl http://localhost:8000/health

# Submit task
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"circuit": "OPENQASM 3; qubit q; h q; measure q;"}'

# Get status (use task_id from above)
curl http://localhost:8000/tasks/{task_id}
```

**View Logs:**
```bash
docker logs -f quantum-api
```

---

## Constitution Compliance Tracking

Each task implements constitution principles:

| Task | Principle(s) | How Satisfied |
|------|--------------|---------------|
| T006 | Principle 3 | Structured logging for observability |
| T007 | Principle 3 | Correlation IDs for request tracing |
| T008 | Principle 8 | Production-ready framework with CORS |
| T009 | Principle 2 | Exception handling for fault tolerance |
| T013-T021 | Principle 7 | API layer doesn't execute, only accepts/returns |
| T020 | Principle 2,6 | Health check for monitoring and orchestration |
| T024 | Principle 8 | Graceful shutdown pattern |
| T003,T022-T023 | Principle 8 | Containerization with best practices |

---

## Document History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-12-28 | Initial task breakdown by user story | Claude |
