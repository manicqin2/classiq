# Technology Research: Standalone API Server with Docker Setup

**Created:** 2025-12-28
**Feature:** Standalone API Server with Docker Setup
**Purpose:** Resolve technical decisions and validate technology choices

---

## Executive Summary

This document resolves all NEEDS CLARIFICATION items from the implementation plan, providing specific technology choices, rationale, and alternatives considered. All decisions prioritize rapid development of a production-ready stub API while maintaining alignment with constitution principles.

---

## Decision 1: Web Framework Selection

### Context

Need to select a web framework for implementing REST endpoints with request validation, structured logging, and OpenAPI documentation.

### Decision

**Selected: FastAPI (Python)**

### Rationale

1. **Built-in Validation**: Pydantic integration provides declarative request/response validation with automatic error messages
2. **Async Support**: Native async/await enables high concurrency with minimal resource usage
3. **Auto Documentation**: OpenAPI/Swagger UI generated automatically from code
4. **Rapid Development**: Stub endpoints can be implemented with minimal boilerplate
5. **Type Safety**: Python type hints enable IDE autocomplete and catch errors early
6. **Production Ready**: Used widely in production systems, mature ecosystem
7. **Constitution Alignment**:
   - Principle 3 (Observable): Built-in request/response logging middleware
   - Principle 8 (Production Patterns): Industry-standard framework

### Alternatives Considered

**Flask (Python)**:
- **Pros**: Simpler, more mature, easier learning curve
- **Cons**: Synchronous (limits concurrency), manual validation, no auto-docs
- **Verdict**: Good for simple cases, but FastAPI's validation alone justifies the choice

**Go (net/http + gorilla/mux)**:
- **Pros**: Superior performance, smaller images, static typing
- **Cons**: More verbose, slower development time for stubs, steeper learning curve
- **Verdict**: Overkill for stub phase; consider for performance-critical future services

**Node.js (Express)**:
- **Pros**: Async by default, JavaScript familiarity for full-stack teams
- **Cons**: Loosely typed (TypeScript adds complexity), less robust validation libraries
- **Verdict**: Viable but FastAPI's validation ecosystem is superior

### Implementation Notes

- **Version**: FastAPI 0.104+ (latest stable)
- **ASGI Server**: Uvicorn for development and production
- **Dependencies**: Pydantic v2 for validation models

---

## Decision 2: Container Base Image

### Context

Need to select a Docker base image that balances size, security, compatibility, and build time.

### Decision

**Selected: python:3.11-slim-bookworm**

### Rationale

1. **Balanced Size**: ~150MB vs 900MB (full) or 50MB (alpine)
2. **Compatibility**: Debian-based, works with all Python packages (unlike Alpine)
3. **Security**: Regular Debian security updates, official Python image
4. **Build Performance**: Faster than full image, more compatible than Alpine
5. **Production Proven**: Widely used in production environments
6. **Constitution Alignment**:
   - Principle 8 (Production Patterns): Industry-standard base image

### Alternatives Considered

**python:3.11-alpine**:
- **Pros**: Smaller size (~50MB), minimal attack surface
- **Cons**: musl libc causes issues with many Python packages, slower builds
- **Verdict**: Too risky for compatibility; size difference not critical for stub phase

**python:3.11 (full Debian)**:
- **Pros**: Maximum compatibility, all build tools included
- **Cons**: Unnecessarily large (~900MB), more attack surface
- **Verdict**: Wasteful for minimal application needs

**Distroless (gcr.io/distroless/python3)**:
- **Pros**: Maximum security, no shell/package manager
- **Cons**: Difficult debugging, requires multi-stage builds, overkill for stubs
- **Verdict**: Consider for future production hardening

### Implementation Notes

- **Multi-stage Build**: Use full Python image for dependency installation, slim for runtime
- **Non-root User**: Create `appuser` with UID 1000
- **Security**: Pin versions, scan with trivy/grype

---

## Decision 3: Request Validation Library

### Context

Need robust validation for request payloads with clear error messages.

### Decision

**Selected: Pydantic v2 (built into FastAPI)**

### Rationale

1. **Native Integration**: FastAPI uses Pydantic automatically for request/response models
2. **Declarative Schemas**: Define validation rules as Python classes with type hints
3. **Automatic Errors**: Validation failures generate detailed 422 responses
4. **Type Safety**: Runtime validation matches static type hints
5. **Performance**: Pydantic v2 is Rust-based, extremely fast
6. **JSON Schema**: Generates JSON schemas for documentation
7. **Constitution Alignment**:
   - Principle 3 (Observable): Detailed error messages aid debugging
   - Principle 2 (Fault Tolerance): Invalid requests rejected before processing

### Alternatives Considered

**Marshmallow**:
- **Pros**: Mature, flexible, serialization + validation
- **Cons**: Not integrated with FastAPI, requires boilerplate
- **Verdict**: Good for Flask, but Pydantic is the FastAPI standard

**JSON Schema + jsonschema**:
- **Pros**: Language-agnostic schema format
- **Cons**: Verbose schemas, poor Python integration, manual error formatting
- **Verdict**: Too low-level for this use case

**Cerberus**:
- **Pros**: Dictionary-based validation, simple
- **Cons**: Not type-safe, no FastAPI integration
- **Verdict**: Doesn't leverage Python's type system

### Implementation Notes

- **Models**: Define `TaskSubmitRequest` and `TaskStatusResponse` as Pydantic models
- **Custom Validators**: Add validator for circuit non-empty string
- **Error Handling**: Customize 422 response format to match spec's 400 structure

---

## Decision 4: Logging Library

### Context

Need structured logging with JSON output for container log aggregation.

### Decision

**Selected: structlog + Python logging**

### Rationale

1. **Structured Logs**: Native JSON output with configurable fields
2. **Context Binding**: Attach correlation IDs and metadata to logger instances
3. **Performance**: Async-friendly, minimal overhead
4. **Flexibility**: Works with standard Python logging, Uvicorn integration
5. **Readability**: Supports both JSON (production) and colored (development) output
6. **Constitution Alignment**:
   - Principle 3 (Observable): Structured logs enable easy parsing and querying

### Alternatives Considered

**Python logging (stdlib)**:
- **Pros**: Built-in, no dependencies, familiar
- **Cons**: Awkward JSON formatting, poor structured logging support
- **Verdict**: Usable but structlog is industry standard for structured logs

**loguru**:
- **Pros**: Simple API, colored output, automatic context
- **Cons**: Less flexible than structlog, harder JSON configuration
- **Verdict**: Good for simple apps, but structlog better for production

**python-json-logger**:
- **Pros**: Simple JSON formatter for stdlib logging
- **Cons**: Basic, no context binding like structlog
- **Verdict**: Minimal but lacks structured logging features

### Implementation Notes

- **Configuration**: JSON format for production, colored for development (ENV-based)
- **Fields**: timestamp, level, message, correlation_id, component, environment
- **Middleware**: FastAPI middleware to inject correlation IDs
- **Uvicorn Integration**: Configure Uvicorn to use structlog

---

## Decision 5: Response Field Naming Convention

### Context

Choose between snake_case and camelCase for JSON response field names.

### Decision

**Selected: snake_case**

### Rationale

1. **Python Standard**: Aligns with Python naming conventions (PEP 8)
2. **Pydantic Default**: Pydantic models use snake_case by default
3. **Consistency**: Backend defines API contract; internal consistency preferred
4. **JSON Preference**: Many JSON APIs use snake_case (GitHub, Stripe, Slack)
5. **Less Configuration**: No aliasing needed in Pydantic models

### Alternatives Considered

**camelCase**:
- **Pros**: JavaScript/frontend standard, common in REST APIs
- **Cons**: Requires Pydantic alias configuration, inconsistent with Python code
- **Verdict**: Adds complexity for frontend preference

### Implementation Notes

- **Field Names**: `task_id`, `correlation_id`, `status_code`, etc.
- **OpenAPI Schema**: Will show snake_case in documentation
- **Frontend Guidance**: Frontend can convert to camelCase if needed (common practice)

---

## Decision 6: UUID Library

### Context

Generate unique task IDs that are collision-resistant and distributed-safe.

### Decision

**Selected: Python uuid.uuid4() (stdlib)**

### Rationale

1. **No Dependencies**: Built into Python standard library
2. **Collision-Resistant**: UUID v4 is statistically unique (2^122 space)
3. **Distributed-Safe**: No coordination needed between API instances
4. **String Representation**: Hyphenated format (550e8400-e29b-41d4-a716-446655440000)
5. **Constitution Alignment**:
   - Principle 4 (Stateless): UUID generation requires no shared state

### Alternatives Considered

**shortuuid**:
- **Pros**: Shorter IDs (22 chars vs 36), URL-safe
- **Cons**: External dependency, less familiar format
- **Verdict**: Nice-to-have but UUID is sufficient and standard

**ULID (Universally Unique Lexicographically Sortable Identifier)**:
- **Pros**: Sortable by creation time, shorter
- **Cons**: Requires library, less standard than UUID
- **Verdict**: Interesting for future but UUID meets requirements

**Sequential Integers**:
- **Pros**: Simple, short, human-readable
- **Cons**: Requires centralized counter (database/Redis), not distributed-safe
- **Verdict**: Violates stateless principle

### Implementation Notes

- **Generation**: `str(uuid.uuid4())` returns hyphenated string
- **Validation**: Use regex or UUID parsing to validate format in GET requests
- **Database Ready**: UUID type supported in PostgreSQL (future feature)

---

## Decision 7: CORS Configuration

### Context

Determine Cross-Origin Resource Sharing policy for API access from web frontends.

### Decision

**Selected: Permissive CORS for development, configurable for production**

### Rationale

1. **Development Flexibility**: Allow all origins during local development
2. **Production Control**: Configurable via CORS_ORIGINS environment variable
3. **Security**: Production deployment sets specific allowed origins
4. **Standard Practice**: Common pattern for API development

### Alternatives Considered

**No CORS (Same-Origin Only)**:
- **Pros**: Maximum security
- **Cons**: Blocks all web frontend access
- **Verdict**: Unworkable for modern web apps

**Always Permissive (***)**:
- **Pros**: Maximum flexibility
- **Cons**: Security risk in production
- **Verdict**: Acceptable for development, not production

### Implementation Notes

- **Default**: `CORS_ORIGINS=*` (development)
- **Production**: `CORS_ORIGINS=https://app.example.com,https://dashboard.example.com`
- **FastAPI Middleware**: `CORSMiddleware` with configurable origins

---

## Decision 8: Error Response Format

### Context

Standardize error response structure for client parsing.

### Decision

**Selected: Consistent JSON structure with correlation IDs**

### Format

```json
{
  "error": "Brief error description",
  "details": {"field": "Specific validation error"},
  "correlation_id": "uuid-here"
}
```

### Rationale

1. **Consistency**: Same structure for all error responses
2. **Debuggability**: Correlation ID enables log tracing
3. **Clarity**: Separate generic message and specific details
4. **Client-Friendly**: Structured details enable UI field highlighting

### Implementation Notes

- **FastAPI Exception Handlers**: Custom handler for validation errors (422 → 400)
- **Generic Errors**: 500 errors return generic message (no internal details)
- **Validation Details**: Field-level errors in `details` object

---

## Decision 9: Container Port

### Context

Choose default port for HTTP server.

### Decision

**Selected: 8000 (configurable via PORT environment variable)**

### Rationale

1. **Python Standard**: Common default for Python web frameworks
2. **Non-Privileged**: Port >1024 allows non-root container user
3. **Conflict-Free**: Unlikely to conflict with other services
4. **Uvicorn Default**: Uvicorn uses 8000 by default

### Implementation Notes

- **Environment Variable**: `PORT=8000` (default)
- **Dockerfile EXPOSE**: `EXPOSE 8000`
- **Container Runtime**: `-p 8000:8000` for local testing

---

## Best Practices Research

### FastAPI Production Patterns

**Researched Best Practices**:
1. **Async Everywhere**: Use `async def` for all endpoint handlers
2. **Dependency Injection**: Use FastAPI's dependency system for testability
3. **Lifespan Events**: Use `@app.on_event("startup")` for initialization
4. **Exception Handlers**: Register custom handlers for all exception types
5. **Middleware Order**: CORS → Logging → Exception Handling → Routes

**References**:
- FastAPI documentation: https://fastapi.tiangolo.com/
- Real World Python: fastapi-best-practices (GitHub)

### Docker Security for Python

**Researched Best Practices**:
1. **Non-Root User**: Create and switch to non-root user
2. **Multi-Stage Builds**: Separate build and runtime stages
3. **Minimal Packages**: Install only production dependencies
4. **Health Checks**: Use HEALTHCHECK instruction
5. **Version Pinning**: Pin all dependency versions

**References**:
- Docker Official Images best practices
- OWASP Docker Security Cheat Sheet

### Structured Logging Standards

**Researched Best Practices**:
1. **Correlation IDs**: Generate or extract from X-Correlation-ID header
2. **Standard Fields**: timestamp, level, message, logger, correlation_id
3. **Log Levels**: INFO for normal, WARN for client errors, ERROR for server errors
4. **Performance**: Use async logging, buffer writes
5. **Context**: Attach request metadata (method, path, user_agent)

**References**:
- structlog documentation
- Twelve-Factor App (Logs section)

---

## Technology Stack Summary

| Component | Technology | Version | Rationale |
|-----------|-----------|---------|-----------|
| **Web Framework** | FastAPI | 0.104+ | Built-in validation, async, auto-docs |
| **ASGI Server** | Uvicorn | 0.24+ | Production-ready, async support |
| **Validation** | Pydantic | 2.5+ | Native FastAPI integration |
| **Logging** | structlog | 23.2+ | Structured JSON logs |
| **Base Image** | python:3.11-slim | latest | Balance of size and compatibility |
| **UUID Generation** | uuid (stdlib) | built-in | Standard, no dependencies |
| **Container Runtime** | Docker | 20.10+ | Industry standard |

---

## Implementation Guidelines

### Project Structure

```
api/
├── Dockerfile
├── requirements.txt
├── app.py                 # Main FastAPI application
├── models.py              # Pydantic request/response models
├── routes.py              # Endpoint handlers
├── logging_config.py      # Structlog configuration
├── config.py              # Environment variable loading
└── tests/
    ├── test_endpoints.py
    └── test_validation.py
```

### Key Dependencies (requirements.txt)

```
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
structlog==23.2.0
python-json-logger==2.0.7  # Fallback formatter
```

### Environment Variables

```bash
PORT=8000                    # HTTP server port
LOG_LEVEL=INFO               # Logging verbosity
ENVIRONMENT=development      # Deployment environment
CORS_ORIGINS=*               # Allowed CORS origins
```

---

## Conclusion

All technical decisions have been made with clear rationale. The chosen stack (FastAPI + Pydantic + structlog + Docker) provides:

✅ Rapid development of stubbed endpoints
✅ Production-ready patterns (logging, validation, containerization)
✅ Full constitution compliance
✅ Clear path to enhance with database and message queue
✅ Industry-standard technologies with strong community support

**Next Phase:** Proceed to Phase 1 (Design & Contracts) to generate data models and OpenAPI specification.

---

## Document History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-12-28 | Initial research findings | Claude |
