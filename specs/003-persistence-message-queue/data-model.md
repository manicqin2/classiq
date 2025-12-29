# Data Model: Persistence Layer and Message Queue Integration

**Feature**: 003-persistence-message-queue
**Date**: 2025-12-28
**Database**: PostgreSQL 15+
**ORM**: SQLAlchemy 2.0+

## Overview

This document defines the database schema, entities, relationships, and state transitions for the quantum circuit task persistence layer. The model supports task storage, status history tracking, and concurrent access from multiple API and worker instances.

---

## Entity Relationship Diagram

```
┌─────────────────────────────┐
│          Task               │
│─────────────────────────────│
│ task_id (UUID, PK)          │
│ circuit (TEXT)              │
│ submitted_at (TIMESTAMP)    │
│ current_status (ENUM)       │
│ completed_at (TIMESTAMP?)   │
│ result (JSONB?)             │
│ error_message (TEXT?)       │
└─────────────────────────────┘
          │
          │ 1:N
          │
          ▼
┌─────────────────────────────┐
│      StatusHistory          │
│─────────────────────────────│
│ id (SERIAL, PK)             │
│ task_id (UUID, FK)          │
│ status (ENUM)               │
│ transitioned_at (TIMESTAMP) │
│ notes (TEXT?)               │
└─────────────────────────────┘
```

---

## Entity 1: Task

### Purpose

Represents a quantum circuit execution request with current state and results. This is the primary entity for task tracking, queried by the API GET /tasks/{id} endpoint and updated by worker processes.

### Fields

| Field Name      | Type               | Constraints           | Description                                      |
|-----------------|--------------------|-----------------------|--------------------------------------------------|
| `task_id`       | UUID               | PRIMARY KEY, NOT NULL | Unique identifier for the task (UUIDv4)         |
| `circuit`       | TEXT               | NOT NULL              | Quantum circuit definition (QASM or other format)|
| `submitted_at`  | TIMESTAMP WITH TZ  | NOT NULL, DEFAULT NOW()| When the task was submitted to the API          |
| `current_status`| ENUM('pending', 'processing', 'completed', 'failed') | NOT NULL, DEFAULT 'pending' | Current state of the task |
| `completed_at`  | TIMESTAMP WITH TZ  | NULLABLE              | When the task reached terminal state (completed/failed) |
| `result`        | JSONB              | NULLABLE              | Execution result (e.g., measurement counts)      |
| `error_message` | TEXT               | NULLABLE              | Error details if task failed                     |

### Indexes

| Index Name               | Columns                | Type    | Purpose                                      |
|--------------------------|------------------------|---------|----------------------------------------------|
| `pk_task`                | `task_id`              | PRIMARY | Fast lookups by task ID                      |
| `idx_task_status`        | `current_status`       | BTREE   | Filter tasks by status (future: list pending)|
| `idx_task_submitted_at`  | `submitted_at DESC`    | BTREE   | Chronological listing (future: recent tasks) |

### Relationships

- **One-to-Many** with `StatusHistory`: Each task has multiple status history entries

### Validation Rules

- `task_id`: Must be valid UUIDv4 (enforced by database type)
- `circuit`: Must be non-empty string (application layer validation)
- `current_status`: Must be one of: `pending`, `processing`, `completed`, `failed`
- `completed_at`: Must be NULL if status is `pending` or `processing`; must be set if status is `completed` or `failed`
- `result`: Must be NULL if status is not `completed`; should contain valid JSON when completed
- `error_message`: Must be NULL if status is not `failed`; should be non-empty if failed

### Lifecycle

1. **Created**: When API receives POST /tasks request
   - `task_id` generated (UUIDv4)
   - `circuit` from request body
   - `submitted_at` set to current timestamp
   - `current_status` initialized to `pending`
   - `completed_at`, `result`, `error_message` all NULL

2. **Updated**: When worker picks up task from queue
   - `current_status` changes from `pending` to `processing`
   - Status history entry created

3. **Completed**: When worker finishes successfully
   - `current_status` changes from `processing` to `completed`
   - `completed_at` set to current timestamp
   - `result` populated with execution results (JSONB)
   - Status history entry created

4. **Failed**: When worker encounters error
   - `current_status` changes from `processing` to `failed`
   - `completed_at` set to current timestamp
   - `error_message` populated with error details
   - Status history entry created

### SQLAlchemy ORM Model

```python
from sqlalchemy import Column, String, Text, Enum as SQLEnum, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
import uuid

class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Task(Base):
    __tablename__ = "tasks"

    task_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    circuit = Column(Text, nullable=False)
    submitted_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    current_status = Column(SQLEnum(TaskStatus), nullable=False, default=TaskStatus.PENDING)
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    result = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)

    # Relationship
    status_history = relationship("StatusHistory", back_populates="task", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_task_status', 'current_status'),
        Index('idx_task_submitted_at', 'submitted_at'),
    )
```

---

## Entity 2: StatusHistory

### Purpose

Tracks all state transitions for a task, providing an audit trail and timeline for debugging and observability. Each row represents a single status change with a timestamp.

### Fields

| Field Name       | Type               | Constraints           | Description                                      |
|------------------|--------------------|-----------------------|--------------------------------------------------|
| `id`             | SERIAL (INT)       | PRIMARY KEY, AUTO_INCREMENT | Unique identifier for this history entry   |
| `task_id`        | UUID               | FOREIGN KEY (tasks.task_id), NOT NULL | Reference to parent task          |
| `status`         | ENUM('pending', 'processing', 'completed', 'failed') | NOT NULL | Status value at this transition |
| `transitioned_at`| TIMESTAMP WITH TZ  | NOT NULL, DEFAULT NOW() | When this status was entered                  |
| `notes`          | TEXT               | NULLABLE              | Optional notes (e.g., worker ID, retry count)    |

### Indexes

| Index Name                  | Columns                          | Type    | Purpose                                      |
|-----------------------------|----------------------------------|---------|----------------------------------------------|
| `pk_status_history`         | `id`                             | PRIMARY | Fast lookups by history entry ID             |
| `fk_status_history_task`    | `task_id`                        | FOREIGN | Enforce referential integrity                |
| `idx_status_history_task_time` | `task_id, transitioned_at DESC` | BTREE   | Retrieve history ordered by time for a task  |

### Relationships

- **Many-to-One** with `Task`: Each history entry belongs to one task

### Validation Rules

- `task_id`: Must reference an existing task (enforced by foreign key)
- `status`: Must be one of: `pending`, `processing`, `completed`, `failed`
- `transitioned_at`: Must be chronologically after previous transitions for the same task (application layer validation)
- `notes`: Optional, can contain metadata like worker ID

### Lifecycle

1. **Created**: When task status changes
   - Triggered by: Task creation (initial `pending`), worker starts processing, worker completes/fails
   - `status` set to new status value
   - `transitioned_at` set to current timestamp
   - `notes` may include worker ID, correlation ID, or other context

2. **Never Updated**: History entries are immutable (append-only)

3. **Deleted**: Only when parent task is deleted (cascade delete)

### SQLAlchemy ORM Model

```python
from sqlalchemy import Column, Integer, String, Text, Enum as SQLEnum, TIMESTAMP, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

class StatusHistory(Base):
    __tablename__ = "status_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.task_id"), nullable=False)
    status = Column(SQLEnum(TaskStatus), nullable=False)
    transitioned_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    notes = Column(Text, nullable=True)

    # Relationship
    task = relationship("Task", back_populates="status_history")

    __table_args__ = (
        Index('idx_status_history_task_time', 'task_id', 'transitioned_at'),
    )
```

---

## State Machine

### Task Status States

```
┌─────────┐
│ pending │  (Initial state when task submitted)
└────┬────┘
     │
     │ Worker picks up from queue
     │
     ▼
┌────────────┐
│ processing │  (Worker actively executing task)
└─────┬──────┘
      │
      ├──────────────┐
      │              │
      │ Success      │ Failure
      │              │
      ▼              ▼
┌───────────┐   ┌────────┐
│ completed │   │ failed │  (Terminal states)
└───────────┘   └────────┘
```

### Valid State Transitions

| From State   | To State     | Trigger                          | Constraints                                   |
|--------------|--------------|----------------------------------|-----------------------------------------------|
| `pending`    | `processing` | Worker starts processing         | First worker to acquire task (optimistic lock)|
| `processing` | `completed`  | Worker finishes successfully     | Must set `result`, `completed_at`             |
| `processing` | `failed`     | Worker encounters error          | Must set `error_message`, `completed_at`      |

### Invalid State Transitions (Rejected)

| From State   | To State     | Reason                                                  |
|--------------|--------------|--------------------------------------------------------|
| `completed`  | Any          | Terminal state, cannot transition                      |
| `failed`     | Any          | Terminal state, cannot transition                      |
| `pending`    | `completed`  | Must pass through `processing` first                   |
| `pending`    | `failed`     | Must pass through `processing` first                   |
| `processing` | `pending`    | Cannot go backward                                     |

### Idempotency Handling

**Scenario**: Worker receives duplicate message (at-least-once delivery)

**Check-Then-Update Pattern**:
```python
async def transition_status(task_id: UUID, from_status: TaskStatus, to_status: TaskStatus):
    """
    Atomically transition task status only if current status matches expected.
    Returns True if transition succeeded, False if already in different state.
    """
    async with session.begin():
        # Query current status with row lock
        result = await session.execute(
            select(Task)
            .where(Task.task_id == task_id)
            .with_for_update()  # Row-level lock
        )
        task = result.scalar_one_or_none()

        if task is None:
            raise TaskNotFoundError(task_id)

        if task.current_status != from_status:
            # Already transitioned by another worker
            return False

        # Perform transition
        task.current_status = to_status
        if to_status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
            task.completed_at = func.now()

        # Create history entry
        history = StatusHistory(
            task_id=task_id,
            status=to_status,
            transitioned_at=func.now()
        )
        session.add(history)

        await session.commit()
        return True
```

---

## Database Initialization

### Alembic Migration (001_create_tasks_table.py)

```python
"""Create tasks and status_history tables

Revision ID: 001
Revises:
Create Date: 2025-12-28
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

def upgrade():
    # Create ENUM type
    op.execute("CREATE TYPE taskstatus AS ENUM ('pending', 'processing', 'completed', 'failed')")

    # Create tasks table
    op.create_table(
        'tasks',
        sa.Column('task_id', UUID(as_uuid=True), primary_key=True),
        sa.Column('circuit', sa.Text(), nullable=False),
        sa.Column('submitted_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('current_status', sa.Enum('pending', 'processing', 'completed', 'failed', name='taskstatus'), nullable=False, server_default='pending'),
        sa.Column('completed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('result', JSONB, nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
    )
    op.create_index('idx_task_status', 'tasks', ['current_status'])
    op.create_index('idx_task_submitted_at', 'tasks', ['submitted_at'])

    # Create status_history table
    op.create_table(
        'status_history',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('task_id', UUID(as_uuid=True), sa.ForeignKey('tasks.task_id'), nullable=False),
        sa.Column('status', sa.Enum('pending', 'processing', 'completed', 'failed', name='taskstatus'), nullable=False),
        sa.Column('transitioned_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
    )
    op.create_index('idx_status_history_task_time', 'status_history', ['task_id', 'transitioned_at'])

def downgrade():
    op.drop_index('idx_status_history_task_time', table_name='status_history')
    op.drop_table('status_history')
    op.drop_index('idx_task_submitted_at', table_name='tasks')
    op.drop_index('idx_task_status', table_name='tasks')
    op.drop_table('tasks')
    op.execute('DROP TYPE taskstatus')
```

---

## Query Patterns

### 1. Create Task (API)

```python
async def create_task(circuit: str) -> UUID:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            task = Task(
                task_id=uuid.uuid4(),
                circuit=circuit,
                current_status=TaskStatus.PENDING
            )
            session.add(task)

            # Create initial status history entry
            history = StatusHistory(
                task_id=task.task_id,
                status=TaskStatus.PENDING,
                notes="Task created"
            )
            session.add(history)

            await session.commit()
            return task.task_id
```

### 2. Retrieve Task with History (API)

```python
async def get_task_with_history(task_id: UUID) -> Optional[Task]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Task)
            .options(selectinload(Task.status_history))  # Eager load history
            .where(Task.task_id == task_id)
        )
        return result.scalar_one_or_none()
```

### 3. Update Task Status (Worker)

```python
async def update_task_status(
    task_id: UUID,
    from_status: TaskStatus,
    to_status: TaskStatus,
    result: Optional[dict] = None,
    error: Optional[str] = None
) -> bool:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            result_query = await session.execute(
                select(Task)
                .where(Task.task_id == task_id)
                .with_for_update()
            )
            task = result_query.scalar_one_or_none()

            if task is None or task.current_status != from_status:
                return False

            task.current_status = to_status
            if to_status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                task.completed_at = func.now()
            if result:
                task.result = result
            if error:
                task.error_message = error

            history = StatusHistory(
                task_id=task_id,
                status=to_status,
                notes=f"Transitioned from {from_status} to {to_status}"
            )
            session.add(history)

            await session.commit()
            return True
```

---

## Performance Considerations

### Connection Pooling

- **Pool Size**: 10 connections per API instance
- **Max Overflow**: 20 additional connections under load
- **Pre-ping**: Validate connections before use (`pool_pre_ping=True`)

### Query Optimization

- **Indexes**: Primary key on `task_id`, status index for filtering
- **Eager Loading**: Use `selectinload()` to fetch status history in one query
- **Row Locking**: `with_for_update()` prevents race conditions during status updates

### Scalability

- **Read Replicas**: Future enhancement for GET requests (status checks)
- **Partitioning**: Future enhancement if task count exceeds millions (partition by submission date)

---

## Document History

| Version | Date       | Changes                  | Author |
|---------|------------|--------------------------|--------|
| 1.0     | 2025-12-28 | Initial data model       | Claude |
