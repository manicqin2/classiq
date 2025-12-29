# Implementation Tasks: Deployment Integration Tests

**Feature**: 004-deployment-integration-tests
**Created**: 2025-12-29
**Total Tasks**: 12
**Estimated Effort**: 3-5 days

## Overview

This document breaks down the implementation of deployment integration tests into concrete, executable tasks. The tests validate complete deployment environments including all system components (API, worker, database, message queue).

**Scope**: Priority 1 and Priority 2 tests only (as per user request)

## Task Summary

- **Phase 1 (Setup)**: 1 task
- **Phase 2 (Foundational)**: 4 tasks
- **Phase 3 (User Story 1 - DevOps Deployment Validation)**: 2 tasks
- **Phase 4 (User Story 2 - Developer Environment Validation)**: 3 tasks
- **Phase 5 (User Story 3 - CI/CD Integration)**: 2 tasks

**Total**: 12 tasks

## Implementation Strategy

### MVP Approach

**Minimum Viable Product** (User Story 1 only):
- Service health validation
- End-to-end task processing tests
- Basic test infrastructure

This validates the most critical deployment workflow and provides immediate value.

### Incremental Delivery

1. **First Increment (US1)**: DevOps deployment validation
   - Deliverable: Health checks + E2E workflow tests
   - Value: Catch deployment failures before production

2. **Second Increment (US2)**: Developer environment validation
   - Deliverable: Schema and queue configuration tests
   - Value: Developers can validate local setup

3. **Third Increment (US3)**: CI/CD integration
   - Deliverable: Error handling tests + CI scripts
   - Value: Automated PR validation

## Phase 1: Setup

**Goal**: Initialize test infrastructure and project structure

**Tasks**:

- [ ] T001 Create test project structure and configuration files in tests/integration/deployment/

**Files to Create**:
- `tests/integration/deployment/` - Main test directory
- `tests/integration/deployment/conftest.py` - Shared pytest fixtures
- `tests/integration/deployment/helpers/` - Helper modules directory
- `tests/integration/deployment/helpers/__init__.py` - Package marker
- `tests/requirements-test.txt` - Test dependencies
- `pytest.ini` - pytest configuration

**Implementation Details**:
```python
# tests/integration/deployment/conftest.py
import os
import pytest

@pytest.fixture(scope="session")
def test_config():
    """Load test configuration from environment variables."""
    return {
        "api_url": os.getenv("TEST_API_URL", "http://localhost:8001"),
        "db_url": os.getenv("TEST_DATABASE_URL",
            "postgresql://quantum_user:quantum_pass@localhost:5432/quantum_db"),
        "rabbitmq_url": os.getenv("TEST_RABBITMQ_URL",
            "amqp://quantum_user:quantum_pass@localhost:5672/"),
        "rabbitmq_mgmt_url": os.getenv("TEST_RABBITMQ_MGMT_URL",
            "http://localhost:15672"),
        "rabbitmq_user": os.getenv("TEST_RABBITMQ_USER", "guest"),
        "rabbitmq_pass": os.getenv("TEST_RABBITMQ_PASS", "guest"),
        "timeout": int(os.getenv("TEST_TIMEOUT", "30")),
        "poll_interval": float(os.getenv("TEST_POLL_INTERVAL", "0.5")),
    }
```

```ini
# pytest.ini
[pytest]
testpaths = tests/integration/deployment
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
markers =
    p1: Priority 1 tests (critical for deployment)
    p2: Priority 2 tests (quality assurance)
```

```txt
# tests/requirements-test.txt
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-html==4.1.1
pytest-json-report==1.5.0
httpx==0.25.0
asyncpg==0.29.0
```

**Acceptance Criteria**:
- [ ] pytest discovery finds deployment tests directory
- [ ] Configuration fixture loads environment variables correctly
- [ ] All dependencies listed in requirements-test.txt

**Estimated Effort**: 2 hours

---

## Phase 2: Foundational Tasks

**Goal**: Build test infrastructure components required by all user stories

**Dependencies**: Must complete Phase 1 before starting Phase 2

**Tasks**:

- [ ] T002 [P] Implement API client helper in tests/integration/deployment/helpers/api_client.py

**Implementation**:
```python
import httpx
from typing import Dict, Any

class APIClient:
    """HTTP client wrapper for API interaction in tests."""

    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=base_url, timeout=timeout)

    async def submit_task(self, circuit: str) -> Dict[str, Any]:
        """Submit quantum circuit task."""
        response = await self.client.post("/tasks", json={"circuit": circuit})
        response.raise_for_status()
        return response.json()

    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get task status by ID."""
        response = await self.client.get(f"/tasks/{task_id}")
        response.raise_for_status()
        return response.json()

    async def check_health(self) -> Dict[str, Any]:
        """Check API health endpoint."""
        response = await self.client.get("/health")
        response.raise_for_status()
        return response.json()

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
```

**Acceptance Criteria**:
- [ ] Client handles HTTP errors gracefully with clear messages
- [ ] All API endpoints (POST /tasks, GET /tasks/<id>, GET /health) accessible
- [ ] Response JSON parsing works correctly

**Estimated Effort**: 3 hours

---

- [ ] T003 [P] Implement database client helper in tests/integration/deployment/helpers/db_client.py

**Implementation**:
```python
import asyncpg
from typing import Optional, List, Dict, Any

class DatabaseClient:
    """Database validation helper for integration tests."""

    def __init__(self, connection_url: str):
        self.connection_url = connection_url
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Establish database connection pool."""
        self.pool = await asyncpg.create_pool(self.connection_url)

    async def check_table_exists(self, table_name: str) -> bool:
        """Check if table exists in database."""
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name=$1)",
                table_name
            )
            return result

    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task by ID from database."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM tasks WHERE task_id = $1::uuid",
                task_id
            )
            return dict(row) if row else None

    async def get_status_history(self, task_id: str) -> List[Dict[str, Any]]:
        """Get status history for task."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM status_history WHERE task_id = $1::uuid ORDER BY transitioned_at",
                task_id
            )
            return [dict(row) for row in rows]

    async def close(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
```

**Acceptance Criteria**:
- [ ] Connection pool established successfully
- [ ] Schema introspection queries work (check_table_exists)
- [ ] Task and status history queries return correct data

**Estimated Effort**: 3 hours

---

- [ ] T004 [P] Implement queue client helper in tests/integration/deployment/helpers/queue_client.py

**Implementation**:
```python
import httpx
from typing import Dict, Any

class QueueClient:
    """RabbitMQ inspection helper for integration tests."""

    def __init__(self, rabbitmq_url: str, mgmt_url: str, mgmt_user: str, mgmt_pass: str):
        self.rabbitmq_url = rabbitmq_url
        self.mgmt_url = mgmt_url
        self.mgmt_auth = httpx.BasicAuth(mgmt_user, mgmt_pass)
        self.http_client = httpx.AsyncClient(base_url=mgmt_url, auth=self.mgmt_auth)

    async def get_queue_info(self, queue_name: str) -> Dict[str, Any]:
        """Get queue metadata from RabbitMQ Management API."""
        response = await self.http_client.get(f"/api/queues/%2F/{queue_name}")
        response.raise_for_status()
        return response.json()

    async def check_queue_exists(self, queue_name: str) -> bool:
        """Check if queue exists."""
        try:
            await self.get_queue_info(queue_name)
            return True
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return False
            raise

    async def get_consumer_count(self, queue_name: str) -> int:
        """Get number of active consumers for queue."""
        info = await self.get_queue_info(queue_name)
        return info.get("consumers", 0)

    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()
```

**Acceptance Criteria**:
- [ ] RabbitMQ Management API accessible
- [ ] Queue metadata retrieved correctly
- [ ] Consumer count accurate

**Estimated Effort**: 2 hours

---

- [ ] T005 Implement test data cleanup fixture in tests/integration/deployment/conftest.py

**Implementation**:
```python
# Add to conftest.py
import pytest
from typing import List
from .helpers.db_client import DatabaseClient

@pytest.fixture
async def cleanup_test_tasks(test_config):
    """Track and cleanup test tasks after each test."""
    test_task_ids: List[str] = []

    def register_task(task_id: str) -> str:
        """Register a task ID for cleanup."""
        test_task_ids.append(task_id)
        return task_id

    yield register_task

    # Cleanup after test (runs even if test fails)
    if test_task_ids:
        db_client = DatabaseClient(test_config["db_url"])
        await db_client.connect()

        try:
            async with db_client.pool.acquire() as conn:
                for task_id in test_task_ids:
                    # Delete status history first (foreign key constraint)
                    await conn.execute(
                        "DELETE FROM status_history WHERE task_id = $1::uuid",
                        task_id
                    )
                    # Then delete task
                    await conn.execute(
                        "DELETE FROM tasks WHERE task_id = $1::uuid",
                        task_id
                    )
        finally:
            await db_client.close()

@pytest.fixture
async def api_client(test_config):
    """Provide API client instance."""
    from .helpers.api_client import APIClient
    client = APIClient(test_config["api_url"])
    yield client
    await client.close()

@pytest.fixture
async def db_client(test_config):
    """Provide database client instance."""
    from .helpers.db_client import DatabaseClient
    client = DatabaseClient(test_config["db_url"])
    await client.connect()
    yield client
    await client.close()

@pytest.fixture
async def queue_client(test_config):
    """Provide queue client instance."""
    from .helpers.queue_client import QueueClient
    client = QueueClient(
        test_config["rabbitmq_url"],
        test_config["rabbitmq_mgmt_url"],
        test_config["rabbitmq_user"],
        test_config["rabbitmq_pass"]
    )
    yield client
    await client.close()
```

**Acceptance Criteria**:
- [ ] Cleanup fixture removes test tasks from database
- [ ] Cleanup runs even if test fails
- [ ] No orphaned test data left in database

**Estimated Effort**: 2 hours

---

## Phase 3: User Story 1 - DevOps Deployment Validation

**User Story**: As a DevOps engineer, I need to validate that a new deployment is fully functional before routing production traffic to it.

**Goal**: Implement critical health checks and end-to-end workflow validation

**Independent Test Criteria**:
- [ ] All services report healthy status within 2 seconds
- [ ] Complete task workflow (submit → process → complete) succeeds
- [ ] Tests pass on fresh deployment without existing data

**Dependencies**: Requires Phase 2 (Foundational tasks) to be complete

**Tasks**:

- [ ] T006 [US1] Implement service health validation tests in tests/integration/deployment/test_p1_health.py

**Test Cases**:
1. API health endpoint responds within 2 seconds
2. Database connection succeeds
3. RabbitMQ connection succeeds
4. All components report "healthy" status

**Implementation**:
```python
import pytest
import time

@pytest.mark.p1
@pytest.mark.asyncio
async def test_api_health_check(api_client):
    """Verify API health endpoint responds correctly within timeout."""
    start_time = time.time()
    health = await api_client.check_health()
    response_time = (time.time() - start_time) * 1000

    assert response_time < 2000, f"Health check took {response_time}ms (expected < 2000ms)"
    assert health["status"] == "healthy", f"API status is {health['status']}"
    assert health["database_status"] == "connected", "Database not connected"
    assert health["queue_status"] == "connected", "Queue not connected"

@pytest.mark.p1
@pytest.mark.asyncio
async def test_database_connectivity(db_client):
    """Verify database accepts connections and executes queries."""
    result = await db_client.pool.fetchval("SELECT 1")
    assert result == 1, "Database query failed"

@pytest.mark.p1
@pytest.mark.asyncio
async def test_rabbitmq_connectivity(queue_client):
    """Verify RabbitMQ Management API is accessible."""
    response = await queue_client.http_client.get("/api/queues")
    assert response.status_code == 200, f"RabbitMQ API returned {response.status_code}"
```

**Acceptance Criteria**:
- [ ] All health checks pass within timeout
- [ ] Test failures provide specific component details
- [ ] Tests complete in under 10 seconds total

**Estimated Effort**: 4 hours

---

- [ ] T007 [US1] Implement end-to-end task processing test in tests/integration/deployment/test_p1_e2e_workflow.py

**Test Cases**:
1. Submit task via API and receive valid task ID
2. Verify task persisted to database with "pending" status
3. Poll until worker processes task (max 30 seconds)
4. Verify task status transitions to "completed"
5. Verify results stored in database
6. Verify status history recorded correctly

**Implementation**:
```python
import pytest
import asyncio
import time

BELL_STATE_CIRCUIT = """OPENQASM 3;
qubit[2] q;
h q[0];
cx q[0], q[1];
measure q;"""

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
    assert task["current_status"] == "pending", f"Expected 'pending', got '{task['current_status']}'"
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
```

**Acceptance Criteria**:
- [ ] Complete workflow executes successfully from submission to completion
- [ ] Task transitions through all expected statuses (pending → processing → completed)
- [ ] Results match expected format (dict with measurement outcomes)
- [ ] Test completes in under 35 seconds (30s timeout + processing)

**Estimated Effort**: 6 hours

---

## Phase 4: User Story 2 - Developer Environment Validation

**User Story**: As a developer, I need to validate that my local development environment is correctly configured before starting work.

**Goal**: Implement schema and queue configuration validation tests

**Independent Test Criteria**:
- [ ] All required database tables exist with correct schema
- [ ] All required indexes exist
- [ ] RabbitMQ queue exists with correct configuration
- [ ] At least one worker is consuming from queue

**Dependencies**: Requires Phase 2 (Foundational tasks) to be complete

**Tasks**:

- [ ] T008 [P] [US2] Implement database schema validation tests in tests/integration/deployment/test_p2_schema.py

**Test Cases**:
1. Verify `tasks` table exists with correct columns
2. Verify `status_history` table exists with correct columns
3. Verify `alembic_version` table exists
4. Verify required indexes exist
5. Verify `taskstatus` enum exists with correct values

**Implementation**:
```python
import pytest

@pytest.mark.p2
@pytest.mark.asyncio
async def test_required_tables_exist(db_client):
    """Verify all required database tables exist."""
    required_tables = ["tasks", "status_history", "alembic_version"]

    for table_name in required_tables:
        exists = await db_client.check_table_exists(table_name)
        assert exists, f"Required table '{table_name}' does not exist"

@pytest.mark.p2
@pytest.mark.asyncio
async def test_tasks_table_schema(db_client):
    """Verify tasks table has correct columns and types."""
    async with db_client.pool.acquire() as conn:
        columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'tasks'
            ORDER BY ordinal_position
        """)

    column_info = {col["column_name"]: col for col in columns}

    required_columns = {
        "task_id": "uuid",
        "circuit": "text",
        "submitted_at": "timestamp with time zone",
        "current_status": "USER-DEFINED",  # enum type
        "completed_at": "timestamp with time zone",
        "result": "jsonb",
        "error_message": "text"
    }

    for col_name, expected_type in required_columns.items():
        assert col_name in column_info, f"Column '{col_name}' missing from tasks table"
        if expected_type != "USER-DEFINED":
            actual_type = column_info[col_name]["data_type"]
            assert actual_type == expected_type, \
                f"Column '{col_name}' has type '{actual_type}', expected '{expected_type}'"

@pytest.mark.p2
@pytest.mark.asyncio
async def test_status_history_table_schema(db_client):
    """Verify status_history table has correct columns."""
    async with db_client.pool.acquire() as conn:
        columns = await conn.fetch("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'status_history'
            ORDER BY ordinal_position
        """)

    column_names = [col["column_name"] for col in columns]
    required_columns = ["id", "task_id", "status", "transitioned_at", "notes"]

    for col in required_columns:
        assert col in column_names, f"Column '{col}' missing from status_history table"

@pytest.mark.p2
@pytest.mark.asyncio
async def test_required_indexes_exist(db_client):
    """Verify all required indexes are created."""
    async with db_client.pool.acquire() as conn:
        indexes = await conn.fetch("""
            SELECT indexname, tablename
            FROM pg_indexes
            WHERE tablename IN ('tasks', 'status_history')
        """)

    index_names = [idx["indexname"] for idx in indexes]

    required_indexes = [
        "idx_task_status",
        "idx_task_submitted_at",
        "idx_status_history_task_time"
    ]

    for idx in required_indexes:
        assert idx in index_names, f"Required index '{idx}' does not exist"

@pytest.mark.p2
@pytest.mark.asyncio
async def test_taskstatus_enum_values(db_client):
    """Verify taskstatus enum type has correct values."""
    async with db_client.pool.acquire() as conn:
        enum_values = await conn.fetch("""
            SELECT enumlabel
            FROM pg_enum
            JOIN pg_type ON pg_enum.enumtypid = pg_type.oid
            WHERE pg_type.typname = 'taskstatus'
            ORDER BY enumsortorder
        """)

    values = [e["enumlabel"] for e in enum_values]
    expected_values = ["pending", "processing", "completed", "failed"]

    assert values == expected_values, \
        f"Enum values mismatch. Expected {expected_values}, got {values}"
```

**Acceptance Criteria**:
- [ ] All schema validation tests pass
- [ ] Missing schema elements clearly identified in failure messages
- [ ] Tests complete in under 5 seconds

**Estimated Effort**: 4 hours

---

- [ ] T009 [P] [US2] Implement queue configuration tests in tests/integration/deployment/test_p2_queue.py

**Test Cases**:
1. Verify `quantum_tasks` queue exists
2. Verify queue is durable
3. Verify queue has at least one active consumer
4. Verify message persistence settings

**Implementation**:
```python
import pytest

@pytest.mark.p2
@pytest.mark.asyncio
async def test_quantum_tasks_queue_exists(queue_client):
    """Verify quantum_tasks queue exists in RabbitMQ."""
    exists = await queue_client.check_queue_exists("quantum_tasks")
    assert exists, "quantum_tasks queue does not exist"

@pytest.mark.p2
@pytest.mark.asyncio
async def test_queue_is_durable(queue_client):
    """Verify queue has durable flag set (survives broker restart)."""
    info = await queue_client.get_queue_info("quantum_tasks")
    assert info["durable"] is True, \
        f"Queue is not durable (durable={info.get('durable')})"

@pytest.mark.p2
@pytest.mark.asyncio
async def test_queue_has_consumers(queue_client):
    """Verify queue has at least one active consumer (worker running)."""
    consumer_count = await queue_client.get_consumer_count("quantum_tasks")
    assert consumer_count >= 1, \
        f"Expected at least 1 consumer, found {consumer_count}. Is the worker running?"

@pytest.mark.p2
@pytest.mark.asyncio
async def test_queue_message_settings(queue_client):
    """Verify queue configuration for message persistence."""
    info = await queue_client.get_queue_info("quantum_tasks")

    # Durable queue accepts persistent messages
    assert info["durable"] is True, "Queue must be durable for message persistence"

    # Auto-delete should be false (queue persists)
    assert info.get("auto_delete", False) is False, \
        "Queue should not auto-delete"
```

**Acceptance Criteria**:
- [ ] All queue configuration tests pass
- [ ] Consumer count validation works correctly
- [ ] Tests complete in under 5 seconds

**Estimated Effort**: 3 hours

---

- [ ] T010 [P] [US2] Implement error handling tests in tests/integration/deployment/test_p2_error_handling.py

**Test Cases**:
1. Submit invalid task data → verify 400 response
2. Query non-existent task → verify 404 response
3. Submit empty circuit → verify 400 response
4. Verify error responses include helpful messages

**Implementation**:
```python
import pytest
import httpx
import uuid

@pytest.mark.p2
@pytest.mark.asyncio
async def test_empty_circuit_returns_400(api_client):
    """Verify API returns 400 for empty circuit."""
    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await api_client.submit_task("")

    assert exc_info.value.response.status_code == 400, \
        f"Expected 400, got {exc_info.value.response.status_code}"

@pytest.mark.p2
@pytest.mark.asyncio
async def test_missing_circuit_field_returns_400(api_client):
    """Verify API returns 400 when circuit field is missing."""
    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        response = await api_client.client.post("/tasks", json={})

    assert exc_info.value.response.status_code == 400, \
        f"Expected 400 for missing field, got {exc_info.value.response.status_code}"

@pytest.mark.p2
@pytest.mark.asyncio
async def test_nonexistent_task_returns_404(api_client):
    """Verify API returns 404 for non-existent task ID."""
    fake_task_id = str(uuid.uuid4())

    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await api_client.get_task_status(fake_task_id)

    assert exc_info.value.response.status_code == 404, \
        f"Expected 404 for non-existent task, got {exc_info.value.response.status_code}"

@pytest.mark.p2
@pytest.mark.asyncio
async def test_invalid_task_id_format_returns_400(api_client):
    """Verify API returns 400 for invalid UUID format."""
    invalid_id = "not-a-uuid"

    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await api_client.get_task_status(invalid_id)

    # Should be 400 (validation error) not 404
    assert exc_info.value.response.status_code == 400, \
        f"Expected 400 for invalid UUID format, got {exc_info.value.response.status_code}"

@pytest.mark.p2
@pytest.mark.asyncio
async def test_error_responses_include_details(api_client, db_client):
    """Verify error responses include helpful error messages."""
    # Test 400 error includes validation details
    try:
        await api_client.submit_task("")
    except httpx.HTTPStatusError as e:
        error_body = e.response.json()
        assert "error" in error_body or "detail" in error_body, \
            "Error response should include error message"

    # Test 404 error includes helpful message
    fake_id = str(uuid.uuid4())
    try:
        await api_client.get_task_status(fake_id)
    except httpx.HTTPStatusError as e:
        error_body = e.response.json()
        assert "error" in error_body or "detail" in error_body, \
            "404 response should include error message"

        # Verify no database record was created
        task = await db_client.get_task(fake_id)
        assert task is None, "404 error should not create database record"
```

**Acceptance Criteria**:
- [ ] All error scenarios return correct HTTP status codes
- [ ] Error responses include actionable messages
- [ ] No database pollution from failed requests (verified)

**Estimated Effort**: 3 hours

---

## Phase 5: User Story 3 - CI/CD Integration

**User Story**: As a CI/CD system, I need to run integration tests automatically and report results in a machine-readable format.

**Goal**: Create test runner scripts and CI integration

**Independent Test Criteria**:
- [ ] Test runner script exits with code 0 on success, non-zero on failure
- [ ] JSON reports generated for CI parsing
- [ ] HTML reports generated for human review
- [ ] Script can run in CI environment (GitHub Actions, GitLab CI)

**Dependencies**: Requires all previous phases complete

**Tasks**:

- [ ] T011 [US3] Create CI test runner script in tests/integration/deployment/run_tests.sh

**Implementation**:
```bash
#!/bin/bash
# tests/integration/deployment/run_tests.sh
# CI/CD integration test runner

set -e  # Exit on any error

echo "================================================"
echo "Deployment Integration Test Runner"
echo "================================================"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
API_URL=${TEST_API_URL:-"http://localhost:8001"}
TIMEOUT=${TEST_TIMEOUT:-60}

echo ""
echo "Configuration:"
echo "  API URL: $API_URL"
echo "  Timeout: ${TIMEOUT}s"
echo ""

# Step 1: Wait for services to be ready
echo "Step 1: Waiting for services to be healthy..."
timeout $TIMEOUT bash -c "
  until curl -f $API_URL/health > /dev/null 2>&1; do
    echo '  Waiting for API...'
    sleep 1
  done
"

if [ $? -eq 0 ]; then
  echo -e "${GREEN}✓ Services are ready${NC}"
else
  echo -e "${RED}✗ Services failed to start within ${TIMEOUT}s${NC}"
  exit 1
fi

echo ""

# Step 2: Run Priority 1 tests (critical - must pass)
echo "Step 2: Running Priority 1 tests (critical)..."
pytest tests/integration/deployment/test_p1_*.py \
  --tb=short \
  --json-report \
  --json-report-file=test-results-p1.json \
  --html=test-report-p1.html \
  --self-contained-html \
  -v

P1_EXIT_CODE=$?

if [ $P1_EXIT_CODE -eq 0 ]; then
  echo -e "${GREEN}✓ Priority 1 tests passed${NC}"
else
  echo -e "${RED}✗ Priority 1 tests failed${NC}"
  echo "Deployment validation FAILED - do not proceed to production"
  exit $P1_EXIT_CODE
fi

echo ""

# Step 3: Run Priority 2 tests (quality - continue on failure)
echo "Step 3: Running Priority 2 tests (quality)..."
pytest tests/integration/deployment/test_p2_*.py \
  --tb=short \
  --json-report \
  --json-report-file=test-results-p2.json \
  --html=test-report-p2.html \
  --self-contained-html \
  --continue-on-collection-errors \
  -v

P2_EXIT_CODE=$?

if [ $P2_EXIT_CODE -eq 0 ]; then
  echo -e "${GREEN}✓ Priority 2 tests passed${NC}"
else
  echo -e "${RED}⚠ Priority 2 tests had failures (non-blocking)${NC}"
fi

echo ""
echo "================================================"
echo "Test Results Summary"
echo "================================================"
echo "  P1 (Critical): $([ $P1_EXIT_CODE -eq 0 ] && echo '✓ PASS' || echo '✗ FAIL')"
echo "  P2 (Quality):  $([ $P2_EXIT_CODE -eq 0 ] && echo '✓ PASS' || echo '⚠ WARN')"
echo ""
echo "Reports generated:"
echo "  - test-results-p1.json (machine-readable)"
echo "  - test-report-p1.html (human-readable)"
echo "  - test-results-p2.json (machine-readable)"
echo "  - test-report-p2.html (human-readable)"
echo "================================================"

# Overall exit code based on P1 (P2 failures are warnings only)
exit $P1_EXIT_CODE
```

**Make script executable**:
```bash
chmod +x tests/integration/deployment/run_tests.sh
```

**Acceptance Criteria**:
- [ ] Script exits with code 0 on P1 pass, non-zero on P1 fail
- [ ] JSON and HTML reports generated for both P1 and P2 tests
- [ ] Clear output shows which tests passed/failed
- [ ] P2 failures don't block deployment (warning only)

**Estimated Effort**: 2 hours

---

- [ ] T012 [US3] Create documentation in tests/integration/deployment/README.md

**Implementation**:
```markdown
# Deployment Integration Tests

## Overview

This test suite validates complete deployment environments for the quantum circuit task queue API. Tests verify all system components (API, worker, database, message queue) are properly configured and functioning.

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Python 3.11+ with pip
- Running deployment (local or remote)

### Installation

```bash
# Install test dependencies
pip install -r tests/requirements-test.txt
```

### Running Tests

**Local development**:
```bash
# Start services
docker-compose up -d

# Run all tests
pytest tests/integration/deployment/ -v

# Run only Priority 1 tests (critical)
pytest tests/integration/deployment/test_p1_*.py -v

# Run only Priority 2 tests (quality)
pytest tests/integration/deployment/test_p2_*.py -v
```

**CI/CD**:
```bash
# Run test runner script (includes service health check)
bash tests/integration/deployment/run_tests.sh
```

## Test Organization

### Priority Levels

- **Priority 1 (P1)**: Critical tests that must pass for deployment
  - Service health validation
  - End-to-end task processing

- **Priority 2 (P2)**: Quality tests that should pass
  - Database schema validation
  - Queue configuration
  - Error handling

### Test Files

- `test_p1_health.py` - Service health checks
- `test_p1_e2e_workflow.py` - End-to-end task processing
- `test_p2_schema.py` - Database schema validation
- `test_p2_queue.py` - Queue configuration validation
- `test_p2_error_handling.py` - API error handling

## Configuration

Tests read configuration from environment variables:

```bash
# API Configuration
export TEST_API_URL="http://localhost:8001"

# Database Configuration
export TEST_DATABASE_URL="postgresql://quantum_user:quantum_pass@localhost:5432/quantum_db"

# RabbitMQ Configuration
export TEST_RABBITMQ_URL="amqp://quantum_user:quantum_pass@localhost:5672/"
export TEST_RABBITMQ_MGMT_URL="http://localhost:15672"
export TEST_RABBITMQ_USER="guest"
export TEST_RABBITMQ_PASS="guest"

# Test Behavior
export TEST_TIMEOUT="30"          # Max seconds to wait for task completion
export TEST_POLL_INTERVAL="0.5"   # Seconds between status polls
```

## Reports

### Generate HTML Report

```bash
pytest tests/integration/deployment/ \
  --html=test-report.html \
  --self-contained-html
```

Open `test-report.html` in a browser to view results.

### Generate JSON Report

```bash
pytest tests/integration/deployment/ \
  --json-report \
  --json-report-file=test-results.json
```

Parse `test-results.json` for CI/CD integration.

## Troubleshooting

### Services Not Ready

Check service status:
```bash
docker-compose ps
docker-compose logs api worker postgres rabbitmq
```

Wait for health:
```bash
timeout 60 bash -c 'until curl -f http://localhost:8001/health; do sleep 1; done'
```

### Tests Timeout

Increase timeout:
```bash
export TEST_TIMEOUT=60
pytest tests/integration/deployment/test_p1_e2e_workflow.py -v
```

Check worker logs:
```bash
docker-compose logs worker --tail=50
```

### Database Connection Failed

Verify database:
```bash
docker-compose exec postgres psql -U quantum_user -l
```

Run migrations:
```bash
docker-compose exec api alembic upgrade head
```

## CI/CD Integration

### GitHub Actions

```yaml
- name: Run integration tests
  run: bash tests/integration/deployment/run_tests.sh

- name: Upload test reports
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: test-reports
    path: |
      test-results-*.json
      test-report-*.html
```

### GitLab CI

```yaml
integration-tests:
  script:
    - bash tests/integration/deployment/run_tests.sh
  artifacts:
    when: always
    paths:
      - test-results-*.json
      - test-report-*.html
```

## Adding New Tests

1. Create test file matching pattern `test_p{priority}_{category}.py`
2. Use `@pytest.mark.asyncio` for async tests
3. Use `@pytest.mark.p1` or `@pytest.mark.p2` for priority marking
4. Use provided fixtures: `api_client`, `db_client`, `queue_client`
5. Register test tasks for cleanup: `cleanup_test_tasks(task_id)`

Example:
```python
import pytest

@pytest.mark.p2
@pytest.mark.asyncio
async def test_new_validation(api_client, db_client, cleanup_test_tasks):
    # Your test logic here
    pass
```

## Resources

- Feature Specification: [../spec.md](../spec.md)
- Implementation Plan: [../plan.md](../plan.md)
- Quickstart Guide: [../quickstart.md](../quickstart.md)
```

**Acceptance Criteria**:
- [ ] README covers all common use cases
- [ ] Clear examples for local and CI execution
- [ ] Troubleshooting section addresses common issues
- [ ] Instructions for adding new tests provided

**Estimated Effort**: 3 hours

---

## Dependencies

### Dependency Graph (User Story Completion Order)

```
Phase 1: Setup
   ↓
Phase 2: Foundational (T002, T003, T004, T005 can run in parallel)
   ↓
   ├─→ Phase 3: US1 (T006, T007 sequential)
   ├─→ Phase 4: US2 (T008, T009, T010 can run in parallel)
   └─→ Phase 5: US3 (T011, T012 can run in parallel)
```

### Task Dependencies

**Sequential Dependencies**:
- T001 → All other tasks (setup first)
- T002, T003, T004, T005 → T006, T007 (helpers before tests)
- T006, T007 → T011, T012 (tests before CI integration)

**Parallel Opportunities**:
- T002, T003, T004, T005 can run in parallel (different files)
- T008, T009, T010 can run in parallel (US2 tests, different files)
- T011, T012 can run in parallel (documentation tasks)

## Parallel Execution Examples

### Phase 2: Foundational (4 tasks in parallel)

**Opportunity**: T002, T003, T004, T005 can be implemented simultaneously by different developers or agents.

**Why**: Each creates a different helper module in separate files with no dependencies between them.

**Execution**:
```bash
# Agent 1
implement T002 (API client helper)

# Agent 2 (parallel)
implement T003 (DB client helper)

# Agent 3 (parallel)
implement T004 (Queue client helper)

# Agent 4 (parallel)
implement T005 (Cleanup fixture)
```

**Result**: Phase 2 completes in ~3 hours instead of 10 hours (sequential).

---

### Phase 4: User Story 2 (3 tasks in parallel)

**Opportunity**: T008, T009, T010 can be implemented simultaneously.

**Why**: Each creates different test files with no dependencies.

**Execution**:
```bash
# Agent 1
implement T008 (Schema validation tests)

# Agent 2 (parallel)
implement T009 (Queue configuration tests)

# Agent 3 (parallel)
implement T010 (Error handling tests)
```

**Result**: Phase 4 completes in ~4 hours instead of 10 hours (sequential).

---

### Phase 5: User Story 3 (2 tasks in parallel)

**Opportunity**: T011, T012 can be implemented simultaneously.

**Why**: One creates script, one creates docs - no overlap.

**Execution**:
```bash
# Agent 1
implement T011 (CI test runner script)

# Agent 2 (parallel)
implement T012 (Documentation README)
```

**Result**: Phase 5 completes in ~3 hours instead of 5 hours (sequential).

---

## Validation Checklist

Before marking the feature complete, verify:

### Format Validation
- [ ] All 12 tasks follow checklist format: `- [ ] TaskID [Labels] Description with file path`
- [ ] All user story tasks have [US1], [US2], or [US3] labels
- [ ] All parallelizable tasks have [P] marker
- [ ] All file paths are absolute and specific

### Completeness Validation
- [ ] Each user story has clear independent test criteria
- [ ] User Story 1 (DevOps): Health checks + E2E workflow
- [ ] User Story 2 (Developer): Schema + Queue + Error tests
- [ ] User Story 3 (CI/CD): Test runner + Documentation
- [ ] All phases have clear goals and deliverables

### Execution Validation
- [ ] MVP scope identified (User Story 1 only)
- [ ] Incremental delivery plan defined (3 increments)
- [ ] Parallel execution opportunities documented (3 opportunities, 7 tasks)
- [ ] Dependencies clearly mapped in dependency graph

### Technical Validation
- [ ] Test infrastructure setup complete (Phase 1)
- [ ] All helper clients implemented (Phase 2)
- [ ] All test files created with proper pytest markers
- [ ] CI integration scripts executable and documented

---

## Summary

**Total Tasks**: 12
**Parallel Opportunities**: 7 tasks across 3 phases
**Sequential Effort**: ~37 hours
**Parallel Effort**: ~20 hours (46% reduction)

**Task Distribution**:
- Setup: 1 task
- Foundational: 4 tasks (all parallelizable)
- User Story 1 (DevOps): 2 tasks
- User Story 2 (Developer): 3 tasks (all parallelizable)
- User Story 3 (CI/CD): 2 tasks (all parallelizable)

**MVP Recommendation**: Implement Phase 1, Phase 2, and Phase 3 (User Story 1) first. This delivers:
- Complete test infrastructure
- Critical deployment validation (health + E2E)
- Immediate value for DevOps deployments

**Incremental Delivery**:
1. **Week 1**: MVP (Phases 1-3) - DevOps can validate deployments
2. **Week 2**: User Story 2 (Phase 4) - Developers can validate local setups
3. **Week 3**: User Story 3 (Phase 5) - CI/CD automation complete

This approach delivers value incrementally while maintaining independent, testable increments.
