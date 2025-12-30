# Quickstart: Standalone API Server

**Feature:** Standalone API Server with Docker Setup
**Audience:** Developers setting up local development environment
**Time to Complete:** 5-10 minutes

---

## Prerequisites

- **Docker**: Version 20.10 or later ([Install Docker](https://docs.docker.com/get-docker/))
- **curl** or **httpie**: For testing API endpoints
- **Text Editor**: For viewing response bodies (optional)

**Verify Prerequisites:**
```bash
docker --version   # Should show 20.10+
curl --version     # Should show any recent version
```

---

## Step 1: Build the Container Image

From the repository root:

```bash
cd api
docker build -t quantum-api:latest .
```

**Expected Output:**
```
[+] Building 45.2s (12/12) FINISHED
 => [internal] load build definition from Dockerfile
 => => transferring dockerfile: 523B
 ...
 => exporting to image
 => => naming to docker.io/library/quantum-api:latest
```

**Troubleshooting:**
- If build fails with "Dockerfile not found": Ensure you're in the `api/` directory
- If build is slow: Docker is downloading base image (first time only)

---

## Step 2: Run the Container

Start the API server on port 8000:

```bash
docker run -d \
  --name quantum-api \
  -p 8000:8000 \
  -e LOG_LEVEL=INFO \
  -e ENVIRONMENT=development \
  quantum-api:latest
```

**Verify Container is Running:**
```bash
docker ps | grep quantum-api
```

**Expected Output:**
```
CONTAINER ID   IMAGE                  STATUS         PORTS
a1b2c3d4e5f6   quantum-api:latest     Up 5 seconds   0.0.0.0:8000->8000/tcp
```

**View Logs:**
```bash
docker logs -f quantum-api
```

**Expected Logs (structured JSON):**
```json
{"timestamp": "2025-12-28T12:00:00Z", "level": "INFO", "message": "Server started", "component": "api-server", "environment": "development"}
```

---

## Step 3: Test the Health Check

Verify the API is responding:

```bash
curl http://localhost:8000/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-12-28T12:00:00Z"
}
```

**If this works, your API server is ready!** ✅

---

## Step 4: Submit a Test Task

Submit a simple quantum circuit:

```bash
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"circuit": "OPENQASM 3; qubit q; h q; measure q;"}'
```

**Expected Response:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Task submitted successfully.",
  "correlation_id": "abc123-def456-789012"
}
```

**Save the task_id** for the next step!

---

## Step 5: Check Task Status

Query the status using the task_id from Step 4:

```bash
curl http://localhost:8000/tasks/550e8400-e29b-41d4-a716-446655440000
```

**Expected Response (Stub Behavior):**
```json
{
  "status": "pending",
  "message": "Task is still in progress.",
  "correlation_id": "xyz789-uvw456-123789"
}
```

**Note:** In the stub implementation, all tasks return "pending" status. Actual task execution will be added in a future feature.

---

## Complete Test Script

Run all tests at once:

```bash
#!/bin/bash

echo "=== Health Check ==="
curl -s http://localhost:8000/health | jq

echo -e "\n=== Submit Task ==="
RESPONSE=$(curl -s -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"circuit": "OPENQASM 3; qubit q; h q; measure q;"}')

echo $RESPONSE | jq
TASK_ID=$(echo $RESPONSE | jq -r '.task_id')

echo -e "\n=== Get Task Status ==="
curl -s http://localhost:8000/tasks/$TASK_ID | jq
```

**Save as** `test-api.sh`, make executable, and run:
```bash
chmod +x test-api.sh
./test-api.sh
```

---

## API Endpoints Summary

| Method | Endpoint | Purpose | Status |
|--------|----------|---------|--------|
| GET | `/health` | Health check | ✅ Working |
| POST | `/tasks` | Submit circuit task | ✅ Stubbed |
| GET | `/tasks/{id}` | Get task status | ✅ Stubbed |

---

## Common Operations

### View Logs (Real-time)

```bash
docker logs -f quantum-api
```

**Log Format:** Structured JSON with correlation IDs

**Example Log Entry:**
```json
{
  "timestamp": "2025-12-28T12:00:00Z",
  "level": "INFO",
  "message": "POST /tasks 200 52ms",
  "correlation_id": "abc123-def456",
  "method": "POST",
  "path": "/tasks",
  "status_code": 200,
  "duration_ms": 52
}
```

### Stop the Server

```bash
docker stop quantum-api
```

### Restart the Server

```bash
docker start quantum-api
```

### Remove the Container

```bash
docker rm -f quantum-api
```

### Rebuild After Code Changes

```bash
cd api
docker build -t quantum-api:latest .
docker rm -f quantum-api
docker run -d --name quantum-api -p 8000:8000 quantum-api:latest
```

---

## Environment Variables

Configure the server with environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | 8000 | HTTP server port |
| `LOG_LEVEL` | INFO | Logging verbosity (DEBUG, INFO, WARN, ERROR) |
| `ENVIRONMENT` | development | Environment name (development, staging, production) |
| `CORS_ORIGINS` | * | Allowed CORS origins (comma-separated) |

**Example with Custom Config:**
```bash
docker run -d \
  --name quantum-api \
  -p 9000:9000 \
  -e PORT=9000 \
  -e LOG_LEVEL=DEBUG \
  -e ENVIRONMENT=staging \
  -e CORS_ORIGINS="http://localhost:3000,https://app.example.com" \
  quantum-api:latest
```

---

## Testing Error Scenarios

### Missing Required Field

```bash
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Expected Response (400):**
```json
{
  "error": "Validation failed",
  "details": {
    "circuit": "Field required"
  },
  "correlation_id": "abc123-def456"
}
```

### Invalid Task ID Format

```bash
curl http://localhost:8000/tasks/not-a-valid-uuid
```

**Expected Response (400):**
```json
{
  "error": "Invalid task ID format. Expected UUID v4.",
  "correlation_id": "xyz789-uvw456"
}
```

### Invalid JSON

```bash
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{invalid json'
```

**Expected Response (400):**
```json
{
  "error": "Invalid JSON",
  "correlation_id": "abc123-def456"
}
```

---

## Accessing OpenAPI Documentation

Once the server is running, access interactive API docs:

**Swagger UI:**
```
http://localhost:8000/docs
```

**ReDoc:**
```
http://localhost:8000/redoc
```

**OpenAPI JSON Schema:**
```
http://localhost:8000/openapi.json
```

---

## Integration with Frontend

### JavaScript/TypeScript Example

```javascript
const API_BASE_URL = 'http://localhost:8000';

async function submitTask(circuit) {
  const response = await fetch(`${API_BASE_URL}/tasks`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Correlation-ID': crypto.randomUUID(), // Optional
    },
    body: JSON.stringify({ circuit }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error);
  }

  return await response.json();
}

async function getTaskStatus(taskId) {
  const response = await fetch(`${API_BASE_URL}/tasks/${taskId}`);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error);
  }

  return await response.json();
}

// Usage
try {
  const task = await submitTask('OPENQASM 3; qubit q; h q; measure q;');
  console.log('Task ID:', task.task_id);

  const status = await getTaskStatus(task.task_id);
  console.log('Status:', status.status);
} catch (error) {
  console.error('API Error:', error.message);
}
```

### Python Example

```python
import requests
import uuid

API_BASE_URL = 'http://localhost:8000'

def submit_task(circuit: str) -> dict:
    response = requests.post(
        f'{API_BASE_URL}/tasks',
        json={'circuit': circuit},
        headers={'X-Correlation-ID': str(uuid.uuid4())}
    )
    response.raise_for_status()
    return response.json()

def get_task_status(task_id: str) -> dict:
    response = requests.get(f'{API_BASE_URL}/tasks/{task_id}')
    response.raise_for_status()
    return response.json()

# Usage
try:
    task = submit_task('OPENQASM 3; qubit q; h q; measure q;')
    print(f"Task ID: {task['task_id']}")

    status = get_task_status(task['task_id'])
    print(f"Status: {status['status']}")
except requests.HTTPError as e:
    print(f"API Error: {e}")
```

---

## Performance Testing

### Load Test with Apache Bench

```bash
# Install Apache Bench (if not already installed)
# macOS: brew install httpd
# Ubuntu: apt-get install apache2-utils

# Test health endpoint (100 requests, 10 concurrent)
ab -n 100 -c 10 http://localhost:8000/health

# Test task submission (requires body file)
echo '{"circuit":"OPENQASM 3; qubit q; h q; measure q;"}' > task.json
ab -n 100 -c 10 -p task.json -T application/json http://localhost:8000/tasks
```

**Expected Results:**
- Health endpoint: < 50ms average response time
- Task submission: < 500ms average response time
- 100% success rate (no failed requests)

---

## Troubleshooting

### Port Already in Use

**Error:** `bind: address already in use`

**Solution:** Use a different port:
```bash
docker run -d --name quantum-api -p 9000:8000 quantum-api:latest
curl http://localhost:9000/health
```

### Container Won't Start

**Check logs:**
```bash
docker logs quantum-api
```

**Common issues:**
- Missing environment variables
- Port binding failure
- Application crash on startup

### Health Check Fails

**Verify container is running:**
```bash
docker ps | grep quantum-api
```

**Check server logs:**
```bash
docker logs quantum-api | tail -20
```

**Test network connectivity:**
```bash
docker exec quantum-api curl http://localhost:8000/health
```

---

## Next Steps

1. **Explore API Docs:** Visit http://localhost:8000/docs for interactive testing
2. **Integrate with Client:** Use the JavaScript/Python examples above
3. **Run Load Tests:** Verify performance under concurrent load
4. **Add Features:** Database persistence, worker integration (future phases)

---

## Clean Up

When finished testing:

```bash
# Stop and remove container
docker stop quantum-api
docker rm quantum-api

# Remove image (optional)
docker rmi quantum-api:latest
```

---

## Additional Resources

- **OpenAPI Specification:** See `contracts/openapi.yaml`
- **Data Model:** See `data-model.md`
- **Implementation Plan:** See `plan.md`
- **FastAPI Documentation:** https://fastapi.tiangolo.com/

---

**Questions or Issues?**
Check logs first: `docker logs quantum-api`
Review error responses for correlation IDs to trace requests in logs
