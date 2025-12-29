"""Database models for the API."""

import enum
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Column,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, mapped_column, relationship


class TaskStatus(str, enum.Enum):
    """Task status enum for proper serialization."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# Create SQLAlchemy declarative base
Base = declarative_base()


class Task(Base):
    """Task model representing quantum circuit compilation tasks."""

    __tablename__ = "tasks"

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    circuit: Mapped[str] = mapped_column(Text, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    current_status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=TaskStatus.PENDING
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    result: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationship: one-to-many with StatusHistory
    status_history: Mapped[List["StatusHistory"]] = relationship(
        "StatusHistory", back_populates="task", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_task_status", "current_status"),
        Index("idx_task_submitted_at", "submitted_at"),
    )


class StatusHistory(Base):
    """Status history model for tracking task status transitions."""

    __tablename__ = "status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.task_id"), nullable=False
    )
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, values_callable=lambda x: [e.value for e in x]), nullable=False
    )
    transitioned_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationship: many-to-one with Task
    task: Mapped["Task"] = relationship("Task", back_populates="status_history")

    __table_args__ = (Index("idx_status_history_task_time", "task_id", "transitioned_at"),)
