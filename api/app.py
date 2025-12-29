"""
Main FastAPI application for Quantum Circuit Task Queue API.

This is a stubbed implementation providing foundational endpoints for parallel development.
Actual task execution and persistence will be added in subsequent features.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from config import settings
from middleware import CorrelationIDMiddleware
import logging_config  # Initialize logging
from db.session import init_db, close_db
from messaging import get_rabbitmq_connection, cleanup_rabbitmq

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info(
        "Application starting",
        environment=settings.environment,
        log_level=settings.log_level,
    )

    # Initialize database connection pool
    await init_db()
    logger.info("Database connection pool initialized")

    # Initialize RabbitMQ connection
    try:
        await get_rabbitmq_connection()
        logger.info("RabbitMQ connection initialized")
    except Exception as e:
        logger.error(
            "Failed to initialize RabbitMQ connection during startup",
            error=str(e),
            exc_info=True
        )
        # Continue startup even if RabbitMQ is unavailable
        # API will return 503 for task submissions

    logger.info("Application startup complete")

    yield

    # Shutdown - gracefully drain in-flight requests
    logger.info("Application shutdown initiated")

    # Close RabbitMQ connections
    try:
        await cleanup_rabbitmq()
        logger.info("RabbitMQ connections closed")
    except Exception as e:
        logger.error(
            "Error during RabbitMQ cleanup",
            error=str(e),
            exc_info=True
        )

    # Close database connections
    await close_db()
    logger.info("Database connections closed")

    logger.info("Application shutdown complete")
    # Note: FastAPI/Uvicorn handles connection draining automatically


# Initialize FastAPI application
app = FastAPI(
    title="Quantum Circuit Task Queue API",
    description="REST API for submitting quantum circuit execution tasks and retrieving results. "
    "This is a stubbed implementation providing foundational endpoints for parallel development.",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
cors_origins = settings.cors_origins.split(",") if settings.cors_origins != "*" else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add correlation ID middleware
app.add_middleware(CorrelationIDMiddleware)

# Exception handlers
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with consistent error response format."""
    from middleware import get_correlation_id

    errors = {}
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"] if loc != "body")
        errors[field] = error["msg"]

    logger.warning(
        "Validation error",
        errors=errors,
        method=request.method,
        path=request.url.path,
    )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "Validation failed",
            "details": errors,
            "correlation_id": get_correlation_id(),
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors with generic error message."""
    from middleware import get_correlation_id

    logger.error(
        "Unhandled exception",
        exc_info=exc,
        method=request.method,
        path=request.url.path,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "correlation_id": get_correlation_id(),
        },
    )


# Register routes
from routes import router as api_router

app.include_router(api_router)
