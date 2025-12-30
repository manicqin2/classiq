"""
Database session management for async SQLAlchemy with PostgreSQL.

This module provides the database engine, session factory, and dependency
injection function for FastAPI routes.
"""

import time
from collections.abc import AsyncGenerator

import structlog
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.common.config import settings

# Get logger for database operations
logger = structlog.get_logger(__name__)


# Determine if we should echo SQL statements based on log level
echo_sql = settings.log_level.upper() == "DEBUG"

# Create async engine with connection pooling configuration
engine = create_async_engine(
    settings.database_url,
    echo=echo_sql,
    pool_pre_ping=True,  # Validate connections before use
    pool_size=10,  # Number of connections to keep open
    max_overflow=20,  # Maximum number of connections that can be created beyond pool_size
    # Use NullPool for testing environments if needed
    # poolclass=NullPool if settings.environment == "test" else None,
)


# Database query logging with execution time tracking
@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """
    Event listener to track query start time.

    This is called before a SQL statement is executed. We store the start time
    in the connection info dictionary for later calculation of execution time.
    """
    conn.info.setdefault("query_start_time", []).append(time.time())

    # Log query start at DEBUG level
    logger.debug(
        "Database query started",
        sql=statement[:200] if statement else "",  # Truncate to first 200 chars
        has_parameters=bool(parameters),
    )


@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """
    Event listener to log query execution time.

    This is called after a SQL statement is executed. We calculate the execution
    time and log it with the query details using structured logging.
    """
    # Calculate execution time
    total_time = None
    if conn.info.get("query_start_time"):
        start_time = conn.info["query_start_time"].pop(-1)
        total_time = time.time() - start_time

    # Prepare log data
    log_data = {
        "sql": statement[:200] if statement else "",  # Truncate to first 200 chars
        "execution_time_ms": round(total_time * 1000, 2) if total_time else None,
    }

    # Add parameter info (but not the actual values for security)
    if parameters:
        if isinstance(parameters, dict):
            log_data["parameter_count"] = len(parameters)
            log_data["parameter_keys"] = list(parameters.keys())[:10]  # First 10 keys
        elif isinstance(parameters, (list, tuple)):
            log_data["parameter_count"] = len(parameters)

    # Log at DEBUG level
    logger.debug("Database query completed", **log_data)


# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Prevent lazy-loading issues after commit
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function for FastAPI that provides a database session.

    This function creates a new database session for each request and ensures
    proper cleanup after the request is complete. It handles errors gracefully
    and always closes the session.

    Yields:
        AsyncSession: An async SQLAlchemy session for database operations.

    Example:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize the database connection.

    This function can be called on application startup to verify
    database connectivity.
    """
    async with engine.begin() as conn:
        # Import your models here to ensure they're registered
        # from api.models import Base
        # await conn.run_sync(Base.metadata.create_all)
        pass


async def close_db() -> None:
    """
    Close the database connection pool.

    This function should be called on application shutdown to properly
    close all database connections.
    """
    await engine.dispose()
