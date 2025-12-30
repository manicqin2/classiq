# Quantum Circuit Task Queue

Asynchronous quantum circuit execution system with REST API, persistent task queue, and horizontal worker scaling.

## Architecture

```mermaid
graph LR
    Client([Client]) -->|HTTP| API[FastAPI Server]
    API -->|Persist| DB[(PostgreSQL)]
    API -->|Publish| Queue[RabbitMQ]
    Queue -->|Consume| W1[Worker 1]
    Queue -->|Consume| W2[Worker 2]
    Queue -->|Consume| W3[Worker 3]
    W1 & W2 & W3 -->|Update Status| DB
    W1 & W2 & W3 -->|Execute| QK[Qiskit Aer]
```

### Key Design Decisions

**Message Queue**: RabbitMQ provides reliable task distribution with message persistence, ensuring no task loss during restarts. Workers use `prefetch=1` for fair load balancing.

**Database**: PostgreSQL with async SQLAlchemy for task persistence and status tracking. Atomic status transitions prevent race conditions in multi-worker scenarios.

**Execution Engine**: Qiskit Aer simulator executes circuits with configurable shots (1-100,000). QASM3 format chosen for standardization and compatibility.

**Horizontal Scaling**: Multiple worker instances consume from shared queue. Add workers by duplicating service definitions in docker-compose.yml.

**Observability**: Structured JSON logging with correlation IDs enables request tracing across API and worker services.

## Project Structure

```
classiq/
├── src/
│   ├── api/           # FastAPI server
│   ├── worker/        # Background task processor
│   ├── core/          # Shared business logic
│   │   ├── db/        # Database models & repository
│   │   ├── messaging/ # RabbitMQ pub/sub
│   │   ├── execution/ # Qiskit circuit execution
│   │   └── services/  # Business logic layer
│   └── common/        # Config, logging, utilities
├── tests/             # Integration tests (26 tests)
└── migrations/        # Alembic database migrations
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Ports 5432, 5672, 8001 available

### Start the System

```bash
# Start all services
docker-compose up -d

# Verify health
curl http://localhost:8001/health

# View logs
docker-compose logs -f api worker-1
```

Services start in dependency order:
1. PostgreSQL (port 5432)
2. RabbitMQ (port 5672, management UI on 15672)
3. API server (port 8001)
4. Workers (3 instances)

## API Usage

### Submit Task

```bash
curl -X POST http://localhost:8001/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "qc": "OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit q;\nbit c;\nx q;\nc = measure q;",
    "shots": 100
  }'
```

**Response:**
```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "message": "Task submitted successfully.",
  "submitted_at": "2025-12-30T10:30:45.123456Z",
  "correlation_id": "abc-123-def"
}
```

**Parameters:**
- `qc`: OpenQASM 3.0 circuit definition (required)
- `shots`: Number of executions (optional, default: 1024, range: 1-100,000)

### Get Task Status

```bash
curl http://localhost:8001/tasks/123e4567-e89b-12d3-a456-426614174000
```

**Response (Completed):**
```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "completed",
  "submitted_at": "2025-12-30T10:30:45.123456Z",
  "message": "Task completed successfully.",
  "result": {
    "counts": {"0": 0, "1": 100},
    "shots": 100,
    "success": true
  },
  "status_history": [
    {
      "status": "pending",
      "transitioned_at": "2025-12-30T10:30:45.123456Z",
      "notes": "Task created and queued"
    },
    {
      "status": "processing",
      "transitioned_at": "2025-12-30T10:30:46.234567Z",
      "notes": "Worker started processing"
    },
    {
      "status": "completed",
      "transitioned_at": "2025-12-30T10:30:47.345678Z",
      "notes": "Task completed successfully"
    }
  ],
  "correlation_id": "abc-123-def"
}
```

### Health Check

```bash
curl http://localhost:8001/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-12-30T10:30:00.000000Z",
  "database_status": "connected",
  "queue_status": "connected"
}
```

## Task Lifecycle

```mermaid
stateDiagram-v2
    [*] --> pending: Task Submitted
    pending --> processing: Worker Picks Up
    processing --> completed: Success
    processing --> failed: Error
    completed --> [*]
    failed --> [*]
```

**States:**
- **pending**: Task persisted to DB, message published to queue
- **processing**: Worker consumed message, executing circuit
- **completed**: Circuit executed successfully, results stored
- **failed**: Circuit parsing or execution error

Workers implement idempotency checks - duplicate messages are safely ignored based on current task status.

## Example Workflows

### Bell State Circuit

Create entangled qubit pair and measure:

```bash
curl -X POST http://localhost:8001/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "qc": "OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit[2] q;\nbit[2] c;\nh q[0];\ncx q[0], q[1];\nc[0] = measure q[0];\nc[1] = measure q[1];",
    "shots": 1024
  }'

# Save task_id from response
TASK_ID="<task_id_from_response>"

# Poll for completion (typically <1 second)
curl http://localhost:8001/tasks/$TASK_ID
```

**Expected result**: ~50% `00`, ~50% `11` (entangled state collapses to correlated measurements).

### Single Qubit X-Gate

Flip qubit from |0⟩ to |1⟩:

```bash
curl -X POST http://localhost:8001/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "qc": "OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit q;\nbit c;\nx q;\nc = measure q;",
    "shots": 100
  }'
```

**Expected result**: 100% `1` (deterministic flip).

## Testing

```bash
# Run full integration test suite
docker-compose exec api pytest tests/integration/deployment -v

# Expected output: 26 passed
```

**Test coverage:**
- E2E workflow (submit → process → retrieve)
- Health checks (database + queue connectivity)
- Error handling (invalid circuits, malformed UUIDs)
- Queue persistence and message acknowledgment
- Schema validation and API contracts

## Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| API Server | FastAPI 0.104 | Async framework with automatic OpenAPI docs |
| Database | PostgreSQL 15 + asyncpg | ACID guarantees, async support |
| ORM | SQLAlchemy 2.0 | Async ORM with type hints |
| Queue | RabbitMQ 3.12 + aio-pika | Message persistence, fair distribution |
| Execution | Qiskit 1.0 + Qiskit Aer | Production quantum simulator |
| Logging | structlog | JSON structured logs for parsing |
| Migrations | Alembic | Version-controlled schema changes |
| Container | Docker + uv | Multi-stage builds, fast installs |

## Monitoring

### RabbitMQ Management UI

```bash
open http://localhost:15672
# Credentials: quantum_user / quantum_pass
```

View queue depth, message rates, consumer activity, and connection health.

### Container Status

```bash
# Check all services
docker-compose ps

# Expected output (all healthy):
# quantum-api        Up (healthy)   0.0.0.0:8001->8000/tcp
# quantum-worker-1   Up (healthy)   8000/tcp
# quantum-worker-2   Up (healthy)   8000/tcp
# quantum-worker-3   Up (healthy)   8000/tcp
# quantum-postgres   Up (healthy)   0.0.0.0:5432->5432/tcp
# quantum-rabbitmq   Up (healthy)   0.0.0.0:5672->5672/tcp
```

### Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f worker-1

# Follow with correlation ID filter
docker-compose logs -f | grep "correlation_id=abc-123"
```

## API Documentation

Interactive OpenAPI documentation:
- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc
- **OpenAPI Schema**: http://localhost:8001/openapi.json

## Stopping the System

```bash
# Stop services (preserve data)
docker-compose down

# Stop and remove volumes (clear all data)
docker-compose down -v
```

## Production Considerations

**Security:**
- Change default credentials in docker-compose.yml
- Use secrets management for production deployments
- Enable TLS for RabbitMQ and PostgreSQL connections

**Scaling:**
- Add workers by duplicating service definitions
- Use external PostgreSQL/RabbitMQ for multi-host deployments
- Consider read replicas for high query loads

**Monitoring:**
- Export structured logs to ELK/Datadog/CloudWatch
- Add Prometheus metrics for worker throughput
- Set up alerts for queue depth and error rates

---

**Status**: Production Ready
**Last Updated**: 2025-12-30
