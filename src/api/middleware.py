"""
Middleware for correlation ID handling and request/response logging.
"""

import uuid
from contextvars import ContextVar

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Context variable for correlation ID
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")

logger = structlog.get_logger(__name__)


def get_correlation_id() -> str:
    """Get the current correlation ID from context."""
    return correlation_id_var.get()


def set_correlation_id(correlation_id: str):
    """Set the correlation ID in context."""
    correlation_id_var.set(correlation_id)


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract or generate correlation IDs for request tracing.

    Extracts X-Correlation-ID from request headers or generates a new UUID.
    Injects correlation ID into response headers and logging context.
    """

    async def dispatch(self, request: Request, call_next):
        """Process request and inject correlation ID."""
        # Extract or generate correlation ID
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())

        # Store in context for access across the request lifecycle
        set_correlation_id(correlation_id)

        # Bind to structlog context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

        # Log incoming request
        logger.info(
            "Request received",
            method=request.method,
            path=request.url.path,
            client_host=request.client.host if request.client else None,
        )

        # Process request
        response: Response = await call_next(request)

        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id

        # Log response
        logger.info(
            "Request completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
        )

        return response
