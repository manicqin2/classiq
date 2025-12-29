# Research: Deployment Integration Tests

**Feature**: 004-deployment-integration-tests
**Date**: 2025-12-29
**Status**: Complete

## Overview

This document captures research decisions made during the planning phase for deployment integration tests. All technology choices and patterns are based on industry best practices and alignment with the existing tech stack.

## Test Framework Research

### Decision: pytest with pytest-asyncio

**Research Questions**:
- What test framework best supports async Python code?
- Which framework has the best CI/CD integration?
- What provides the clearest test output for deployment validation?

**Options Evaluated**:

| Framework | Async Support | CI Integration | Ecosystem | Learning Curve |
|-----------|---------------|----------------|-----------|----------------|
| pytest | ✅ Excellent (pytest-asyncio) | ✅ Excellent | ✅ Rich plugins | ⚠️ Medium |
| unittest | ⚠️ Manual (asyncio.run) | ✅ Good | ⚠️ Limited | ✅ Low |
| nose2 | ⚠️ Plugin-based | ⚠️ Limited | ⚠️ Small | ⚠️ Medium |

**Rationale**:
1. **Async Support**: pytest-asyncio provides native `@pytest.mark.asyncio` decorator
2. **Fixtures**: Powerful fixture system for test setup/teardown
3. **Plugins**: pytest-html, pytest-json for CI reporting
4. **Industry Standard**: Most Python projects use pytest
5. **Parametrization**: Easy to test multiple scenarios with `@pytest.mark.parametrize`

**Implementation Pattern**:
```python
import pytest

@pytest.mark.asyncio
async def test_api_health():
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8001/health")
        assert response.status_code == 200
```

**References**:
- pytest documentation: https://docs.pytest.org/
- pytest-asyncio: https://pytest-asyncio.readthedocs.io/

---

## HTTP Client Research

### Decision: httpx

**Research Questions**:
- Which HTTP client provides best async support?
- What library aligns with FastAPI ecosystem?
- Which client handles connection pooling efficiently?

**Options Evaluated**:

| Client | Async Support | HTTP/2 | Familiar API | Active Development |
|--------|---------------|--------|--------------|-------------------|
| httpx | ✅ Native | ✅ Yes | ✅ requests-like | ✅ Active |
| aiohttp | ✅ Native | ❌ No | ⚠️ Different | ✅ Active |
| requests | ❌ None | ❌ No | ✅ Standard | ⚠️ Maintenance mode |

**Rationale**:
1. **Async-First**: Designed for async/await from ground up
2. **FastAPI Alignment**: Same ecosystem (used by Starlette test client)
3. **Modern Python**: Type hints, modern features
4. **Connection Pooling**: Automatic connection reuse
5. **Timeout Handling**: Clear timeout configuration

**Implementation Pattern**:
```python
import httpx

async with httpx.AsyncClient(base_url="http://localhost:8001", timeout=30.0) as client:
    response = await client.post("/tasks", json={"circuit": circuit})
    assert response.status_code == 200
```

**References**:
- httpx documentation: https://www.python-httpx.org/
- FastAPI testing guide: https://fastapi.tiangolo.com/tutorial/testing/

---

## Database Testing Strategy

### Decision: Direct asyncpg Connection

**Research Questions**:
- Should tests use ORM (SQLAlchemy) or raw SQL?
- How to validate schema without coupling to application code?
- What provides fastest query execution for validation?

**Options Evaluated**:

| Approach | Speed | Decoupling | Schema Introspection | Maintenance |
|----------|-------|------------|---------------------|-------------|
| asyncpg | ✅ Fastest | ✅ High | ✅ Direct SQL | ⚠️ Raw SQL |
| SQLAlchemy | ⚠️ Slower | ⚠️ Coupled | ✅ Metadata | ✅ ORM |
| psycopg2 | ⚠️ Sync only | ✅ High | ✅ Direct SQL | ⚠️ Blocking |

**Rationale**:
1. **Performance**: asyncpg is fastest Python PostgreSQL driver
2. **Same Driver**: Application uses asyncpg, tests match
3. **Schema Validation**: Direct access to `information_schema`
4. **No ORM Overhead**: Tests don't need models, just data
5. **Independence**: Tests don't import application code

**Implementation Pattern**:
```python
import asyncpg

pool = await asyncpg.create_pool("postgresql://...")
async with pool.acquire() as conn:
    task = await conn.fetchrow(
        "SELECT * FROM tasks WHERE task_id = $1::uuid",
        task_id
    )
    assert task["current_status"] == "pending"
```

**References**:
- asyncpg documentation: https://magicstack.github.io/asyncpg/
- PostgreSQL information_schema: https://www.postgresql.org/docs/current/information-schema.html

---

## Queue Inspection Strategy

### Decision: RabbitMQ Management API + aio-pika

**Research Questions**:
- How to inspect queue state without consuming messages?
- What's the best way to check consumer count?
- How to validate queue configuration (durable, persistent)?

**Options Evaluated**:

| Approach | Non-Invasive | Consumer Info | Config Validation | Complexity |
|----------|--------------|---------------|-------------------|------------|
| Management API | ✅ Read-only | ✅ Complete | ✅ Full metadata | ⚠️ HTTP client |
| aio-pika inspect | ⚠️ Connection | ⚠️ Limited | ⚠️ Limited | ✅ Simple |
| Both combined | ✅ Best of both | ✅ Complete | ✅ Full | ⚠️ Two clients |

**Rationale**:
1. **Management API**: Provides queue metadata without affecting messages
2. **Consumer Count**: Accurate real-time consumer information
3. **Configuration**: Durable, auto-delete, message counts all available
4. **HTTP Interface**: Easy to query with httpx
5. **aio-pika Fallback**: Use for message-level inspection if needed

**Implementation Pattern**:
```python
# Management API approach
async with httpx.AsyncClient() as client:
    response = await client.get(
        "http://localhost:15672/api/queues/%2F/quantum_tasks",
        auth=("guest", "guest")
    )
    queue_info = response.json()
    assert queue_info["durable"] is True
    assert queue_info["consumers"] >= 1
```

**References**:
- RabbitMQ Management HTTP API: https://www.rabbitmq.com/management.html
- aio-pika documentation: https://aio-pika.readthedocs.io/

---

## Test Data Management

### Decision: UUID-based Test Data with Automatic Cleanup

**Research Questions**:
- How to prevent test data conflicts?
- How to ensure idempotent test runs?
- What's the best cleanup strategy?

**Patterns Evaluated**:

| Pattern | Isolation | Idempotent | Parallel Safe | Cleanup |
|---------|-----------|------------|---------------|---------|
| UUID prefixes | ✅ High | ✅ Yes | ✅ Yes | ⚠️ Manual |
| Test database | ✅ Perfect | ✅ Yes | ⚠️ Resource heavy | ✅ Drop DB |
| Cleanup fixtures | ✅ High | ✅ Yes | ✅ Yes | ✅ Automatic |

**Rationale**:
1. **UUID Generation**: Each test uses unique task IDs
2. **Fixture-Based Cleanup**: pytest fixtures handle teardown
3. **Parallel Execution**: No conflicts between parallel tests
4. **Failure Resilience**: Cleanup runs even if test fails
5. **No Test Database**: Use same DB, just clean data

**Implementation Pattern**:
```python
@pytest.fixture
async def test_task_cleanup(db_pool):
    """Register and cleanup test tasks."""
    task_ids = []

    def register(task_id: str):
        task_ids.append(task_id)
        return task_id

    yield register

    # Cleanup (runs even on test failure)
    async with db_pool.acquire() as conn:
        for task_id in task_ids:
            await conn.execute(
                "DELETE FROM status_history WHERE task_id = $1::uuid",
                task_id
            )
            await conn.execute(
                "DELETE FROM tasks WHERE task_id = $1::uuid",
                task_id
            )
```

**References**:
- pytest fixtures: https://docs.pytest.org/en/stable/fixture.html
- UUID module: https://docs.python.org/3/library/uuid.html

---

## Polling Strategy for Async Tasks

### Decision: Exponential Backoff with Max Timeout

**Research Questions**:
- How to wait for worker to process task?
- What polling interval balances responsiveness vs load?
- How to avoid flaky tests from timing issues?

**Patterns Evaluated**:

| Pattern | Responsiveness | Resource Usage | Flake Risk | Complexity |
|---------|----------------|----------------|------------|------------|
| Fixed interval (0.5s) | ⚠️ Wasteful | ⚠️ High | ✅ Low | ✅ Simple |
| Exponential backoff | ✅ Adaptive | ✅ Low | ✅ Low | ⚠️ Medium |
| Fixed with timeout | ✅ Good | ⚠️ Medium | ✅ Low | ✅ Simple |

**Rationale**:
1. **Fixed Interval**: Simple, predictable, good for short waits
2. **Max Timeout**: Prevents infinite loops, clear failure message
3. **Generous Timeout**: 30 seconds for task processing (2-3s typical)
4. **Short Poll**: 0.5s interval catches completion quickly
5. **Clear Errors**: Timeout message includes elapsed time

**Implementation Pattern**:
```python
async def wait_for_completion(api_client, task_id, max_wait=30, poll_interval=0.5):
    """Poll task status until completed or timeout."""
    start_time = time.time()

    while (time.time() - start_time) < max_wait:
        status = await api_client.get_task_status(task_id)

        if status["status"] in ["completed", "failed"]:
            return status

        await asyncio.sleep(poll_interval)

    elapsed = time.time() - start_time
    raise TimeoutError(f"Task {task_id} did not complete in {elapsed:.1f}s")
```

**References**:
- asyncio sleep: https://docs.python.org/3/library/asyncio-task.html#sleeping
- Testing async code: https://pytest-asyncio.readthedocs.io/en/latest/concepts.html

---

## CI/CD Integration

### Decision: pytest-json-report + HTML Reports

**Research Questions**:
- What test output format works best for CI/CD?
- How to provide human-readable reports?
- What enables test result trending over time?

**Options Evaluated**:

| Format | CI Parsing | Human Readable | Trending | Artifact Size |
|--------|------------|----------------|----------|---------------|
| JUnit XML | ✅ Universal | ⚠️ Limited | ✅ Yes | ⚠️ Large |
| JSON | ✅ Good | ⚠️ Raw data | ✅ Yes | ✅ Small |
| HTML | ⚠️ No | ✅ Excellent | ❌ No | ⚠️ Medium |
| JSON + HTML | ✅ Both | ✅ Both | ✅ Yes | ⚠️ Both |

**Rationale**:
1. **JSON Report**: Machine-readable for CI/CD parsing
2. **HTML Report**: Human-readable for debugging failures
3. **Both Formats**: Best of both worlds
4. **Self-Contained HTML**: Embeds CSS/JS, single file artifact
5. **Structured JSON**: Easy to parse for metrics/trending

**Implementation Pattern**:
```bash
pytest tests/integration/deployment/ \
    --json-report \
    --json-report-file=test-results.json \
    --html=test-report.html \
    --self-contained-html
```

**References**:
- pytest-json-report: https://github.com/numirias/pytest-json-report
- pytest-html: https://github.com/pytest-dev/pytest-html

---

## Test Execution Order

### Decision: Priority-Based Test Organization

**Research Questions**:
- Should fast tests run first (fail fast)?
- How to organize tests by criticality?
- What enables partial test runs in CI?

**Patterns Evaluated**:

| Pattern | Fail Fast | Partial Runs | Clear Intent | Flexibility |
|---------|-----------|--------------|--------------|-------------|
| Alphabetical | ❌ Random | ⚠️ Hard | ❌ No | ❌ No |
| By file (P1, P2) | ✅ Yes | ✅ Easy | ✅ Clear | ✅ Yes |
| Markers (@pytest.mark) | ⚠️ Config | ✅ Easy | ✅ Clear | ✅ Yes |

**Rationale**:
1. **File-Based Priority**: `test_p1_*.py` vs `test_p2_*.py`
2. **Sequential Execution**: P1 tests run first
3. **Fail Fast**: CI can stop after P1 failures
4. **Partial Runs**: `pytest test_p1_*.py` for quick validation
5. **Clear Intent**: Filename indicates criticality

**Implementation Pattern**:
```bash
# Run only Priority 1 (must pass for deployment)
pytest tests/integration/deployment/test_p1_*.py

# Run only Priority 2 (quality checks)
pytest tests/integration/deployment/test_p2_*.py

# Run all tests
pytest tests/integration/deployment/
```

**References**:
- pytest test selection: https://docs.pytest.org/en/stable/usage.html#specifying-tests-selecting-tests

---

## Summary

All technology decisions align with:
- **Existing Stack**: Python 3.11+, FastAPI, PostgreSQL, RabbitMQ
- **Industry Standards**: pytest, httpx, asyncpg
- **Best Practices**: Async-first, fixture-based cleanup, clear test organization
- **CI/CD Ready**: JSON + HTML reports, priority-based execution

Total research items: 7
Total technologies evaluated: 20+
Decision confidence: High
Implementation risk: Low
