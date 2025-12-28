# Quantum Circuit Task Queue API

Production-ready REST API server for quantum circuit task management with Docker support.

## Quick Start

### Local Development

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the server:**
   ```bash
   uvicorn app:app --reload --port 8000
   ```

3. **Access the API:**
   - API: http://localhost:8000
   - Interactive Docs: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

### Docker Deployment

1. **Build the image:**
   ```bash
   docker build -t quantum-api:latest .
   ```

2. **Run the container:**
   ```bash
   docker run -d --name quantum-api -p 8000:8000 quantum-api:latest
   ```

3. **View logs:**
   ```bash
   docker logs -f quantum-api
   ```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | 8000 | HTTP server port |
| `LOG_LEVEL` | INFO | Logging verbosity (DEBUG, INFO, WARN, ERROR) |
| `ENVIRONMENT` | development | Environment name (development, staging, production) |
| `CORS_ORIGINS` | * | Allowed CORS origins (comma-separated) |

## API Endpoints

### POST /tasks
Submit a quantum circuit for execution.

**Request:**
```json
{
  "circuit": "OPENQASM 3; qubit q; h q; measure q;"
}
```

**Response:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Task submitted successfully.",
  "correlation_id": "abc123-def456"
}
```

### GET /tasks/{task_id}
Query task status and results.

**Response:**
```json
{
  "status": "pending",
  "message": "Task is still in progress.",
  "correlation_id": "xyz789-uvw456"
}
```

### GET /health
Health check for monitoring.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-12-28T12:00:00Z"
}
```

## Testing

Run unit tests:
```bash
pytest tests/unit/ -v
```

Run integration tests:
```bash
./tests/integration/test-api.sh
```

## Architecture

- **Framework:** FastAPI with async/await
- **Validation:** Pydantic v2
- **Logging:** structlog (structured JSON)
- **Container:** Docker with non-root user
- **Health Checks:** Built-in liveness/readiness probes

## Development

### Project Structure

```
api/
├── app.py                 # Main FastAPI application
├── config.py              # Configuration from environment
├── models.py              # Pydantic request/response models
├── routes.py              # API endpoint handlers
├── middleware.py          # Correlation ID middleware
├── logging_config.py      # Structured logging setup
├── utils.py               # Utility functions
├── Dockerfile             # Container image definition
├── requirements.txt       # Python dependencies
└── tests/                 # Test suite
```

### Adding New Endpoints

1. Define Pydantic models in `models.py`
2. Implement handler in `routes.py`
3. FastAPI automatically generates OpenAPI docs

## License

MIT
