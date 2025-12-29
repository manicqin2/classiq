# Quickstart Guide: Deployment Integration Tests

**Feature**: 004-deployment-integration-tests
**Last Updated**: 2025-12-29

## Overview

This guide provides step-by-step instructions for running the deployment integration tests locally and in CI/CD environments. These tests validate that all system components (API, worker, database, message queue) are properly configured and functioning.

## Prerequisites

### Required Software

- **Docker** 20.10+ and **Docker Compose** 2.0+
- **Python** 3.11+
- **Git** for repository access

### Required Services

The tests require a running deployment with all services:
- FastAPI application (port 8001)
- PostgreSQL database (port 5432)
- RabbitMQ message broker (ports 5672, 15672)
- Worker process

## Quick Start (Local Development)

### Step 1: Start Services

```bash
# From repository root
cd /Users/bzpysmn/work/classiq/api

# Start all services with Docker Compose
docker-compose up -d

# Verify services are healthy
docker-compose ps
```

**Expected output**:
```
NAME               STATUS             PORTS
quantum-api        Up (healthy)       0.0.0.0:8001->8000/tcp
quantum-postgres   Up (healthy)       0.0.0.0:5432->5432/tcp
quantum-rabbitmq   Up (healthy)       0.0.0.0:5672->5672/tcp, 0.0.0.0:15672->15672/tcp
classiq-worker-1   Up (healthy)       -
```

### Step 2: Install Test Dependencies

```bash
# Create virtual environment (optional but recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install test dependencies
pip install -r tests/requirements-test.txt
```

**Test dependencies** (tests/requirements-test.txt):
```
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-html==4.1.1
pytest-json-report==1.5.0
httpx==0.25.0
asyncpg==0.29.0
```

### Step 3: Run Tests

```bash
# Run all deployment integration tests
pytest tests/integration/deployment/ -v

# Run only Priority 1 tests (critical for deployment)
pytest tests/integration/deployment/test_p1_*.py -v

# Run only Priority 2 tests (quality checks)
pytest tests/integration/deployment/test_p2_*.py -v
```

**Expected output**:
```
================= test session starts =================
collected 10 items

test_p1_health.py::test_api_health_check PASSED       [ 10%]
test_p1_health.py::test_database_connectivity PASSED  [ 20%]
test_p1_health.py::test_rabbitmq_connectivity PASSED  [ 30%]
test_p1_e2e_workflow.py::test_complete_task_workflow PASSED [ 40%]
test_p2_schema.py::test_required_tables_exist PASSED  [ 50%]
test_p2_schema.py::test_tasks_table_schema PASSED     [ 60%]
test_p2_schema.py::test_indexes_exist PASSED          [ 70%]
test_p2_queue.py::test_quantum_tasks_queue_exists PASSED [ 80%]
test_p2_queue.py::test_queue_has_consumers PASSED     [ 90%]
test_p2_error_handling.py::test_invalid_task_returns_400 PASSED [100%]

================= 10 passed in 12.34s =================
```

## Configuration

### Environment Variables

Tests read configuration from environment variables. Defaults work for local docker-compose setup.

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

### Custom Configuration File

Create `.env.test` file for persistent configuration:

```bash
# .env.test
TEST_API_URL=http://localhost:8001
TEST_DATABASE_URL=postgresql://quantum_user:quantum_pass@localhost:5432/quantum_db
TEST_RABBITMQ_URL=amqp://quantum_user:quantum_pass@localhost:5672/
TEST_RABBITMQ_MGMT_URL=http://localhost:15672
TEST_RABBITMQ_USER=guest
TEST_RABBITMQ_PASS=guest
TEST_TIMEOUT=30
TEST_POLL_INTERVAL=0.5
```

Load configuration before running tests:
```bash
# Load environment variables
set -a
source .env.test
set +a

# Run tests
pytest tests/integration/deployment/
```

## Test Reports

### HTML Report

Generate human-readable HTML report:

```bash
pytest tests/integration/deployment/ \
    --html=test-report.html \
    --self-contained-html
```

Open `test-report.html` in browser to view:
- Test summary (passed/failed/skipped)
- Execution times
- Failure details with stack traces
- Environment information

### JSON Report (for CI/CD)

Generate machine-readable JSON report:

```bash
pytest tests/integration/deployment/ \
    --json-report \
    --json-report-file=test-results.json
```

JSON structure:
```json
{
  "created": "2025-12-29T10:00:00",
  "duration": 12.34,
  "exitcode": 0,
  "root": "/Users/bzpysmn/work/classiq/api",
  "environment": {
    "Python": "3.11.6",
    "Platform": "macOS-14.0-arm64"
  },
  "summary": {
    "passed": 10,
    "failed": 0,
    "total": 10
  },
  "tests": [
    {
      "nodeid": "test_p1_health.py::test_api_health_check",
      "outcome": "passed",
      "duration": 0.123
    }
  ]
}
```

### Combined Reports

Generate both HTML and JSON reports in one run:

```bash
pytest tests/integration/deployment/ \
    --html=test-report.html \
    --self-contained-html \
    --json-report \
    --json-report-file=test-results.json \
    -v
```

## Running Specific Tests

### By Priority

```bash
# Only Priority 1 (critical deployment validation)
pytest tests/integration/deployment/test_p1_*.py

# Only Priority 2 (quality checks)
pytest tests/integration/deployment/test_p2_*.py
```

### By Test Function

```bash
# Run specific test function
pytest tests/integration/deployment/test_p1_health.py::test_api_health_check

# Run all tests in a file
pytest tests/integration/deployment/test_p1_e2e_workflow.py
```

### By Keyword

```bash
# Run tests matching keyword
pytest tests/integration/deployment/ -k "health"

# Run tests NOT matching keyword
pytest tests/integration/deployment/ -k "not schema"
```

## Troubleshooting

### Services Not Ready

**Problem**: Tests fail with connection errors

**Solution**:
```bash
# Check service status
docker-compose ps

# View service logs
docker-compose logs api
docker-compose logs worker
docker-compose logs postgres
docker-compose logs rabbitmq

# Restart services
docker-compose restart api worker

# Wait for health checks
timeout 60 bash -c 'until curl -f http://localhost:8001/health; do sleep 1; done'
```

### Database Connection Failed

**Problem**: `asyncpg.exceptions.InvalidCatalogNameError: database "quantum_db" does not exist`

**Solution**:
```bash
# Check if database exists
docker-compose exec postgres psql -U quantum_user -l

# Create database if missing
docker-compose exec postgres psql -U quantum_user -c "CREATE DATABASE quantum_db;"

# Run migrations
docker-compose exec api alembic upgrade head
```

### RabbitMQ Queue Not Found

**Problem**: `test_quantum_tasks_queue_exists` fails

**Solution**:
```bash
# Check queue exists in RabbitMQ UI
open http://localhost:15672
# Login: guest/guest
# Navigate to Queues tab

# Restart worker to recreate queue
docker-compose restart worker

# Wait 5 seconds for queue declaration
sleep 5
```

### Tests Timeout Waiting for Task Completion

**Problem**: `TimeoutError: Task did not complete in 30s`

**Solution**:
```bash
# Check worker is running
docker-compose ps worker

# Check worker logs
docker-compose logs worker --tail=50

# Increase timeout
export TEST_TIMEOUT=60

# Run single test with verbose output
pytest tests/integration/deployment/test_p1_e2e_workflow.py -v -s
```

### Port Already in Use

**Problem**: Services fail to start due to port conflicts

**Solution**:
```bash
# Find process using port 8001
lsof -i :8001

# Kill process if safe
kill <PID>

# Or change ports in docker-compose.yml
# Edit ports section:
#   ports:
#     - "8002:8000"  # Changed from 8001

# Update TEST_API_URL
export TEST_API_URL="http://localhost:8002"
```

## CI/CD Integration

### GitHub Actions Example

Create `.github/workflows/integration-tests.yml`:

```yaml
name: Integration Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Start services
        run: docker-compose up -d

      - name: Wait for services
        run: |
          timeout 60 bash -c 'until curl -f http://localhost:8001/health; do sleep 1; done'

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install test dependencies
        run: pip install -r tests/requirements-test.txt

      - name: Run Priority 1 tests
        run: |
          pytest tests/integration/deployment/test_p1_*.py \
            --json-report \
            --json-report-file=test-results-p1.json \
            --html=test-report-p1.html \
            --self-contained-html

      - name: Run Priority 2 tests
        run: |
          pytest tests/integration/deployment/test_p2_*.py \
            --json-report \
            --json-report-file=test-results-p2.json \
            --html=test-report-p2.html \
            --self-contained-html \
            --continue-on-collection-errors

      - name: Upload test reports
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: test-reports
          path: |
            test-results-*.json
            test-report-*.html

      - name: Shutdown services
        if: always()
        run: docker-compose down -v
```

### GitLab CI Example

Create `.gitlab-ci.yml`:

```yaml
integration-tests:
  stage: test
  image: docker:latest
  services:
    - docker:dind

  variables:
    DOCKER_DRIVER: overlay2
    TEST_API_URL: "http://docker:8001"

  before_script:
    - apk add --no-cache python3 py3-pip curl bash
    - pip3 install -r tests/requirements-test.txt
    - docker-compose up -d
    - timeout 60 bash -c 'until curl -f http://localhost:8001/health; do sleep 1; done'

  script:
    # Priority 1 tests (must pass)
    - pytest tests/integration/deployment/test_p1_*.py
          --json-report --json-report-file=test-results-p1.json
          --html=test-report-p1.html --self-contained-html

    # Priority 2 tests (continue on error)
    - pytest tests/integration/deployment/test_p2_*.py
          --json-report --json-report-file=test-results-p2.json
          --html=test-report-p2.html --self-contained-html
          --continue-on-collection-errors || true

  after_script:
    - docker-compose down -v

  artifacts:
    when: always
    paths:
      - test-results-*.json
      - test-report-*.html
    reports:
      junit: test-results-*.json
```

## Best Practices

### 1. Always Start Fresh

```bash
# Stop existing services
docker-compose down -v

# Pull latest images
docker-compose pull

# Start services
docker-compose up -d

# Wait for health
timeout 60 bash -c 'until curl -f http://localhost:8001/health; do sleep 1; done'

# Run tests
pytest tests/integration/deployment/
```

### 2. Use Verbose Mode for Debugging

```bash
# Show test names and outcomes
pytest tests/integration/deployment/ -v

# Show print statements and logs
pytest tests/integration/deployment/ -v -s

# Show full diff on assertion failures
pytest tests/integration/deployment/ -v --tb=long
```

### 3. Run Fast Tests First

```bash
# Run health checks first (fast, catch config issues)
pytest tests/integration/deployment/test_p1_health.py

# Then run E2E tests (slower but comprehensive)
pytest tests/integration/deployment/test_p1_e2e_workflow.py

# Finally run schema/queue validation
pytest tests/integration/deployment/test_p2_*.py
```

### 4. Clean Up After Tests

Tests automatically clean up test data, but you can also clean manually:

```bash
# Remove test tasks from database
docker-compose exec postgres psql -U quantum_user quantum_db -c "
  DELETE FROM status_history WHERE task_id IN (
    SELECT task_id FROM tasks WHERE circuit LIKE '%test_%'
  );
  DELETE FROM tasks WHERE circuit LIKE '%test_%';
"

# Purge RabbitMQ queue
docker-compose exec rabbitmq rabbitmqctl purge_queue quantum_tasks
```

## Next Steps

After successfully running tests locally:

1. **Integrate into CI/CD**: Add tests to your continuous integration pipeline
2. **Monitor Test Results**: Track pass rates and execution times over deployments
3. **Expand Coverage**: Add Priority 3 tests for performance baselines
4. **Automate Validation**: Run tests automatically before production deployments

## Additional Resources

- **Full Implementation Plan**: [plan.md](plan.md)
- **Research Decisions**: [research.md](research.md)
- **Feature Specification**: [spec.md](spec.md)
- **Main API Documentation**: [../../README.md](../../api/README.md)
