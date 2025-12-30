# Deployment Integration Tests

Comprehensive integration tests for validating quantum task processing system deployments. These tests verify that API, database, message queue, and worker components are correctly configured and functioning together.

## Overview

These tests validate a complete deployment environment by testing:

- **Service Health**: API, database, and RabbitMQ connectivity
- **End-to-End Workflow**: Complete task lifecycle from submission to completion
- **Database Schema**: Correct table structure, indexes, and constraints
- **Queue Configuration**: RabbitMQ queue settings and consumer status
- **Error Handling**: Proper validation and error responses

## Test Organization

Tests are organized by **priority level** to support incremental validation:

### Priority 1 (P1) - Critical Tests

Must pass for deployment to be considered functional. These tests validate core system health and basic functionality.

**Files:**
- `test_p1_health.py` - Service health checks (API, database, RabbitMQ)
- `test_p1_e2e_workflow.py` - Complete task processing workflow

**Run P1 only:**
```bash
pytest tests/integration/deployment -m p1 -v
```

### Priority 2 (P2) - Quality Tests

Validate proper configuration and error handling. Failures are warnings that should be investigated but don't block deployment.

**Files:**
- `test_p2_schema.py` - Database schema validation
- `test_p2_queue.py` - RabbitMQ queue configuration
- `test_p2_error_handling.py` - API error handling and validation

**Run P2 only:**
```bash
pytest tests/integration/deployment -m p2 -v
```

## Quick Start

### 1. Prerequisites

- Python 3.11+
- Running deployment (API, database, RabbitMQ, worker)
- Test dependencies installed:

```bash
pip install -r tests/requirements-test.txt
```

### 2. Configure Environment

Set environment variables pointing to your deployment:

```bash
export TEST_API_URL="http://localhost:8001"
export TEST_DATABASE_URL="postgresql://quantum_user:quantum_pass@localhost:5432/quantum_db"
export TEST_RABBITMQ_URL="amqp://quantum_user:quantum_pass@localhost:5672/"
export TEST_RABBITMQ_MGMT_URL="http://localhost:15672"
export TEST_RABBITMQ_MGMT_USER="quantum_user"
export TEST_RABBITMQ_MGMT_PASS="quantum_pass"
```

Or create a `.env` file in the project root (not committed to git).

### 3. Run Tests

**All tests:**
```bash
pytest tests/integration/deployment -v
```

**Using the CI runner script:**
```bash
./tests/integration/deployment/run_tests.sh
```

The script will:
1. Wait for services to be healthy (120s timeout)
2. Run P1 tests (must pass)
3. Run P2 tests (failures are warnings)
4. Generate HTML and JSON reports

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TEST_API_URL` | API endpoint URL | `http://localhost:8001` |
| `TEST_DATABASE_URL` | PostgreSQL connection string | `postgresql://quantum_user:quantum_pass@localhost:5432/quantum_db` |
| `TEST_RABBITMQ_URL` | RabbitMQ AMQP URL | `amqp://quantum_user:quantum_pass@localhost:5672/` |
| `TEST_RABBITMQ_MGMT_URL` | RabbitMQ Management API URL | `http://localhost:15672` |
| `TEST_RABBITMQ_MGMT_USER` | RabbitMQ Management API username | `quantum_user` |
| `TEST_RABBITMQ_MGMT_PASS` | RabbitMQ Management API password | `quantum_pass` |
| `TEST_TIMEOUT` | Task processing timeout (seconds) | `30` |
| `TEST_POLL_INTERVAL` | Status polling interval (seconds) | `0.5` |

### Test Fixtures

Tests use shared fixtures defined in `conftest.py`:

- **`test_config`** - Loads environment configuration
- **`api_client`** - HTTP client for API endpoints
- **`db_client`** - Direct database access for validation
- **`queue_client`** - RabbitMQ Management API client
- **`cleanup_test_tasks`** - Automatic test data cleanup

## Running Tests Locally

### Against Docker Compose Deployment

If you have the system running via Docker Compose:

```bash
# Start the system
docker-compose up -d

# Wait for services to be ready
sleep 10

# Run tests
pytest tests/integration/deployment -v

# Or use the runner script
./tests/integration/deployment/run_tests.sh
```

### Against Kubernetes Deployment

For Kubernetes deployments, port-forward the required services:

```bash
# Port-forward API
kubectl port-forward svc/api 8001:8000 &

# Port-forward database
kubectl port-forward svc/postgres 5432:5432 &

# Port-forward RabbitMQ
kubectl port-forward svc/rabbitmq 5672:5672 15672:15672 &

# Run tests
pytest tests/integration/deployment -v
```

## CI/CD Integration

### Using the Runner Script

The `run_tests.sh` script is designed for CI/CD pipelines:

```bash
#!/bin/bash
# In your CI pipeline

# Set environment variables
export TEST_API_URL="http://api-service:8000"
export TEST_DATABASE_URL="postgresql://user:pass@db:5432/quantum_db"
# ... other variables

# Run tests
./tests/integration/deployment/run_tests.sh

# Exit code:
#   0 = All P1 tests passed
#   1 = P1 tests failed or services unhealthy
#   2 = Configuration error
```

### GitHub Actions Example

```yaml
name: Deployment Integration Tests

on:
  push:
    branches: [main]
  pull_request:

jobs:
  integration-tests:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: quantum_user
          POSTGRES_PASSWORD: quantum_pass
          POSTGRES_DB: quantum_db
        ports:
          - 5432:5432

      rabbitmq:
        image: rabbitmq:3.12-management
        env:
          RABBITMQ_DEFAULT_USER: quantum_user
          RABBITMQ_DEFAULT_PASS: quantum_pass
        ports:
          - 5672:5672
          - 15672:15672

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r tests/requirements-test.txt

      - name: Run database migrations
        run: alembic upgrade head
        env:
          DATABASE_URL: postgresql://quantum_user:quantum_pass@localhost:5432/quantum_db

      - name: Start API and Worker
        run: |
          python app.py &
          python worker.py &
          sleep 5

      - name: Run integration tests
        run: ./tests/integration/deployment/run_tests.sh
        env:
          TEST_API_URL: http://localhost:8001
          TEST_DATABASE_URL: postgresql://quantum_user:quantum_pass@localhost:5432/quantum_db
          TEST_RABBITMQ_URL: amqp://quantum_user:quantum_pass@localhost:5672/
          TEST_RABBITMQ_MGMT_URL: http://localhost:15672
          TEST_RABBITMQ_MGMT_USER: quantum_user
          TEST_RABBITMQ_MGMT_PASS: quantum_pass

      - name: Upload test reports
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: test-reports
          path: |
            test-results-*.json
            test-report-*.html
```

### GitLab CI Example

```yaml
integration-tests:
  stage: test
  image: python:3.11

  services:
    - name: postgres:15
      alias: postgres
    - name: rabbitmq:3.12-management
      alias: rabbitmq

  variables:
    POSTGRES_USER: quantum_user
    POSTGRES_PASSWORD: quantum_pass
    POSTGRES_DB: quantum_db
    RABBITMQ_DEFAULT_USER: quantum_user
    RABBITMQ_DEFAULT_PASS: quantum_pass

  before_script:
    - pip install -r requirements.txt
    - pip install -r tests/requirements-test.txt
    - alembic upgrade head

  script:
    - python app.py &
    - python worker.py &
    - sleep 5
    - ./tests/integration/deployment/run_tests.sh

  artifacts:
    when: always
    paths:
      - test-results-*.json
      - test-report-*.html
    reports:
      junit: test-results-p1.json

  variables:
    TEST_API_URL: http://localhost:8001
    TEST_DATABASE_URL: postgresql://quantum_user:quantum_pass@postgres:5432/quantum_db
    TEST_RABBITMQ_URL: amqp://quantum_user:quantum_pass@rabbitmq:5672/
    TEST_RABBITMQ_MGMT_URL: http://rabbitmq:15672
    TEST_RABBITMQ_MGMT_USER: quantum_user
    TEST_RABBITMQ_MGMT_PASS: quantum_pass
```

## Test Reports

Tests generate two types of reports:

### HTML Reports

Human-readable test results with full details:
- `test-report-p1.html` - Priority 1 test results
- `test-report-p2.html` - Priority 2 test results

Open in browser: `open test-report-p1.html`

### JSON Reports

Machine-readable results for CI/CD integration:
- `test-results-p1.json` - Priority 1 test results
- `test-results-p2.json` - Priority 2 test results

Parse with `jq`:
```bash
jq '.summary' test-results-p1.json
```

## Troubleshooting

### Tests Fail with Connection Errors

**Problem:** `httpx.ConnectError` or `asyncpg.exceptions.CannotConnectNowError`

**Solution:**
1. Verify services are running: `docker-compose ps`
2. Check `TEST_API_URL` and `TEST_DATABASE_URL` are correct
3. Wait longer for services: `./run_tests.sh --timeout 180`

### Health Check Times Out

**Problem:** "Services did not become healthy within 120s"

**Solution:**
1. Check API logs: `docker-compose logs api`
2. Verify database migrations ran: `docker-compose exec api alembic current`
3. Check RabbitMQ is accessible: `curl http://localhost:15672`
4. Increase timeout: `TEST_HEALTH_CHECK_TIMEOUT=300 ./run_tests.sh`

### E2E Workflow Test Fails

**Problem:** "Task did not complete within 30s"

**Solution:**
1. Verify worker is running: `docker-compose ps worker`
2. Check worker logs: `docker-compose logs worker`
3. Verify RabbitMQ has consumers: Check Management UI at http://localhost:15672
4. Increase timeout: `export TEST_TIMEOUT=60`

### Database Schema Tests Fail

**Problem:** "Column 'xyz' missing from table"

**Solution:**
1. Verify migrations ran: `docker-compose exec api alembic current`
2. Run migrations manually: `docker-compose exec api alembic upgrade head`
3. Check database directly: `docker-compose exec db psql -U quantum_user -d quantum_db`

### Queue Tests Fail

**Problem:** "quantum_tasks queue does not exist"

**Solution:**
1. Verify RabbitMQ Management API is accessible
2. Check credentials: `TEST_RABBITMQ_MGMT_USER` and `TEST_RABBITMQ_MGMT_PASS`
3. Verify queue was created: Check http://localhost:15672/#/queues
4. Restart worker to recreate queue: `docker-compose restart worker`

### P2 Tests Fail But P1 Pass

**Problem:** Priority 2 tests failing

**Impact:** Not critical - deployment is functional but may have configuration issues

**Action:**
1. Review P2 test failures to understand configuration gaps
2. Fix issues in next deployment iteration
3. P2 failures don't block deployment (warnings only)

## Test Development

### Adding New Tests

1. **Determine priority level**: P1 (critical) or P2 (quality)
2. **Create test file**: `test_p{1|2}_{category}.py`
3. **Mark with decorator**: `@pytest.mark.p1` or `@pytest.mark.p2`
4. **Use fixtures**: `api_client`, `db_client`, `queue_client`
5. **Add cleanup**: Use `cleanup_test_tasks` for test data

Example:
```python
import pytest

@pytest.mark.p1
@pytest.mark.asyncio
async def test_new_feature(api_client, cleanup_test_tasks):
    """Test description."""
    # Submit test task
    response = await api_client.submit_task("test circuit")
    task_id = response["task_id"]
    cleanup_test_tasks(task_id)  # Auto-cleanup

    # Validate behavior
    assert response["message"] == "Task submitted successfully."
```

### Running Specific Tests

```bash
# Single test function
pytest tests/integration/deployment/test_p1_health.py::test_api_health_check -v

# Single test file
pytest tests/integration/deployment/test_p1_health.py -v

# Tests matching pattern
pytest tests/integration/deployment -k "health" -v

# P1 tests only
pytest tests/integration/deployment -m p1 -v
```

## Architecture

```
tests/integration/deployment/
├── conftest.py                    # Shared fixtures and configuration
├── helpers/                       # Helper classes for test clients
│   ├── __init__.py
│   ├── api_client.py             # HTTP client for API endpoints
│   ├── db_client.py              # Direct database access
│   └── queue_client.py           # RabbitMQ Management API client
├── test_p1_health.py             # P1: Service health validation
├── test_p1_e2e_workflow.py       # P1: End-to-end task processing
├── test_p2_schema.py             # P2: Database schema validation
├── test_p2_queue.py              # P2: Queue configuration validation
├── test_p2_error_handling.py     # P2: API error handling validation
├── run_tests.sh                  # CI/CD test runner script
└── README.md                     # This file
```

## References

- **API Documentation**: See `README.md` in project root
- **Database Schema**: See `migrations/versions/001_create_tasks_table.py`
- **Queue Configuration**: See `src/queue/consumer.py` and `src/queue/publisher.py`
- **Worker Implementation**: See `worker.py`

## Support

For issues or questions:

1. Check this README's Troubleshooting section
2. Review test logs and error messages
3. Check service logs: `docker-compose logs <service>`
4. Open an issue in the project repository
