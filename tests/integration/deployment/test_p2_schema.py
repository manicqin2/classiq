"""Priority 2: Database schema validation tests.

These tests verify that the database schema matches the expected structure
for the quantum task processing system.
"""

import pytest


@pytest.mark.p2
@pytest.mark.asyncio
async def test_required_tables_exist(db_client):
    """Verify all required tables exist in database."""
    required_tables = ["tasks", "status_history", "alembic_version"]

    for table_name in required_tables:
        exists = await db_client.check_table_exists(table_name)
        assert exists, f"Required table '{table_name}' does not exist"


@pytest.mark.p2
@pytest.mark.asyncio
async def test_tasks_table_schema(db_client):
    """Verify tasks table has correct columns and types."""
    async with db_client.pool.acquire() as conn:
        # Get column information
        columns = await conn.fetch(
            """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'tasks'
            ORDER BY ordinal_position
        """
        )

        column_info = {row["column_name"]: row for row in columns}

        # Verify required columns exist
        required_columns = {
            "task_id": {"data_type": "uuid", "is_nullable": "NO"},
            "circuit": {"data_type": "text", "is_nullable": "NO"},
            "submitted_at": {"data_type": "timestamp with time zone", "is_nullable": "NO"},
            "current_status": {"data_type": "USER-DEFINED", "is_nullable": "NO"},  # ENUM type
            "completed_at": {"data_type": "timestamp with time zone", "is_nullable": "YES"},
            "result": {"data_type": "jsonb", "is_nullable": "YES"},
            "error_message": {"data_type": "text", "is_nullable": "YES"},
        }

        for col_name, expected in required_columns.items():
            assert col_name in column_info, f"Column '{col_name}' missing from tasks table"
            actual = column_info[col_name]
            assert (
                actual["data_type"] == expected["data_type"]
            ), f"Column '{col_name}' has type '{actual['data_type']}', expected '{expected['data_type']}'"
            assert (
                actual["is_nullable"] == expected["is_nullable"]
            ), f"Column '{col_name}' nullable={actual['is_nullable']}, expected {expected['is_nullable']}"


@pytest.mark.p2
@pytest.mark.asyncio
async def test_status_history_table_schema(db_client):
    """Verify status_history table has correct columns and types."""
    async with db_client.pool.acquire() as conn:
        # Get column information
        columns = await conn.fetch(
            """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'status_history'
            ORDER BY ordinal_position
        """
        )

        column_info = {row["column_name"]: row for row in columns}

        # Verify required columns exist
        required_columns = {
            "id": {"data_type": "integer", "is_nullable": "NO"},
            "task_id": {"data_type": "uuid", "is_nullable": "NO"},
            "status": {"data_type": "USER-DEFINED", "is_nullable": "NO"},  # ENUM type
            "transitioned_at": {"data_type": "timestamp with time zone", "is_nullable": "NO"},
            "notes": {"data_type": "text", "is_nullable": "YES"},
        }

        for col_name, expected in required_columns.items():
            assert col_name in column_info, f"Column '{col_name}' missing from status_history table"
            actual = column_info[col_name]
            assert (
                actual["data_type"] == expected["data_type"]
            ), f"Column '{col_name}' has type '{actual['data_type']}', expected '{expected['data_type']}'"
            assert (
                actual["is_nullable"] == expected["is_nullable"]
            ), f"Column '{col_name}' nullable={actual['is_nullable']}, expected {expected['is_nullable']}"


@pytest.mark.p2
@pytest.mark.asyncio
async def test_tasks_table_indexes(db_client):
    """Verify tasks table has required indexes."""
    async with db_client.pool.acquire() as conn:
        # Get index information
        indexes = await conn.fetch(
            """
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'tasks'
        """
        )

        index_names = [row["indexname"] for row in indexes]

        # Verify required indexes
        required_indexes = ["tasks_pkey", "idx_task_status", "idx_task_submitted_at"]

        for index_name in required_indexes:
            assert (
                index_name in index_names
            ), f"Required index '{index_name}' missing from tasks table"


@pytest.mark.p2
@pytest.mark.asyncio
async def test_status_history_table_indexes(db_client):
    """Verify status_history table has required indexes."""
    async with db_client.pool.acquire() as conn:
        # Get index information
        indexes = await conn.fetch(
            """
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'status_history'
        """
        )

        index_names = [row["indexname"] for row in indexes]

        # Verify required indexes
        required_indexes = ["status_history_pkey", "idx_status_history_task_time"]

        for index_name in required_indexes:
            assert (
                index_name in index_names
            ), f"Required index '{index_name}' missing from status_history table"


@pytest.mark.p2
@pytest.mark.asyncio
async def test_taskstatus_enum_values(db_client):
    """Verify taskstatus ENUM has correct values."""
    async with db_client.pool.acquire() as conn:
        # Get ENUM values
        enum_values = await conn.fetch(
            """
            SELECT e.enumlabel
            FROM pg_type t
            JOIN pg_enum e ON t.oid = e.enumtypid
            WHERE t.typname = 'taskstatus'
            ORDER BY e.enumsortorder
        """
        )

        actual_values = [row["enumlabel"] for row in enum_values]
        expected_values = ["pending", "processing", "completed", "failed"]

        assert (
            actual_values == expected_values
        ), f"taskstatus ENUM values {actual_values} != expected {expected_values}"


@pytest.mark.p2
@pytest.mark.asyncio
async def test_foreign_key_constraint(db_client):
    """Verify status_history has foreign key to tasks table."""
    async with db_client.pool.acquire() as conn:
        # Get foreign key constraints
        constraints = await conn.fetch(
            """
            SELECT
                tc.constraint_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
            WHERE tc.table_name = 'status_history'
                AND tc.constraint_type = 'FOREIGN KEY'
        """
        )

        assert len(constraints) > 0, "No foreign key constraints found on status_history table"

        # Verify the constraint references tasks.task_id
        fk = constraints[0]
        assert (
            fk["column_name"] == "task_id"
        ), f"Foreign key on column '{fk['column_name']}', expected 'task_id'"
        assert (
            fk["foreign_table_name"] == "tasks"
        ), f"Foreign key references table '{fk['foreign_table_name']}', expected 'tasks'"
        assert (
            fk["foreign_column_name"] == "task_id"
        ), f"Foreign key references column '{fk['foreign_column_name']}', expected 'task_id'"
