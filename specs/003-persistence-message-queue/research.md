# Technology Research: Persistence Layer and Message Queue Integration

**Feature**: 003-persistence-message-queue
**Date**: 2025-12-28
**Status**: Complete

## Overview

This document records the technology selection decisions for integrating a persistence layer and message queue into the existing FastAPI-based quantum circuit task API. All decisions prioritize production readiness, async/await compatibility with FastAPI, and ease of deployment in Docker environments.

---

## Decision 1: Database Selection

### Requirement

A relational database for storing quantum circuit tasks with ACID transaction guarantees, support for JSON data types (for results), and concurrent access from multiple API and worker instances.

### Options Evaluated

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **PostgreSQL 15+** | ACID compliant, excellent JSON/JSONB support, robust connection pooling, widely used in production, strong async driver support (asyncpg) | Slightly more complex setup than SQLite | **SELECTED** |
| **MySQL 8.0** | ACID compliant, mature ecosystem, good performance | JSON support less mature than PostgreSQL, async drivers less established | Not selected |
| **SQLite** | Simple, no separate server process, good for development | Not suitable for multi-instance deployments (file locking issues), limited concurrency | Not suitable |

### Decision: PostgreSQL 15+

**Rationale**:
- Industry-standard choice for Python web applications requiring ACID transactions
- Excellent JSONB support for storing quantum circuit results efficiently
- Strong ecosystem of async Python drivers (asyncpg, SQLAlchemy 2.0+)
- Proven production track record with FastAPI applications
- Docker official images available with health check support

**Key Features**:
- **ACID Transactions**: Ensures task creation and queue publish can be atomic
- **JSONB Type**: Native storage for circuit results without serialization overhead
- **Row-Level Locking**: Supports concurrent updates from multiple workers
- **Connection Pooling**: Efficient resource usage with many API/worker instances

**Implementation Notes**:
- Use official `postgres:15-alpine` Docker image for lightweight deployment
- Configure `max_connections` appropriately for API + worker instance count
- Enable WAL (Write-Ahead Logging) for crash recovery
- Use JSONB indexes for efficient result queries if needed in future

---

## Decision 2: ORM Selection

### Requirement

An Object-Relational Mapping (ORM) library that supports async/await, integrates with FastAPI, provides migration tooling, and handles connection pooling efficiently.

### Options Evaluated

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **SQLAlchemy 2.0+** | Full async support, mature migration tooling (Alembic), excellent documentation, FastAPI ecosystem standard, flexible (Core + ORM) | Learning curve for advanced features | **SELECTED** |
| **Tortoise ORM** | Built for async from ground up, Django-like API, simple to learn | Smaller ecosystem, less mature, migration tooling less robust | Not selected |
| **Raw asyncpg** | Maximum performance, no abstraction overhead, full control | No ORM layer (manual SQL), no migration tooling, more boilerplate code | Not selected |

### Decision: SQLAlchemy 2.0+

**Rationale**:
- SQLAlchemy 2.0 introduces first-class async support with `async_sessionmaker`
- Alembic provides production-grade migration management with rollback support
- Extensive FastAPI integration examples and community support
- Repository pattern can isolate SQL complexity from business logic
- Connection pooling with `pool_pre_ping` for dead connection detection

**Key Features**:
- **Async Session**: `AsyncSession` with async/await for all database operations
- **ORM Models**: Declarative base for Task and StatusHistory entities
- **Query Building**: Composable queries with type safety
- **Connection Pool**: Built-in pooling with configurable size and overflow

**Implementation Notes**:
- Use SQLAlchemy 2.0.x (latest stable)
- Define models with `declarative_base()` and async relationships
- Use `pool_pre_ping=True` to validate connections before use
- Configure `pool_size=10` and `max_overflow=20` for initial deployment

**Example Pattern**:
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

engine = create_async_engine(
    "postgresql+asyncpg://user:pass@localhost/db",
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
```

---

## Decision 3: Database Migration Tool

### Requirement

A migration tool that integrates with SQLAlchemy, supports version control of schema changes, allows rollback, and works in automated deployment pipelines.

### Options Evaluated

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **Alembic** | Official SQLAlchemy migration tool, version-controlled migrations, auto-generation from models, rollback support, widely adopted | Python-specific (not suitable for polyglot teams) | **SELECTED** |
| **Flyway** | Language-agnostic, SQL-based, good for Java/JVM teams | No Python ORM integration, manual SQL writing | Not selected |
| **Manual SQL Scripts** | Full control, simple for small projects | Error-prone, no versioning, difficult rollback, doesn't scale | Not selected |

### Decision: Alembic

**Rationale**:
- Official migration tool for SQLAlchemy with seamless integration
- Auto-generate migrations from SQLAlchemy model changes
- Version control friendly (migrations are Python files in git)
- Supports both upgrade and downgrade (rollback) operations
- Can run migrations in init containers before API deployment

**Key Features**:
- **Auto-generation**: `alembic revision --autogenerate -m "description"`
- **Versioning**: Linear migration history with dependency tracking
- **Rollback**: `alembic downgrade -1` for safe rollback
- **Multiple Environments**: Separate configs for dev/staging/prod

**Implementation Notes**:
- Store migrations in `api/migrations/versions/`
- Run `alembic upgrade head` in Docker entrypoint or init container
- Include rollback instructions in migration docstrings
- Test both upgrade and downgrade paths

**Workflow**:
1. Modify SQLAlchemy models
2. Run `alembic revision --autogenerate -m "add status_history table"`
3. Review generated migration, add any manual changes
4. Test upgrade: `alembic upgrade head`
5. Test downgrade: `alembic downgrade -1`
6. Commit migration file to git

---

## Decision 4: Message Queue Selection

### Requirement

A message queue system supporting at-least-once delivery, message persistence, concurrent consumers, and ease of deployment in Docker environments.

### Options Evaluated

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **RabbitMQ 3.12+** | Industry standard, excellent at-least-once delivery, mature, official Docker image, management UI, flexible routing | More complex than Redis, requires separate service | **SELECTED** |
| **Redis Streams** | Simple, often already deployed, low latency, pub/sub model | At-least-once requires manual acknowledgment logic, less feature-rich than RabbitMQ | Not selected |
| **AWS SQS** | Managed service, no infrastructure, built-in retry | Cloud-specific, not suitable for local dev, network latency | Not selected |
| **Apache Kafka** | High throughput, distributed, exactly-once possible | Overkill for this use case, complex setup, resource-intensive | Not selected |

### Decision: RabbitMQ 3.12+

**Rationale**:
- Industry-standard message broker designed for task queues
- Built-in support for at-least-once delivery with manual message acknowledgment
- Durable queues with message persistence to disk
- Prefetch count control for fair distribution to workers
- Management UI for debugging (viewing queues, messages, consumers)

**Key Features**:
- **Message Persistence**: Durable queues + persistent messages survive broker restart
- **Acknowledgment**: Workers manually acknowledge after processing (prevents message loss)
- **Prefetch Count**: Set to 1 for fair distribution (each worker gets one message at a time)
- **Dead Letter Queue**: Failed messages can be routed to DLQ for analysis (future enhancement)

**Implementation Notes**:
- Use `rabbitmq:3.12-management-alpine` Docker image (includes management UI)
- Declare queue as durable: `queue_declare(queue='tasks', durable=True)`
- Publish persistent messages: `delivery_mode=2`
- Consumer sets `prefetch_count=1` for fair distribution
- Management UI accessible at http://localhost:15672 (guest/guest)

**Message Flow**:
1. API publishes message to `tasks` queue (durable, persistent)
2. Worker consumes message with `prefetch_count=1`
3. Worker processes task, updates database
4. Worker acknowledges message (removed from queue)
5. If worker crashes before ACK, message redelivered to another worker

---

## Decision 5: Queue Client Library

### Requirement

A Python library for interacting with RabbitMQ that supports async/await, integrates with FastAPI, and provides fine-grained control over message acknowledgment.

### Options Evaluated

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **aio-pika 9.0+** | Async/await native, FastAPI-compatible, active development, good docs, built on pika | Relatively newer than pika | **SELECTED** |
| **pika (sync)** | Official RabbitMQ client, stable, widely used | Synchronous (blocks event loop), not compatible with FastAPI async patterns | Not selected |
| **kombu** | High-level abstraction, Celery backend | Too high-level, hides important details, Celery dependency | Not selected |

### Decision: aio-pika 9.0+

**Rationale**:
- Built specifically for async/await Python applications
- Direct integration with FastAPI's async request handlers
- Provides full control over message acknowledgment (critical for at-least-once delivery)
- Automatic reconnection with backoff for resilience
- Well-documented with FastAPI examples

**Key Features**:
- **Async Connection**: `await aio_pika.connect_robust()` with auto-reconnect
- **Channel Management**: Async channel creation and closing
- **Message Publishing**: `await channel.default_exchange.publish()`
- **Message Consumption**: Async iterator for consuming messages
- **Manual ACK/NACK**: `await message.ack()` or `await message.nack(requeue=True)`

**Implementation Notes**:
- Use `connect_robust()` for automatic reconnection
- Set `prefetch_count=1` on channel for fair worker distribution
- Always acknowledge messages after successful database update
- Use `nack(requeue=True)` for transient errors, `nack(requeue=False)` for permanent failures

**Example Pattern**:
```python
import aio_pika

# Publisher (API)
connection = await aio_pika.connect_robust("amqp://guest:guest@localhost/")
channel = await connection.channel()
await channel.default_exchange.publish(
    aio_pika.Message(
        body=json.dumps({"task_id": str(task_id)}).encode(),
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT
    ),
    routing_key="tasks"
)

# Consumer (Worker)
queue = await channel.declare_queue("tasks", durable=True)
await channel.set_qos(prefetch_count=1)

async with queue.iterator() as queue_iter:
    async for message in queue_iter:
        try:
            # Process task, update database
            await process_task(message.body)
            await message.ack()
        except Exception:
            await message.nack(requeue=True)
```

---

## Additional Best Practices

### Database Connection Pooling

- **API Instances**: Each API instance maintains its own connection pool (10 connections + 20 overflow)
- **Worker Instances**: Each worker maintains a smaller pool (5 connections + 10 overflow)
- **Total Calculation**: For 5 API + 3 workers, max connections = 5×30 + 3×15 = 195 (set PostgreSQL `max_connections=250`)

### Queue Configuration

- **Queue Name**: `quantum_tasks` (descriptive, versioned if needed)
- **Durability**: Queue and messages both durable (survive RabbitMQ restart)
- **Acknowledgment Mode**: Manual acknowledgment after database update
- **Prefetch Count**: 1 (fair distribution, prevents worker overload)
- **TTL**: No message TTL (tasks can wait indefinitely for workers)

### Worker Idempotency

**Strategy**: Check-then-update pattern
```python
async def process_task(task_id: UUID):
    # Query current status
    task = await repository.get_task(task_id)

    # Only process if in expected state
    if task.status != "pending":
        # Already processed or in progress by another worker
        return

    # Update status to "processing" (atomic compare-and-swap)
    updated = await repository.update_status_if(
        task_id,
        from_status="pending",
        to_status="processing"
    )

    if not updated:
        # Another worker already started processing
        return

    # Process task...
```

### Error Handling

- **Transient Errors** (DB connection lost): NACK with requeue
- **Permanent Errors** (invalid task data): NACK without requeue, log error
- **Partial Failures** (task processed but ACK fails): Idempotency handles redelivery

---

## Technology Stack Summary

| Component | Technology | Version | Justification |
|-----------|-----------|---------|---------------|
| **Database** | PostgreSQL | 15+ | ACID transactions, JSONB support, production-ready |
| **ORM** | SQLAlchemy | 2.0+ | Async support, mature ecosystem, Alembic integration |
| **Migrations** | Alembic | Latest | Official SQLAlchemy tool, version control, rollback support |
| **Message Queue** | RabbitMQ | 3.12+ | At-least-once delivery, durability, management UI |
| **Queue Client** | aio-pika | 9.0+ | Async/await, FastAPI-compatible, fine-grained control |

---

## Implementation Checklist

- [x] PostgreSQL selected for database
- [x] SQLAlchemy 2.0+ selected for ORM
- [x] Alembic selected for migrations
- [x] RabbitMQ selected for message queue
- [x] aio-pika selected for queue client
- [x] Connection pooling strategy defined
- [x] Idempotency strategy defined
- [x] Error handling patterns defined

**Next Steps**: Proceed to Phase 1 (Data Model and Contracts)

---

## References

- [SQLAlchemy 2.0 Async Tutorial](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [RabbitMQ Tutorials](https://www.rabbitmq.com/getstarted.html)
- [aio-pika Documentation](https://aio-pika.readthedocs.io/)
- [FastAPI + SQLAlchemy Async Example](https://fastapi.tiangolo.com/advanced/async-sql-databases/)

---

## Document History

| Version | Date       | Changes                  | Author |
|---------|------------|--------------------------|--------|
| 1.0     | 2025-12-28 | Initial research complete | Claude |
