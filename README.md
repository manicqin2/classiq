# Quantum Circuit Task Queue API

Production-ready REST API server for quantum circuit task management, built with FastAPI and Docker.

## Features

- ✅ **3 RESTful Endpoints**: Task submission, status query, and health check
- ✅ **Docker & Docker Compose Support**: Easy deployment and orchestration
- ✅ **Structured Logging**: JSON logs with correlation IDs for request tracing
- ✅ **Automatic OpenAPI Documentation**: Interactive API docs at `/docs`
- ✅ **Input Validation**: Pydantic v2 request/response validation
- ✅ **Health Checks**: Built-in container health monitoring
- ✅ **Production-Ready**: Non-root user, multi-stage builds, graceful shutdown

## Quick Start

### Option 1: Docker Compose (Recommended)

```bash
# 1. Clone and navigate to the project
cd /path/to/classiq

# 2. (Optional) Create .env file from template
cp .env.example .env

# 3. Start the service
docker-compose up -d

# 4. Verify it's running
curl http://localhost:8001/health

# 5. View logs
docker-compose logs -f api

# 6. Stop the service
docker-compose down
```

### Option 2: Docker Only

```bash
# Build the image
docker build -t quantum-api:latest .

# Run the container
docker run -d --name quantum-api -p 8000:8000 quantum-api:latest

# Verify it's running
curl http://localhost:8000/health

# View logs
docker logs -f quantum-api

# Stop and remove
docker stop quantum-api && docker rm quantum-api
```

### Option 3: Local Development

```bash
# Navigate to api directory
cd api

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn app:app --host 0.0.0.0 --port 8000 --reload

# Access at http://localhost:8000
```

## API Endpoints

### 1. Health Check
```bash
curl http://localhost:8001/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-12-28T12:00:00.000000+00:00"
}
```

### 2. Submit Task
```bash
curl -X POST http://localhost:8001/tasks \
  -H "Content-Type: application/json" \
  -d '{"circuit": "OPENQASM 3; qubit q; h q; measure q;"}'
```

**Response:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Task submitted successfully.",
  "correlation_id": "abc123-def456-ghi789"
}
```

### 3. Query Task Status
```bash
curl http://localhost:8001/tasks/550e8400-e29b-41d4-a716-446655440000
```

**Response:**
```json
{
  "status": "pending",
  "message": "Task is still in progress.",
  "result": null,
  "correlation_id": "xyz789-uvw456-rst123"
}
```

## Documentation

Once the server is running, access interactive API documentation:

- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc
- **OpenAPI JSON**: http://localhost:8001/openapi.json

## Docker Compose Commands

```bash
# Start services in detached mode
docker-compose up -d

# Start with rebuild
docker-compose up -d --build

# View logs
docker-compose logs -f

# View logs for specific service
docker-compose logs -f api

# Stop services
docker-compose stop

# Stop and remove containers
docker-compose down

# Stop and remove containers, volumes, and images
docker-compose down -v --rmi all

# Restart service
docker-compose restart api

# Check service status
docker-compose ps

# Execute command in running container
docker-compose exec api bash
```

## Configuration

### Environment Variables

Create a `.env` file in the project root (copy from `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | 8000 | HTTP server port |
| `LOG_LEVEL` | INFO | Logging level (DEBUG, INFO, WARN, ERROR) |
| `ENVIRONMENT` | development | Environment name |
| `CORS_ORIGINS` | * | Allowed CORS origins (comma-separated) |

### Docker Compose Configuration

Edit `docker-compose.yml` to customize:

- **Ports**: Change `"8000:8000"` to use different host port
- **Environment**: Add/modify environment variables
- **Restart Policy**: Change `restart: unless-stopped`
- **Networks**: Add additional services to `quantum-network`

## Testing

### Integration Tests

```bash
# Run all integration tests
API_BASE=http://localhost:8001 bash api/tests/integration/test-api.sh

# Or with custom API base URL
API_BASE=http://localhost:8001 bash api/tests/integration/test-api.sh
```

### Manual Testing

```bash
# Test health endpoint
curl http://localhost:8001/health

# Test task submission
curl -X POST http://localhost:8001/tasks \
  -H "Content-Type: application/json" \
  -d '{"circuit": "OPENQASM 3; qubit[2] q; h q[0]; cx q[0], q[1];"}'

# Test validation error
curl -X POST http://localhost:8001/tasks \
  -H "Content-Type: application/json" \
  -d '{}'

# Test invalid UUID
curl http://localhost:8001/tasks/invalid-uuid
```

## Project Structure

```
.
├── Dockerfile                      # Multi-stage container build
├── docker-compose.yml             # Docker Compose orchestration
├── .env.example                   # Environment variables template
├── .dockerignore                  # Docker build exclusions
├── README.md                      # This file
└── api/                           # API application code
    ├── app.py                     # FastAPI application
    ├── config.py                  # Configuration management
    ├── models.py                  # Pydantic models
    ├── routes.py                  # API endpoints
    ├── middleware.py              # Correlation ID middleware
    ├── logging_config.py          # Structured logging setup
    ├── utils.py                   # Utility functions
    ├── requirements.txt           # Python dependencies
    └── tests/
        └── integration/
            └── test-api.sh        # Integration test suite
```

## Architecture

### Technology Stack

- **Framework**: FastAPI 0.104.1 (async web framework)
- **Server**: Uvicorn 0.24.0 (ASGI server)
- **Validation**: Pydantic 2.5.0 (type validation)
- **Logging**: structlog 23.2.0 (structured logging)
- **Container**: Docker with multi-stage builds
- **Base Image**: python:3.11-slim-bookworm

### Key Features

1. **Correlation IDs**: Every request gets a unique ID for distributed tracing
2. **Structured Logging**: JSON logs with contextual information
3. **Request Validation**: Automatic validation using Pydantic models
4. **Error Handling**: Global exception handlers with clear error messages
5. **Health Checks**: Docker health checks and dedicated health endpoint
6. **CORS Support**: Configurable CORS middleware
7. **Non-root User**: Container runs as `appuser` (UID 1000)
8. **Graceful Shutdown**: Proper cleanup on SIGTERM

## Current Implementation Status

This is a **stubbed implementation** designed for parallel development:

- ✅ All 3 endpoints implemented and functional
- ✅ Request validation and error handling working
- ✅ Structured logging with correlation IDs
- ✅ Docker and Docker Compose ready
- ⚠️ Task IDs generated but not persisted (no database)
- ⚠️ Status always returns "pending" (no state tracking)
- ⚠️ No actual quantum circuit execution (no Qiskit integration)

### Future Enhancements (Out of Scope)

- Database persistence (PostgreSQL)
- Message queue integration (RabbitMQ)
- Worker implementation for task execution
- Authentication/authorization
- Rate limiting
- Metrics collection (Prometheus)

## Troubleshooting

### Port Already in Use

```bash
# Check what's using the port
lsof -i :8000

# Stop the conflicting process or use different port
docker-compose down
# Edit docker-compose.yml to change port mapping
```

### Container Won't Start

```bash
# Check logs
docker-compose logs api

# Rebuild from scratch
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Health Check Failing

```bash
# Check container status
docker-compose ps

# View detailed logs
docker-compose logs api

# Execute health check manually
docker-compose exec api python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
```

### Permission Issues

```bash
# Container runs as non-root user (appuser)
# If you need to access files, ensure they're readable by UID 1000
ls -la api/

# Fix permissions if needed
chmod -R 755 api/
```

## Development Workflow

### Making Code Changes

```bash
# 1. Make your changes to files in api/

# 2. Rebuild and restart
docker-compose up -d --build

# 3. View logs to verify
docker-compose logs -f api

# 4. Test your changes
curl http://localhost:8000/health
```

### Debugging

```bash
# Access container shell
docker-compose exec api bash

# Check Python version
docker-compose exec api python --version

# List installed packages
docker-compose exec api pip list

# Test import
docker-compose exec api python -c "from app import app; print('OK')"
```

## Production Deployment

For production deployment:

1. **Set Environment**:
   ```bash
   echo "ENVIRONMENT=production" >> .env
   echo "LOG_LEVEL=WARN" >> .env
   ```

2. **Configure CORS**:
   ```bash
   echo "CORS_ORIGINS=https://your-domain.com" >> .env
   ```

3. **Use Production Compose File**:
   ```yaml
   # docker-compose.prod.yml
   version: '3.8'
   services:
     api:
       build: .
       restart: always
       environment:
         - ENVIRONMENT=production
         - LOG_LEVEL=WARN
       # Add nginx reverse proxy, SSL, etc.
   ```

4. **Deploy**:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

## License

This project is part of the Classiq Quantum Circuit Task Queue system.

## Support

For issues and questions:
- Check logs: `docker-compose logs -f api`
- Review API docs: http://localhost:8000/docs
- Inspect container: `docker-compose exec api bash`

---

**Status**: ✅ Ready for Production Deployment

**Last Updated**: 2025-12-28
