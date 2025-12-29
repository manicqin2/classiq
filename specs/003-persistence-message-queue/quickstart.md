# Developer Quickstart: Persistence Layer and Message Queue Integration

**Feature**: 003-persistence-message-queue
**Date**: 2025-12-28
**Prerequisites**: Docker, Docker Compose, curl (for testing)

## Overview

This guide walks you through setting up the full quantum circuit task queue system with persistence and asynchronous processing on your local machine. You'll run:

- **API Server** (FastAPI): Accepts task submissions, persists to database, publishes to queue
- **Worker** (Python): Consumes queue messages, processes tasks, updates database
- **PostgreSQL**: Stores tasks and status history
- **RabbitMQ**: Message queue for task distribution

---

## Quick Start (5 Minutes)

### 1. Start All Services

```bash
# From repository root
docker-compose up -d
```

This starts 4 services:
- `postgres`: PostgreSQL 15 database
- `rabbitmq`: RabbitMQ 3.12 message broker
- `api`: FastAPI REST API server
- `worker`: Task processing worker

### 2. Run Database Migrations

```bash
# Apply schema migrations
docker-compose exec api alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 001, create tasks and status_history tables
```

### 3. Verify Health

```bash
curl http://localhost:8001/health | jq
```

Expected response:
```json
{
  "status": "healthy",
  "database_status": "connected",
  "queue_status": "connected",
  "timestamp": "2025-12-28T14:30:00Z"
}
```

### 4. Submit a Task

```bash
curl -X POST http://localhost:8001/tasks \
  -H "Content-Type: application/json" \
  -d '{"circuit": "OPENQASM 3; qubit q; h q; measure q;"}' \
  | jq
```

Expected response:
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "submitted_at": "2025-12-28T14:30:00.123Z",
  "message": "Task submitted successfully.",
  "correlation_id": "abc123-def456-789012"
}
```

**Save the `task_id` for the next step!**

### 5. Check Task Status

```bash
# Replace with your task_id from step 4
TASK_ID="550e8400-e29b-41d4-a716-446655440000"
curl http://localhost:8001/tasks/$TASK_ID | jq
```

Expected response (initially):
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "submitted_at": "2025-12-28T14:30:00.123Z",
  "status_history": [
    {
      "status": "pending",
      "transitioned_at": "2025-12-28T14:30:00.123Z",
      "notes": "Task created"
    }
  ],
  "correlation_id": "xyz789-uvw456"
}
```

Wait a few seconds and check again - status should transition to `processing`, then `completed`:

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "submitted_at": "2025-12-28T14:30:00.123Z",
  "completed_at": "2025-12-28T14:30:12.789Z",
  "result": {
    "0": 512,
    "1": 512
  },
  "status_history": [
    {
      "status": "pending",
      "transitioned_at": "2025-12-28T14:30:00.123Z",
      "notes": "Task created"
    },
    {
      "status": "processing",
      "transitioned_at": "2025-12-28T14:30:05.456Z",
      "notes": "Worker started processing"
    },
    {
      "status": "completed",
      "transitioned_at": "2025-12-28T14:30:12.789Z",
      "notes": "Task completed successfully"
    }
  ],
  "correlation_id": "xyz789-uvw456"
}
```

### 6. View Logs

```bash
# All services
docker-compose logs -f

# Just API
docker-compose logs -f api

# Just worker
docker-compose logs -f worker
```

### 7. Verify Persistence (Optional)

```bash
# Restart all services
docker-compose restart api worker

# Check task again - it should still exist!
curl http://localhost:8001/tasks/$TASK_ID | jq
```

✅ **Success!** Task persists across restarts.

---

## Service Details

### API Server

- **URL**: http://localhost:8001
- **Endpoints**:
  - `POST /tasks` - Submit task
  - `GET /tasks/{task_id}` - Get status
  - `GET /health` - Health check
- **Logs**: `docker-compose logs -f api`
- **Container**: `api`

### Worker Process

- **Purpose**: Consumes queue messages, processes tasks, updates database
- **Logs**: `docker-compose logs -f worker`
- **Container**: `worker`
- **Scaling**: Run multiple workers with `docker-compose up -d --scale worker=3`

### PostgreSQL Database

- **Host**: localhost
- **Port**: 5432
- **Database**: `quantum_tasks`
- **User**: `postgres`
- **Password**: `postgres` (development only!)
- **Container**: `postgres`

### RabbitMQ Message Queue

- **AMQP URL**: amqp://guest:guest@localhost:5672/
- **Management UI**: http://localhost:15672
  - **Username**: guest
  - **Password**: guest
- **Container**: `rabbitmq`

---

## Development Workflows

### Accessing the Database

**Using psql in container**:
```bash
docker-compose exec postgres psql -U postgres -d quantum_tasks
```

**Sample queries**:
```sql
-- List all tasks
SELECT task_id, current_status, submitted_at FROM tasks ORDER BY submitted_at DESC LIMIT 10;

-- View status history for a task
SELECT * FROM status_history WHERE task_id = '550e8400-e29b-41d4-a716-446655440000' ORDER BY transitioned_at;

-- Count tasks by status
SELECT current_status, COUNT(*) FROM tasks GROUP BY current_status;
```

**Exit psql**: `\q`

### Accessing RabbitMQ Management UI

1. Open http://localhost:15672 in browser
2. Login with `guest` / `guest`
3. Navigate to **Queues** tab
4. View `quantum_tasks` queue:
   - Message count
   - Consumer count
   - Message rates

**Useful actions**:
- **Purge Queue**: Delete all pending messages (testing)
- **Get Messages**: Peek at message content (non-destructive)

### Running Database Migrations

**Create a new migration** (after modifying SQLAlchemy models):
```bash
docker-compose exec api alembic revision --autogenerate -m "add new field"
```

**Apply migrations**:
```bash
docker-compose exec api alembic upgrade head
```

**Rollback last migration**:
```bash
docker-compose exec api alembic downgrade -1
```

**View migration history**:
```bash
docker-compose exec api alembic history
docker-compose exec api alembic current
```

### Scaling Workers

**Run 3 workers concurrently**:
```bash
docker-compose up -d --scale worker=3
```

**Verify all workers consuming**:
```bash
# Check RabbitMQ management UI - "Consumers" column should show 3
# Or check logs:
docker-compose logs worker | grep "consuming"
```

### Testing Failure Scenarios

**Simulate database failure**:
```bash
# Stop database
docker-compose stop postgres

# Try to submit task - should return 503
curl -X POST http://localhost:8001/tasks \
  -H "Content-Type: application/json" \
  -d '{"circuit": "test"}' \
  -w "\nHTTP Status: %{http_code}\n"

# Restart database
docker-compose start postgres
```

**Simulate queue failure**:
```bash
# Stop RabbitMQ
docker-compose stop rabbitmq

# Try to submit task - should return 503
curl -X POST http://localhost:8001/tasks \
  -H "Content-Type: application/json" \
  -d '{"circuit": "test"}' \
  -w "\nHTTP Status: %{http_code}\n"

# Restart queue
docker-compose start rabbitmq
```

**Simulate worker crash**:
```bash
# Kill all workers
docker-compose stop worker

# Submit tasks - they will queue up
curl -X POST http://localhost:8001/tasks \
  -H "Content-Type: application/json" \
  -d '{"circuit": "task 1"}'

curl -X POST http://localhost:8001/tasks \
  -H "Content-Type: application/json" \
  -d '{"circuit": "task 2"}'

# Check RabbitMQ - should show 2 messages in queue

# Restart workers - tasks should be processed
docker-compose start worker
```

---

## Environment Configuration

### API Configuration

Edit `docker-compose.yml` or create `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | 8000 | API server port (inside container) |
| `LOG_LEVEL` | INFO | Logging level (DEBUG, INFO, WARN, ERROR) |
| `DATABASE_URL` | postgresql+asyncpg://postgres:postgres@postgres/quantum_tasks | Database connection string |
| `RABBITMQ_URL` | amqp://guest:guest@rabbitmq:5672/ | RabbitMQ connection string |
| `CORS_ORIGINS` | * | Allowed CORS origins |

### Database Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_USER` | postgres | Database user |
| `POSTGRES_PASSWORD` | postgres | Database password (CHANGE IN PRODUCTION!) |
| `POSTGRES_DB` | quantum_tasks | Database name |

### RabbitMQ Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `RABBITMQ_DEFAULT_USER` | guest | RabbitMQ user |
| `RABBITMQ_DEFAULT_PASS` | guest | RabbitMQ password (CHANGE IN PRODUCTION!) |

---

## Troubleshooting

### "Connection refused" errors

**Symptom**: API returns 503, logs show database/queue connection errors

**Solution**:
```bash
# Check all services running
docker-compose ps

# Restart failed services
docker-compose restart postgres rabbitmq

# View logs for errors
docker-compose logs postgres
docker-compose logs rabbitmq
```

### Migrations not applied

**Symptom**: API crashes with "table does not exist" error

**Solution**:
```bash
# Run migrations
docker-compose exec api alembic upgrade head

# Verify tables exist
docker-compose exec postgres psql -U postgres -d quantum_tasks -c "\dt"
```

### Tasks stuck in "pending"

**Symptom**: Tasks never transition to "processing"

**Check worker is running**:
```bash
docker-compose ps worker

# If not running:
docker-compose up -d worker
```

**Check worker logs**:
```bash
docker-compose logs worker

# Look for:
# - "Connected to RabbitMQ"
# - "Started consuming messages"
```

**Check queue has messages**:
- Open http://localhost:15672
- Navigate to Queues → `quantum_tasks`
- Should show message count and consumer count

### Port conflicts

**Symptom**: "port already in use" error when starting services

**Solution**:
```bash
# API port conflict (8001)
# Edit docker-compose.yml, change "8001:8000" to "8002:8000"

# PostgreSQL port conflict (5432)
# Edit docker-compose.yml, change "5432:5432" to "5433:5432"
# Update DATABASE_URL to use localhost:5433

# RabbitMQ port conflict (5672, 15672)
# Edit docker-compose.yml, change port mappings
```

---

## Next Steps

1. ✅ **Run integration tests**: `docker-compose exec api pytest tests/integration/`
2. ✅ **Explore RabbitMQ UI**: View message flow in real-time
3. ✅ **Test persistence**: Submit tasks, restart services, verify tasks persist
4. ✅ **Scale workers**: Run `docker-compose up -d --scale worker=5`
5. ✅ **View API docs**: Open http://localhost:8001/docs (Swagger UI)

---

## Clean Up

### Stop all services

```bash
docker-compose down
```

### Remove all data (database, queue)

```bash
docker-compose down -v
```

**Warning**: This deletes all tasks and messages!

### Remove images

```bash
docker-compose down --rmi all -v
```

---

## References

- **OpenAPI Spec**: `specs/003-persistence-message-queue/contracts/openapi.yaml`
- **Data Model**: `specs/003-persistence-message-queue/data-model.md`
- **Research Decisions**: `specs/003-persistence-message-queue/research.md`
- **Implementation Plan**: `specs/003-persistence-message-queue/plan.md`

---

**Happy Coding!** For questions or issues, check the project documentation or open an issue on GitHub.
