"""create tasks and status_history tables

Revision ID: 001
Revises:
Create Date: 2025-12-29

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create ENUM type for task status
    op.execute("CREATE TYPE taskstatus AS ENUM ('pending', 'processing', 'completed', 'failed')")

    # Create tasks table
    op.create_table(
        'tasks',
        sa.Column('task_id', UUID(as_uuid=True), primary_key=True),
        sa.Column('circuit', sa.Text(), nullable=False),
        sa.Column('submitted_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('current_status', sa.Enum('pending', 'processing', 'completed', 'failed', name='taskstatus'), nullable=False, server_default='pending'),
        sa.Column('completed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('result', JSONB, nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True)
    )

    # Create indexes for tasks table
    op.create_index('idx_task_status', 'tasks', ['current_status'])
    op.create_index('idx_task_submitted_at', 'tasks', ['submitted_at'])

    # Create status_history table
    op.create_table(
        'status_history',
        sa.Column('id', sa.Integer(), sa.Identity(always=False), primary_key=True),
        sa.Column('task_id', UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.Enum('pending', 'processing', 'completed', 'failed', name='taskstatus'), nullable=False),
        sa.Column('transitioned_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.task_id'], name='fk_status_history_task_id')
    )

    # Create index for status_history table
    op.create_index('idx_status_history_task_time', 'status_history', ['task_id', 'transitioned_at'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_status_history_task_time', table_name='status_history')
    op.drop_index('idx_task_submitted_at', table_name='tasks')
    op.drop_index('idx_task_status', table_name='tasks')

    # Drop tables
    op.drop_table('status_history')
    op.drop_table('tasks')

    # Drop ENUM type
    op.execute("DROP TYPE taskstatus")
