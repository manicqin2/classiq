# Docker Compose Quick Start Guide

## Prerequisites

- Docker Desktop installed and running
- Docker Compose (included with Docker Desktop)

## Getting Started

### 1. Start the Service

```bash
# From the project root directory
docker-compose up -d
```

The `-d` flag runs containers in detached mode (background).

**Expected output:**
```
 Network classiq_quantum-network  Created
 Container quantum-api  Created
 Container quantum-api  Started
```

### 2. Verify It's Running

```bash
# Check container status
docker-compose ps

# Test the health endpoint
curl http://localhost:8001/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-12-28T13:10:06.538999+00:00"
}
```

### 3. View Logs

```bash
# View all logs
docker-compose logs

# Follow logs in real-time
docker-compose logs -f

# View last 20 lines
docker-compose logs --tail=20

# View logs for specific service
docker-compose logs -f api
```

### 4. Stop the Service

```bash
# Stop containers (keeps containers and networks)
docker-compose stop

# Stop and remove containers and networks
docker-compose down

# Stop, remove everything including volumes
docker-compose down -v
```

## Common Commands

### Service Management

```bash
# Start services
docker-compose up -d

# Start with rebuild
docker-compose up -d --build

# Restart service
docker-compose restart api

# Stop services
docker-compose stop

# Remove stopped containers
docker-compose down
```

### Logs and Debugging

```bash
# View logs
docker-compose logs -f api

# Execute command in container
docker-compose exec api bash

# Check Python version
docker-compose exec api python --version

# Test imports
docker-compose exec api python -c "from app import app"
```

### Monitoring

```bash
# Check service status
docker-compose ps

# View resource usage
docker stats quantum-api

# Inspect service configuration
docker-compose config
```

## Testing the API

### Health Check
```bash
curl http://localhost:8001/health
```

### Submit Task
```bash
curl -X POST http://localhost:8001/tasks \
  -H "Content-Type: application/json" \
  -d '{"circuit": "OPENQASM 3; qubit q; h q; measure q;"}'
```

### Query Task Status
```bash
# Use the task_id from the submit response
curl http://localhost:8001/tasks/YOUR-TASK-ID-HERE
```

### Access API Documentation
Open in your browser:
- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Copy from example
cp .env.example .env

# Edit as needed
nano .env
```

**Available variables:**
- `PORT` - Server port (default: 8000)
- `LOG_LEVEL` - Logging level (default: INFO)
- `ENVIRONMENT` - Environment name (default: development)
- `CORS_ORIGINS` - Allowed CORS origins (default: *)

### Change Port

Edit `docker-compose.yml`:

```yaml
ports:
  - "9000:8000"  # Change 9000 to your desired port
```

Then restart:
```bash
docker-compose down
docker-compose up -d
```

## Troubleshooting

### Port Already in Use

**Error:** `Bind for 0.0.0.0:8001 failed: port is already allocated`

**Solution:**
```bash
# Check what's using the port
lsof -i :8001

# Either stop the conflicting process, or change the port in docker-compose.yml
```

### Container Won't Start

```bash
# View logs
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

# View detailed health check logs
docker inspect quantum-api --format='{{json .State.Health}}' | jq .

# Manually run health check
docker-compose exec api python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
```

### Code Changes Not Reflected

```bash
# Rebuild and restart
docker-compose up -d --build

# Or force rebuild
docker-compose build --no-cache
docker-compose up -d --force-recreate
```

### Permission Denied

Container runs as non-root user (UID 1000). If you encounter permission issues:

```bash
# Check file permissions
ls -la api/

# Fix if needed
chmod -R 755 api/
```

## Development Workflow

### Making Code Changes

1. **Edit files** in the `api/` directory
2. **Rebuild**: `docker-compose up -d --build`
3. **View logs**: `docker-compose logs -f api`
4. **Test**: `curl http://localhost:8001/health`

### Debugging

```bash
# Access container shell
docker-compose exec api bash

# Inside container:
# - Check files: ls -la
# - View logs: cat /app/logs/*.log
# - Test Python: python -c "from app import app"
# - Check environment: env | grep -E "PORT|LOG_LEVEL"
```

### Running Integration Tests

```bash
# Update API base URL and run tests
API_BASE=http://localhost:8001 bash api/tests/integration/test-api.sh
```

## Production Deployment

### Create Production Configuration

Create `docker-compose.prod.yml`:

```yaml
services:
  api:
    build: .
    container_name: quantum-api-prod
    ports:
      - "8001:8000"
    environment:
      - PORT=8000
      - LOG_LEVEL=WARN
      - ENVIRONMENT=production
      - CORS_ORIGINS=https://your-domain.com
    restart: always
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
      interval: 30s
      timeout: 3s
      start_period: 5s
      retries: 3
    networks:
      - quantum-network

networks:
  quantum-network:
    driver: bridge
```

### Deploy to Production

```bash
# Use production config
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f
```

## Architecture

### Services

- **api**: FastAPI application server
  - Built from `Dockerfile`
  - Exposes port 8001 (maps to internal 8000)
  - Runs as non-root user (appuser)
  - Health check every 30 seconds

### Networks

- **quantum-network**: Bridge network for service communication
  - Allows future services (database, queue, etc.) to connect

### Volumes

Currently no persistent volumes (stateless API).

Future enhancements may include:
- Database volume for PostgreSQL
- Redis volume for caching
- Log volume for centralized logging

## Next Steps

### Add Database

```yaml
services:
  db:
    image: postgres:15
    container_name: quantum-db
    environment:
      - POSTGRES_DB=quantum
      - POSTGRES_USER=quantum
      - POSTGRES_PASSWORD=quantum
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - quantum-network

volumes:
  postgres_data:
```

### Add Message Queue

```yaml
services:
  rabbitmq:
    image: rabbitmq:3-management
    container_name: quantum-queue
    ports:
      - "5672:5672"
      - "15672:15672"
    networks:
      - quantum-network
```

## Useful Commands Reference

| Command | Description |
|---------|-------------|
| `docker-compose up -d` | Start services in background |
| `docker-compose down` | Stop and remove containers |
| `docker-compose ps` | List running services |
| `docker-compose logs -f` | Follow logs in real-time |
| `docker-compose restart` | Restart all services |
| `docker-compose exec api bash` | Access container shell |
| `docker-compose build --no-cache` | Rebuild from scratch |
| `docker-compose config` | Validate and view config |

## Status

✅ **Docker Compose is ready and tested**

- Container builds successfully
- Service starts and passes health checks
- All 3 API endpoints accessible
- Structured logging working
- Health checks passing

---

**Last Updated**: 2025-12-28
**Port**: 8001 (maps to internal 8000)
**Container Name**: quantum-api
**Network**: classiq_quantum-network
