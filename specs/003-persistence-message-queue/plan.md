# Implementation Plan: Persistence Layer and Message Queue Integration

**Branch**: `003-persistence-message-queue` | **Date**: 2025-12-28 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-persistence-message-queue/spec.md`

## Summary

This feature integrates persistence and message queue infrastructure into the existing API server (Feature 2-api-server-docker). It replaces the stubbed in-memory task storage with a PostgreSQL database for permanent task storage, adds RabbitMQ for asynchronous task queuing, and implements worker processes that consume queue messages and update task status. The system will support at-least-once delivery semantics with idempotent worker operations, horizontal scaling of both API and worker instances, and comprehensive status history tracking for observability.

## Technical Context

**Language/Version**: Python 3.11 (existing)
**Primary Dependencies**: FastAPI 0.104.1 (existing), SQLAlchemy 2.0+ (new - ORM), Alembic (new - migrations), aio-pika 9.0+ (new - async RabbitMQ client)
**Storage**: PostgreSQL 15+ (relational database for task persistence, ACID compliance)
**Testing**: pytest 7.4.3 (existing), pytest-asyncio 0.21.1 (existing), httpx 0.25.2 (existing)
**Target Platform**: Linux containers (Docker) - existing deployment model
**Project Type**: Web application (API + worker services)
**Performance Goals**:
- Task submission < 500ms (including DB write + queue publish)
- Support 100 messages/second queue throughput
- Database connection pool sized for 10-20 concurrent API/worker instances
**Constraints**:
- Zero data loss on server restart (100% persistence reliability)
- At-least-once delivery guarantees (messages not lost, may be redelivered)
- Workers must be idempotent (handle duplicate messages gracefully)
**Scale/Scope**:
- Initial: 1000 tasks/day, indefinite retention
- Future: Scale to 10,000+ tasks/day with time-based cleanup

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### ✅ Principle 1 - Zero Task Loss Guarantee

**How Satisfied**: This feature FULLY implements zero task loss
- Tasks persisted to PostgreSQL immediately upon submission (ACID transactions)
- Database ensures durability across server restarts
- Queue messages persisted to disk (RabbitMQ durable queues)
- Worker acknowledgment only after successful database status update

**Implementation Details**:
- PostgreSQL with WAL (Write-Ahead Logging) for crash recovery
- Database transactions wrap task creation + queue publish (atomicity)
- RabbitMQ durable queues with persistent messages

### ✅ Principle 2 - Fault Tolerance and Resilience

**How Satisfied**: Comprehensive fault tolerance for database and queue failures
- Database connection pool with automatic reconnection and health checks
- Queue connection recovery with exponential backoff
- Graceful degradation: API returns 503 when DB/queue unavailable (no crashes)
- Worker retry logic: Failed messages requeued with retry count tracking
- Transaction rollback on failures prevents inconsistent state

**Implementation Details**:
- SQLAlchemy connection pool with `pool_pre_ping=True` for dead connection detection
- aio-pika automatic reconnection for queue connections
- Circuit breaker pattern for health checks
- Message visibility timeout ensures crashed workers don't lose messages

### ✅ Principle 3 - Observable and Debuggable

**How Satisfied**: Enhanced observability with database and queue operations logged
- All database queries logged with execution time (slow query detection)
- Message publish/consume events logged with task ID correlation
- Status transitions logged with timestamps for lifecycle visibility
- Database and queue connection status monitored and logged
- Full error context captured (query, parameters, stack trace)

**Implementation Details**:
- Structlog (existing) extended with database and queue logging
- SQLAlchemy echo mode for query logging (development)
- Correlation IDs flow through API → Queue → Worker → DB
- Status history table provides audit trail

### ✅ Principle 4 - Stateless Worker Design

**How Satisfied**: Both API and workers remain stateless with shared storage
- API instances share database and queue (no local state)
- Worker instances independently consume from shared queue
- Database is single source of truth for task state
- Horizontal scaling: Add more API/worker containers without coordination

**Implementation Details**:
- No in-memory caching of task state
- Database handles concurrency with row-level locking
- Queue distributes work fairly across workers (round-robin)
- Workers process one message at a time (prefetch_count=1)

### ✅ Principle 5 - Idempotent Operations

**How Satisfied**: Workers implement idempotent task processing
- Database operations use optimistic locking (check current status before update)
- Duplicate messages detected by comparing task status before processing
- Status transitions validated (can't go from "completed" back to "processing")
- Task table updates use atomic compare-and-swap patterns

**Implementation Details**:
- Before updating status, worker queries current status
- Only transition if current status matches expected (e.g., pending → processing)
- Already-processed tasks (completed/failed) skip reprocessing
- Worker acknowledges message only after successful idempotent update

### ✅ Principle 6 - Dependency Management and Startup Ordering

**How Satisfied**: Health checks verify database and queue availability
- API health check tests database connectivity (simple query)
- API health check tests queue connectivity (connection alive check)
- Workers wait for queue connection before consuming
- Docker Compose depends_on with health checks ensures startup order

**Implementation Details**:
- Health endpoint returns degraded status if DB or queue unavailable
- Alembic migrations run before API starts (init container or manual)
- Workers retry queue connection on startup until successful
- Container orchestration uses health checks for readiness probes

### ✅ Principle 7 - Separation of Concerns

**How Satisfied**: Clear separation between API, storage, queue, and workers
- API layer: HTTP handling, validation, persistence, message publishing
- Database layer: Task storage, status history, transaction management
- Queue layer: Message transport and delivery guarantees
- Worker layer: Message consumption, task processing, status updates
- No business logic mixed across layers

**Implementation Details**:
- Repository pattern for database access (isolate SQL from routes)
- Service layer for task submission logic (DB + queue coordination)
- Worker processes separate from API processes
- Clear interfaces between components

### ✅ Principle 8 - Production-Grade Patterns

**How Satisfied**: Production-ready database and queue infrastructure
- Database migrations with Alembic (version-controlled schema)
- Connection pooling for efficient resource usage
- Environment-based configuration for DB and queue credentials
- Graceful shutdown drains workers and closes connections properly
- Security: Database credentials from environment, no hardcoded secrets

**Implementation Details**:
- Alembic migration scripts in version control
- SQLAlchemy pool_size and max_overflow configured
- Docker secrets or environment variables for credentials
- SIGTERM handlers close DB connections and acknowledge in-flight messages

## Project Structure

### Documentation (this feature)

```text
specs/003-persistence-message-queue/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output: Technology decisions for DB/queue
├── data-model.md        # Phase 1 output: Database schema and entities
├── quickstart.md        # Phase 1 output: Local dev setup with DB/queue
├── contracts/           # Phase 1 output: Updated API contracts
│   └── openapi.yaml     # Extended API spec with persistence
└── tasks.md             # Phase 2 output: Implementation tasks (NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
# Web application structure (API + Workers)
api/
├── src/                 # (NEW: Reorganize for clarity)
│   ├── models.py        # Pydantic request/response models (existing)
│   ├── db/              # (NEW: Database layer)
│   │   ├── __init__.py
│   │   ├── models.py    # SQLAlchemy ORM models (Task, StatusHistory)
│   │   ├── session.py   # Database session management
│   │   └── repository.py # Data access layer (task CRUD operations)
│   ├── queue/           # (NEW: Message queue layer)
│   │   ├── __init__.py
│   │   ├── publisher.py # Queue message publishing
│   │   └── consumer.py  # Queue message consumption (for workers)
│   ├── services/        # (NEW: Business logic)
│   │   ├── __init__.py
│   │   └── task_service.py # Task submission orchestration (DB + queue)
│   ├── routes.py        # API endpoint handlers (existing, MODIFIED)
│   ├── app.py           # FastAPI application (existing, MODIFIED)
│   ├── config.py        # Configuration (existing, MODIFIED - add DB/queue settings)
│   ├── middleware.py    # Correlation ID middleware (existing)
│   └── logging_config.py # Logging setup (existing)
├── migrations/          # (NEW: Alembic database migrations)
│   ├── versions/
│   │   └── 001_create_tasks_table.py
│   └── alembic.ini
├── worker.py            # (NEW: Worker process entrypoint)
├── requirements.txt     # Python dependencies (existing, MODIFIED - add SQLAlchemy, aio-pika, alembic)
└── tests/               # (existing, EXTENDED)
    ├── integration/
    │   ├── test-api.sh  # (existing, MODIFIED - test persistence)
    │   └── test-worker.py # (NEW: Worker integration tests)
    └── unit/
        ├── test_repository.py # (NEW: Database layer tests)
        └── test_task_service.py # (NEW: Service layer tests)

docker-compose.yml       # (existing, MODIFIED - add PostgreSQL, RabbitMQ services)
Dockerfile               # (existing - may need adjustments for migrations)
```

**Structure Decision**: Extending existing web application structure with database and queue layers. API and workers share codebase but run as separate containers. Database and queue operations isolated into dedicated modules for testability and separation of concerns.

## Complexity Tracking

> **No violations** - All constitution principles satisfied without exceptions

## Phase 0: Research & Technology Decisions

**Goal**: Resolve technology choices for database, queue, ORM, and migration tools

**Research Tasks**:
1. **Database Selection**: Confirm PostgreSQL for relational task storage
   - Alternatives: MySQL, SQLite (not suitable for production multi-instance)
   - Decision criteria: ACID compliance, JSON support, production-ready
2. **ORM Selection**: Choose between SQLAlchemy, raw SQL, or alternatives
   - Alternatives: Tortoise ORM, raw asyncpg, Django ORM
   - Decision criteria: Async support, migration tooling, ecosystem maturity
3. **Migration Tool**: Select Alembic or alternatives
   - Alternatives: Flyway, manual SQL scripts
   - Decision criteria: Python integration, version control, rollback support
4. **Queue Selection**: Confirm RabbitMQ or evaluate alternatives
   - Alternatives: Redis Streams, AWS SQS, Apache Kafka
   - Decision criteria: At-least-once delivery, ease of deployment, Docker support
5. **Queue Client Library**: Choose aio-pika, pika, or alternatives
   - Alternatives: pika (sync), kombu
   - Decision criteria: Async/await support, FastAPI compatibility, message acknowledgment control

**Deliverable**: `research.md` with final technology choices and justification

## Phase 1: Design & Contracts

**Prerequisites**: `research.md` complete with all technology decisions finalized

### 1. Data Model Design (`data-model.md`)

**Entities to Define**:
- **Task** (from spec Key Entities)
  - Fields: task_id (UUID PK), circuit (text), submitted_at (timestamp), current_status (enum), completed_at (timestamp nullable), result (JSON nullable), error_message (text nullable)
  - Relationships: One-to-many with StatusHistory
  - Indexes: Primary key on task_id, index on current_status for filtering
- **StatusHistory** (from spec Key Entities)
  - Fields: id (serial PK), task_id (UUID FK), status (enum), transitioned_at (timestamp), notes (text nullable)
  - Relationships: Many-to-one with Task
  - Indexes: Composite index on (task_id, transitioned_at) for ordered history queries

**State Machine**:
- Valid transitions: pending → processing → completed/failed
- Validation rules: Cannot transition backward, cannot change from terminal state (completed/failed)

### 2. API Contract Updates (`contracts/openapi.yaml`)

**Modified Endpoints** (extend existing from Feature 2):
- **POST /tasks**:
  - Updated response: Include `submitted_at` timestamp
  - Behavior change: Task persisted to database, message published to queue
  - New error: 503 if database or queue unavailable
- **GET /tasks/{task_id}**:
  - Updated response: Include `status_history` array with transitions
  - Response fields: Add `completed_at`, `result`, `error_message` (when applicable)
  - Behavior change: Query from database instead of stub
- **GET /health**:
  - Updated response: Include `database_status` and `queue_status` fields
  - Response values: "healthy", "degraded" (DB/queue issues)

**No new endpoints** - Extends existing API with persistence

### 3. Developer Quickstart (`quickstart.md`)

**Setup Instructions**:
1. Prerequisites: Docker, Docker Compose
2. Start services: `docker-compose up -d` (API, worker, PostgreSQL, RabbitMQ)
3. Run migrations: `docker-compose exec api alembic upgrade head`
4. Verify health: `curl http://localhost:8001/health`
5. Submit task: Example curl command
6. Check status: Example curl command with task ID
7. View logs: `docker-compose logs -f api worker`

**Database Access**:
- Connection string format
- Running migrations manually
- Accessing PostgreSQL CLI for debugging

**Queue Access**:
- RabbitMQ management UI (http://localhost:15672)
- Viewing queues and messages
- Purging messages for testing

### 4. Agent Context Update

Run `.specify/scripts/bash/update-agent-context.sh claude` to add:
- SQLAlchemy ORM models and patterns
- Alembic migration workflow
- aio-pika message publishing and consumption
- Database connection pooling patterns
- Worker process structure

## Phase 2: Implementation Tasks

**Note**: Task breakdown will be created by `/speckit.tasks` command (NOT this plan)

**High-Level Implementation Areas**:
1. Database layer: SQLAlchemy models, repository, session management
2. Migration scripts: Alembic setup, initial schema
3. Queue layer: Publisher (API), consumer (worker)
4. Service layer: Task submission orchestration (DB + queue atomicity)
5. API modifications: Integrate database and queue
6. Worker process: Message consumption, task processing stub, status updates
7. Configuration: Add DB and queue connection settings
8. Docker Compose: Add PostgreSQL and RabbitMQ services
9. Testing: Unit tests for repository, integration tests for end-to-end flow
10. Documentation: Update README with new setup steps

## Re-evaluation After Phase 1

**Constitution Check Status**: ✅ All principles satisfied

**Design Changes**: None - design aligns with all principles

**Risks Identified**:
- Database connection pool sizing must be tested under load
- Queue visibility timeout must be tuned for task processing duration
- Migration rollback procedures needed for production deployments

**Mitigation Strategies**:
- Load testing with 100 concurrent API instances to validate pool configuration
- Set initial visibility timeout to 5 minutes (adjustable based on task duration)
- Document rollback steps in each migration file

---

## Document History

| Version | Date       | Changes                  | Author |
|---------|------------|--------------------------|--------|
| 1.0     | 2025-12-28 | Initial implementation plan | Claude |
