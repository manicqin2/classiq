"""Task service for coordinating database and queue operations."""

from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db.repository import TaskRepository
from src.core.messaging.publisher import QueuePublisher

logger = structlog.get_logger(__name__)


class TaskService:
    """Service for managing task submission and coordination."""

    def __init__(self, db: AsyncSession):
        """Initialize TaskService with database session.

        Args:
            db: SQLAlchemy async database session
        """
        self.repository = TaskRepository(db)
        self.publisher = QueuePublisher()

    async def submit_task(self, circuit: str, shots: int = 1024) -> "Task":
        """Submit a task by creating database record and publishing to queue.

        This method coordinates two operations:
        1. Create task in database (within transaction)
        2. Publish message to queue

        The database transaction ensures the task persists. If queue publishing
        fails, the task remains in the database (at-least-once delivery semantics).

        Args:
            circuit: Circuit code string to be processed
            shots: Number of circuit executions (default: 1024)

        Returns:
            Task: The created Task object with task_id and submitted_at

        Raises:
            Exception: If database operation fails or queue publishing fails
        """
        # Step 1: Create task in database
        task = await self.repository.create_task(circuit, shots=shots)
        task_id = task.task_id
        logger.info(
            "task_created_in_database",
            task_id=str(task_id),
            circuit_length=len(circuit),
            shots=shots,
        )

        try:
            # Step 2: Publish message to queue
            await self.publisher.publish_task_message(task_id, circuit)
            logger.info("task_published_to_queue", task_id=str(task_id))
        except Exception as e:
            # Log the error but don't rollback the database transaction
            # The task persists in DB for at-least-once delivery
            logger.error("queue_publish_failed", task_id=str(task_id), error=str(e), exc_info=True)
            raise

        # Step 3: Return task
        logger.info("task_submitted_successfully", task_id=str(task_id))
        return task
