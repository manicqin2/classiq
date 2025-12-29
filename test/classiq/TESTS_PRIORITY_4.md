# Priority 4: Production Readiness Tests

**Scope:** Monitoring, observability, data persistence  
**Duration:** 10 minutes  
**Pass Rate Required:** ≥90%

## Logging & Observability Tests

### Test 5.1: API Logs All Requests
API logs show method, path, status code, and timestamp for every POST/GET request.

### Test 5.2: Worker Logs Task Processing
Worker logs contain task ID, action (processing/completed/failed), and timestamp for each task.

### Test 5.3: Error Logging with Context
Application errors are logged with full stack trace, context, and component name.

### Test 5.4: RabbitMQ Management UI is Accessible
RabbitMQ management interface at localhost:15672 shows queue depth and consumer count.

### Test 5.5: API Swagger Docs Auto-Generated
FastAPI auto-generates OpenAPI docs at /docs with all endpoints documented.

## Data Persistence Tests

### Test 5.6: Database Persistence Across Restart
Stop all containers and restart; old task data is still queryable.

### Test 5.7: RabbitMQ Message Persistence
Submit task, restart RabbitMQ container, message is still in queue and workers process it.

### Test 5.8: Volume Mounts Work Correctly
PostgreSQL volume persists data; verify files exist in `/var/lib/postgresql/data`.

## Container Health Tests

### Test 5.9: Health Checks Report Status
`docker-compose ps` shows postgres and rabbitmq as "healthy" after startup.

### Test 5.10: Graceful Shutdown
`docker-compose down` stops all containers cleanly without errors or stuck processes.

### Test 5.11: Restart Resilience
`docker-compose down && docker-compose up -d` restarts system with all services functional.

## Monitoring & Metrics Tests

### Test 5.12: Queue Metrics Visible
RabbitMQ UI shows message count, consumer count, and message rates.

### Test 5.13: Consumer Status Visible
RabbitMQ UI shows all 3 workers connected as consumers on task_queue.

### Test 5.14: Database Connection Status
PostgreSQL logs show successful connections from API and workers.

## Docker Compose Tests

### Test 5.15: Single Command Startup
`docker-compose up -d` brings entire system up with no manual intervention.

### Test 5.16: Dependency Order is Correct
Services start in proper order; postgres/rabbitmq healthy before API/workers.

### Test 5.17: Environment Variables Passed Correctly
Services receive DATABASE_URL, RABBITMQ_URL, and WORKER_ID as expected.

---

**Pass/Fail:** [ ] PASS / [ ] FAIL  
**Notes:** Focus on observability and crash recovery; production systems must be debuggable.
