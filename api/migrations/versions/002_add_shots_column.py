"""add shots column to tasks table

Revision ID: 002
Revises: 001
Create Date: 2025-12-29

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add shots column to tasks table
    op.add_column(
        'tasks',
        sa.Column('shots', sa.Integer(), nullable=False, server_default='1024')
    )


def downgrade() -> None:
    # Remove shots column from tasks table
    op.drop_column('tasks', 'shots')
