# Claude AI Agent Context

**Last Updated:** 2025-12-28
**Purpose:** Technology stack and conventions for code generation

---

## Project: Quantum Circuit Task Queue System

### Technology Stack

#### Feature: Standalone API Server (2-api-server-docker)

**Web Framework:**
- FastAPI 0.104+ (Python)
- Async/await patterns
- Pydantic v2 for validation
- Uvicorn ASGI server

**Container:**
- Base Image: python:3.11-slim-bookworm
- Multi-stage builds
- Non-root user (UID 1000)
- Port 8000 exposed

**Logging:**
- structlog for structured JSON logs
- Fields: timestamp, level, message, correlation_id, component, environment
- Correlation ID propagation via contextvars

**Validation:**
- Pydantic models for request/response
- UUID v4 for task IDs
- snake_case naming convention

**Configuration:**
- Environment variables: PORT, LOG_LEVEL, ENVIRONMENT, CORS_ORIGINS
- Defaults in code, overridden by env vars

---

## Coding Conventions

### Python Style

- **PEP 8** compliance
- **Type hints** on all functions
- **Async functions** for I/O operations
- **Pydantic models** for data validation
- **docstrings** for public functions

### API Design

- **RESTful** endpoints
- **snake_case** for JSON fields
- **UUID v4** for identifiers
- **Correlation IDs** in all responses

### Error Handling

- **Custom exception handlers** for FastAPI
- **422 → 400** mapping for validation errors
- **Correlation IDs** in error responses
- **No internal details** in 500 errors

### Logging

- **Structured JSON** format
- **Correlation IDs** in all log entries
- **Context binding** with contextvars
- **Log levels**: INFO (requests), WARN (client errors), ERROR (server errors)

---

## File Structure

```
api/
├── Dockerfile              # Multi-stage container build
├── requirements.txt        # Python dependencies
├── app.py                  # Main FastAPI application
├── models.py               # Pydantic request/response models
├── routes.py               # Endpoint handlers
├── logging_config.py       # Structlog configuration
├── config.py               # Environment variable loading
├── middleware.py           # Correlation ID injection
└── tests/
    ├── test_endpoints.py   # Endpoint unit tests
    └── test_validation.py  # Validation unit tests
```

---

## Dependencies

### Production Requirements

```
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
structlog==23.2.0
python-json-logger==2.0.7
```

### Development Requirements

```
pytest==7.4.3
httpx==0.25.2  # For FastAPI test client
pytest-asyncio==0.21.1
```

---

## Code Generation Guidelines

When generating code for this project:

1. **Use async/await** for all endpoint handlers
2. **Include type hints** on all functions and variables
3. **Use Pydantic models** for request/response validation
4. **Add correlation ID middleware** for request tracing
5. **Configure structlog** for JSON logging
6. **Implement health check endpoint** at `/health`
7. **Use CORS middleware** with configurable origins
8. **Add global exception handlers** for consistent error responses
9. **Generate UUID v4** for task IDs using `uuid.uuid4()`
10. **Use environment variables** for configuration

---

## Manual Additions

<!-- USER_MANUAL_START -->

<!-- USER_MANUAL_END -->

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-28 | Initial context for api-server-docker feature |
