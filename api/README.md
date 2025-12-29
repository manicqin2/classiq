# Quantum Circuit Task Queue API

Production-ready REST API server for quantum circuit task management with PostgreSQL persistence and RabbitMQ message queue.

## Quick Start

### Local Development with Docker Compose (Recommended)

The fastest way to get started with the complete system including database and message queue:

1. **Start all services:**
   ```bash
   # From repository root
   docker-compose up -d
   ```

   This starts:
   - PostgreSQL 15 database
   - RabbitMQ 3.12 message broker
   - API server (FastAPI)
   - Worker process (task consumer)

2. **Run database migrations:**
   ```bash
   docker-compose exec api alembic upgrade head
   ```

3. **Verify health:**
   ```bash
   curl http://localhost:8001/health | jq
   ```

4. **Access services:**
   - API: http://localhost:8001
   - Interactive API Docs: http://localhost:8001/docs
   - RabbitMQ Management UI: http://localhost:15672 (guest/guest)

For detailed workflows, see the [Developer Quickstart Guide](../specs/003-persistence-message-queue/quickstart.md).

### Standalone API Development

For API-only development without database/queue:

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables:**
   ```bash
   export DATABASE_URL="postgresql://user:pass@localhost:5432/quantum_db"
   export RABBITMQ_URL="amqp://user:pass@localhost:5672/"
   ```

3. **Run the server:**
   ```bash
   uvicorn app:app --reload --port 8000
   ```

4. **Access the API:**
   - API: http://localhost:8000
   - Interactive Docs: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## Database Setup

### PostgreSQL Connection

The API uses PostgreSQL for persistent storage of tasks and status history.

**Connection URL Format:**
```
postgresql://username:password@host:port/database
```

**Docker Compose (default):**
```bash
DATABASE_URL=postgresql://quantum_user:quantum_pass@postgres:5432/quantum_db
```

**Local PostgreSQL:**
```bash
DATABASE_URL=postgresql://quantum_user:quantum_pass@localhost:5432/quantum_db
```

### Running Migrations

The API uses Alembic for database schema migrations.

**Apply all migrations:**
```bash
# In Docker
docker-compose exec api alembic upgrade head

# Locally
alembic upgrade head
```

**Create new migration:**
```bash
# After modifying SQLAlchemy models
docker-compose exec api alembic revision --autogenerate -m "description"
```

**View migration history:**
```bash
docker-compose exec api alembic current
docker-compose exec api alembic history
```

**Rollback last migration:**
```bash
docker-compose exec api alembic downgrade -1
```

### Database Schema Overview

The database schema consists of two main tables:

**`tasks` table:**
- `task_id` (UUID): Primary key, unique task identifier
- `circuit` (TEXT): OpenQASM 3 circuit definition
- `submitted_at` (TIMESTAMP): Task submission time (auto-generated)
- `current_status` (ENUM): Current task status (pending, processing, completed, failed)
- `completed_at` (TIMESTAMP): Task completion time (nullable)
- `result` (JSONB): Task execution results (nullable)
- `error_message` (TEXT): Error details if failed (nullable)

**`status_history` table:**
- `id` (INTEGER): Auto-incrementing primary key
- `task_id` (UUID): Foreign key to tasks table
- `status` (ENUM): Status at this transition
- `transitioned_at` (TIMESTAMP): Time of status change
- `notes` (TEXT): Optional notes about the transition

**Indexes:**
- `idx_task_status`: Fast lookup by task status
- `idx_task_submitted_at`: Fast lookup by submission time
- `idx_status_history_task_time`: Fast lookup of status history by task and time

### Accessing the Database

**Using psql in Docker:**
```bash
docker-compose exec postgres psql -U quantum_user -d quantum_db
```

**Sample queries:**
```sql
-- List recent tasks
SELECT task_id, current_status, submitted_at
FROM tasks
ORDER BY submitted_at DESC
LIMIT 10;

-- View status history for a task
SELECT *
FROM status_history
WHERE task_id = '550e8400-e29b-41d4-a716-446655440000'
ORDER BY transitioned_at;

-- Count tasks by status
SELECT current_status, COUNT(*)
FROM tasks
GROUP BY current_status;
```

## Message Queue Setup

### RabbitMQ Connection

The API uses RabbitMQ for asynchronous task processing.

**Connection URL Format:**
```
amqp://username:password@host:port/vhost
```

**Docker Compose (default):**
```bash
RABBITMQ_URL=amqp://quantum_user:quantum_pass@rabbitmq:5672/
```

**Local RabbitMQ:**
```bash
RABBITMQ_URL=amqp://quantum_user:quantum_pass@localhost:5672/
```

### Queue Configuration

**Queue name:** `quantum_tasks`

**Message properties:**
- **Durable:** Yes (survives broker restart)
- **Auto-delete:** No
- **Message format:** JSON

**Message schema:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "circuit": "OPENQASM 3; qubit q; h q; measure q;"
}
```

### RabbitMQ Management UI

Access the web-based management interface to monitor queues and messages:

1. **URL:** http://localhost:15672
2. **Default credentials:** guest/guest (development only)
3. **Navigate to:** Queues tab > `quantum_tasks` queue

**Available actions:**
- View message count and rates
- Monitor consumer count
- Purge queue (delete all messages)
- Get messages (peek at content without consuming)

### Worker Deployment

The worker process consumes messages from RabbitMQ and processes tasks.

**Start worker with Docker Compose:**
```bash
docker-compose up -d worker
```

**Scale workers for parallel processing:**
```bash
# Run 3 workers concurrently
docker-compose up -d --scale worker=3
```

**View worker logs:**
```bash
docker-compose logs -f worker
```

**Worker responsibilities:**
1. Connect to RabbitMQ and consume from `quantum_tasks` queue
2. Deserialize task messages
3. Update task status to "processing" in database
4. Execute quantum circuit simulation
5. Store results in database
6. Update task status to "completed" or "failed"
7. Acknowledge message to RabbitMQ

## Environment Variables

### API Server Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | 8000 | HTTP server port |
| `LOG_LEVEL` | INFO | Logging verbosity (DEBUG, INFO, WARN, ERROR) |
| `ENVIRONMENT` | development | Environment name (development, staging, production) |
| `CORS_ORIGINS` | * | Allowed CORS origins (comma-separated) |
| `DATABASE_URL` | (required) | PostgreSQL connection string (format: `postgresql://user:pass@host:port/db`) |
| `RABBITMQ_URL` | (required) | RabbitMQ connection string (format: `amqp://user:pass@host:port/vhost`) |

### Database Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_USER` | quantum_user | Database username |
| `POSTGRES_PASSWORD` | quantum_pass | Database password (CHANGE IN PRODUCTION!) |
| `POSTGRES_DB` | quantum_db | Database name |

### RabbitMQ Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `RABBITMQ_DEFAULT_USER` | quantum_user | RabbitMQ username |
| `RABBITMQ_DEFAULT_PASS` | quantum_pass | RabbitMQ password (CHANGE IN PRODUCTION!) |

### Example .env File

Create a `.env` file in the project root (see `.env.example`):

```bash
# Server
PORT=8000
LOG_LEVEL=INFO
ENVIRONMENT=development
CORS_ORIGINS=*

# Database
DATABASE_URL=postgresql://quantum_user:quantum_pass@localhost:5432/quantum_db

# Message Queue
RABBITMQ_URL=amqp://quantum_user:quantum_pass@localhost:5672/
```

## API Endpoints

### POST /tasks
Submit a quantum circuit for execution.

**Request:**
```json
{
  "circuit": "OPENQASM 3; qubit q; h q; measure q;"
}
```

**Response:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Task submitted successfully.",
  "correlation_id": "abc123-def456"
}
```

### GET /tasks/{task_id}
Query task status and results.

**Response:**
```json
{
  "status": "pending",
  "message": "Task is still in progress.",
  "correlation_id": "xyz789-uvw456"
}
```

### GET /health
Health check for monitoring.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-12-28T12:00:00Z"
}
```

## Troubleshooting

### Database Connection Issues

**Symptom:** API fails to start with "connection refused" or "could not connect to server"

**Solutions:**

1. **Verify PostgreSQL is running:**
   ```bash
   docker-compose ps postgres
   # Should show "Up" status
   ```

2. **Check PostgreSQL health:**
   ```bash
   docker-compose logs postgres
   # Look for "database system is ready to accept connections"
   ```

3. **Verify connection string:**
   ```bash
   # Ensure DATABASE_URL uses correct host:
   # - Docker: use service name "postgres"
   # - Local: use "localhost"
   echo $DATABASE_URL
   ```

4. **Test connection manually:**
   ```bash
   docker-compose exec postgres psql -U quantum_user -d quantum_db -c "SELECT 1;"
   # Should return "1" if connection works
   ```

5. **Restart database:**
   ```bash
   docker-compose restart postgres
   ```

### RabbitMQ Connection Issues

**Symptom:** API returns 503 errors, logs show "Failed to connect to RabbitMQ"

**Solutions:**

1. **Verify RabbitMQ is running:**
   ```bash
   docker-compose ps rabbitmq
   # Should show "Up" status
   ```

2. **Check RabbitMQ health:**
   ```bash
   docker-compose logs rabbitmq
   # Look for "Server startup complete"
   ```

3. **Verify connection string:**
   ```bash
   # Ensure RABBITMQ_URL uses correct host:
   # - Docker: use service name "rabbitmq"
   # - Local: use "localhost"
   echo $RABBITMQ_URL
   ```

4. **Check RabbitMQ management UI:**
   - Open http://localhost:15672
   - Login with guest/guest
   - Verify "Overview" shows green status

5. **Restart RabbitMQ:**
   ```bash
   docker-compose restart rabbitmq
   ```

### Migration Errors

**Symptom:** "relation does not exist" or "table not found"

**Solution:**
```bash
# Run migrations
docker-compose exec api alembic upgrade head

# Verify tables exist
docker-compose exec postgres psql -U quantum_user -d quantum_db -c "\dt"
# Should show: tasks, status_history, alembic_version
```

**Symptom:** "Target database is not up to date"

**Solution:**
```bash
# Check current version
docker-compose exec api alembic current

# View migration history
docker-compose exec api alembic history

# Upgrade to latest
docker-compose exec api alembic upgrade head
```

### Tasks Stuck in "pending" Status

**Symptom:** Tasks never transition to "processing"

**Solutions:**

1. **Verify worker is running:**
   ```bash
   docker-compose ps worker
   # Should show "Up" status
   ```

2. **Check worker logs:**
   ```bash
   docker-compose logs worker
   # Look for "Connected to RabbitMQ" and "Started consuming"
   ```

3. **Check queue has consumers:**
   - Open http://localhost:15672
   - Navigate to Queues > quantum_tasks
   - "Consumers" column should show count > 0

4. **Verify messages in queue:**
   - Check "Messages" column in RabbitMQ UI
   - If messages are piling up but not being consumed, restart worker:
   ```bash
   docker-compose restart worker
   ```

### Port Conflicts

**Symptom:** "address already in use" when starting services

**Solutions:**

**API port (8001) conflict:**
```yaml
# Edit docker-compose.yml
services:
  api:
    ports:
      - "8002:8000"  # Change external port
```

**PostgreSQL port (5432) conflict:**
```yaml
# Edit docker-compose.yml
services:
  postgres:
    ports:
      - "5433:5432"  # Change external port

# Update DATABASE_URL:
DATABASE_URL=postgresql://quantum_user:quantum_pass@localhost:5433/quantum_db
```

**RabbitMQ ports (5672, 15672) conflict:**
```yaml
# Edit docker-compose.yml
services:
  rabbitmq:
    ports:
      - "5673:5672"
      - "15673:15672"

# Update RABBITMQ_URL:
RABBITMQ_URL=amqp://quantum_user:quantum_pass@localhost:5673/
```

### Worker Crashes or Restarts

**Symptom:** Worker container constantly restarting

**Solutions:**

1. **Check worker logs for errors:**
   ```bash
   docker-compose logs --tail=50 worker
   ```

2. **Common issues:**
   - Database connection failure: Verify DATABASE_URL
   - RabbitMQ connection failure: Verify RABBITMQ_URL
   - Invalid circuit syntax: Check task input validation

3. **Restart with fresh state:**
   ```bash
   docker-compose stop worker
   docker-compose up -d worker
   ```

### Health Check Failures

**Symptom:** `/health` endpoint returns unhealthy status

**Response example:**
```json
{
  "status": "unhealthy",
  "database_status": "disconnected",
  "queue_status": "connected",
  "timestamp": "2025-12-29T10:00:00Z"
}
```

**Solutions:**

1. **Check component status:**
   - `database_status: "disconnected"` - See "Database Connection Issues"
   - `queue_status: "disconnected"` - See "RabbitMQ Connection Issues"

2. **Verify all services healthy:**
   ```bash
   docker-compose ps
   # All services should show "healthy" in STATUS column
   ```

3. **Restart unhealthy services:**
   ```bash
   docker-compose restart postgres rabbitmq api
   ```

## Testing

Run unit tests:
```bash
pytest tests/unit/ -v
```

Run integration tests:
```bash
./tests/integration/test-api.sh
```

## Architecture

- **Framework:** FastAPI with async/await
- **Database:** PostgreSQL 15 with SQLAlchemy (async)
- **Migrations:** Alembic for schema version control
- **Message Queue:** RabbitMQ 3.12 with Pika client
- **Validation:** Pydantic v2
- **Logging:** structlog (structured JSON)
- **Container:** Docker with non-root user
- **Health Checks:** Built-in liveness/readiness probes with database and queue status
- **Worker:** Async task consumer with error handling and retry logic

## Development

### Project Structure

```
api/
├── app.py                 # Main FastAPI application
├── config.py              # Configuration from environment
├── models.py              # Pydantic request/response models
├── routes.py              # API endpoint handlers
├── middleware.py          # Correlation ID middleware
├── logging_config.py      # Structured logging setup
├── utils.py               # Utility functions
├── Dockerfile             # Container image definition
├── requirements.txt       # Python dependencies
└── tests/                 # Test suite
```

### Adding New Endpoints

1. Define Pydantic models in `models.py`
2. Implement handler in `routes.py`
3. FastAPI automatically generates OpenAPI docs

## Additional Resources

- **Developer Quickstart Guide:** [specs/003-persistence-message-queue/quickstart.md](../specs/003-persistence-message-queue/quickstart.md)
  - Complete walkthrough of local development setup
  - Step-by-step examples of submitting and querying tasks
  - Database and queue management workflows
  - Testing failure scenarios

- **API Specification:** [specs/003-persistence-message-queue/contracts/openapi.yaml](../specs/003-persistence-message-queue/contracts/openapi.yaml)
  - Complete OpenAPI 3.0 specification
  - Request/response schemas
  - Error handling documentation

- **Data Model Documentation:** [specs/003-persistence-message-queue/data-model.md](../specs/003-persistence-message-queue/data-model.md)
  - Detailed database schema
  - Entity relationships
  - Status transition diagrams

- **Implementation Plan:** [specs/003-persistence-message-queue/plan.md](../specs/003-persistence-message-queue/plan.md)
  - Architecture decisions
  - Technology choices
  - Integration patterns

- **Docker Compose Configuration:** [docker-compose.yml](../docker-compose.yml)
  - Service definitions
  - Environment variables
  - Health check configurations

## License

MIT
