# Priority 1: Critical Path Tests

**Scope:** Infrastructure setup and core API functionality  
**Duration:** 25 minutes  
**Pass Rate Required:** 100%  
**Status:** Must pass before proceeding to Priority 2

---

## Part 1: Infrastructure & Setup (10 minutes)

### Test 1.1: Docker Compose Startup

**Objective:** All services start successfully without errors

**Steps:**
```bash
# Clean up any previous runs
docker-compose down -v

# Start all services
docker-compose up -d

# Wait for health checks
sleep 30

# Verify all containers are running
docker-compose ps
```

**Expected Output:**
```
NAME                   COMMAND                  SERVICE              STATUS                 PORTS
quantum-postgres       "docker-entrypoint.s…"   postgres             Up (healthy)           0.0.0.0:5432->5432/tcp
quantum-rabbitmq       "docker-entrypoint.s…"   rabbitmq             Up (healthy)           0.0.0.0:5672->5672/tcp, 0.0.0.0:15672->15672/tcp
quantum-api            "uvicorn app:app --h…"   api                  Up                     0.0.0.0:5000->8000/tcp
quantum-worker-1       "python worker.py"       worker-1             Up                     
quantum-worker-2       "python worker.py"       worker-2             Up                     
quantum-worker-3       "python worker.py"       worker-3             Up                     
```

**Pass Criteria:**
- [ ] All containers show "Up" or "Up (healthy)"
- [ ] No containers in "Restarting" or "Exit" state
- [ ] Port mappings are correct (5000, 5432, 5672)
- [ ] Status shows healthy for postgres and rabbitmq

**Failure Debugging:**
```bash
# If any container is unhealthy, check logs
docker-compose logs quantum-postgres
docker-compose logs quantum-rabbitmq
docker-compose logs quantum-api

# Common issues:
# - Port already in use: lsof -i :5000
# - Image build failed: docker-compose build
# - Volume permission issue: docker-compose down -v && docker-compose up -d
```

---

### Test 1.2: PostgreSQL Database Initialization

**Objective:** Database schema is created and ready

**Steps:**
```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U quantum_user -d quantum_db

# Inside psql:
\dt                    # List tables
\d tasks               # Describe tasks table
SELECT COUNT(*) FROM tasks;  # Verify table is empty
\q                     # Exit
```

**Expected Output:**
```
              List of relations
 Schema |       Name       | Type  | Owner
--------+------------------+-------+--------------
 public | tasks            | table | quantum_user

                    Table "public.tasks"
      Column      |            Type             | Collation | Nullable | Default
------------------+-----------------------------+-----------+----------+---------
 id               | character varying(36)       |           | not null | 
 circuit_qasm3    | text                        |           | not null | 
 status           | character varying(20)       |           | not null | pending
 result           | jsonb                       |           |          | 
 created_at       | timestamp without time zone |           |          | now()
 completed_at     | timestamp without time zone |           |          | 

count
-------
    0

```

**Pass Criteria:**
- [ ] `tasks` table exists
- [ ] Columns: `id`, `circuit_qasm3`, `status`, `result`, `created_at`, `completed_at`
- [ ] `id` is VARCHAR(36) primary key
- [ ] `status` has default value 'pending'
- [ ] `created_at` has default CURRENT_TIMESTAMP
- [ ] Table is empty (count = 0)

**Failure Debugging:**
```bash
# If table doesn't exist, check PostgreSQL logs
docker-compose logs quantum-postgres | tail -50

# Check if migrations ran
docker-compose exec postgres psql -U quantum_user -d quantum_db -c \
  "SELECT * FROM information_schema.tables WHERE table_name='tasks';"
```

---

### Test 1.3: RabbitMQ Queue & Exchange Setup

**Objective:** Message queue infrastructure is ready

**Steps:**

Option A: Via CLI (in container)
```bash
docker-compose exec rabbitmq rabbitmqctl list_exchanges
docker-compose exec rabbitmq rabbitmqctl list_queues
docker-compose exec rabbitmq rabbitmqctl list_bindings
```

Option B: Via Management UI
1. Open http://localhost:15672
2. Username: `quantum_user`, Password: `quantum_pass`
3. Navigate to "Exchanges" tab
4. Verify `quantum_task` exchange exists
5. Navigate to "Queues" tab
6. Verify `task_queue` exists

**Expected Output (CLI):**
```
Listing exchanges ...
	direct
	amq.match
	amq.rabbitmq.trace
	quantum_task	direct	true	false	false	[]

Listing queues ...
	name	messages	consumers
	task_queue	0	0

Listing bindings ...
	source_name	source_kind	destination_name	destination_kind	routing_key	arguments
	quantum_task	exchange	task_queue	queue	tasks
```

**Pass Criteria:**
- [ ] Exchange `quantum_task` exists with type "direct"
- [ ] Queue `task_queue` exists
- [ ] Queue is bound to exchange with routing key "tasks"
- [ ] Queue message count = 0 (empty)
- [ ] No consumers connected (will change during processing)

**Failure Debugging:**
```bash
# If exchange/queue missing, check worker startup logs
docker-compose logs quantum-worker-1 | grep -i "exchange\|queue\|rabbitmq"

# Check RabbitMQ logs
docker-compose logs quantum-rabbitmq | tail -50
```

---

### Test 1.4: API Server Accessibility

**Objective:** FastAPI server is running and responding

**Steps:**
```bash
# Test 1: Basic connectivity
curl -v http://localhost:5000/health

# Test 2: Check Swagger docs
curl http://localhost:5000/docs

# Test 3: Check OpenAPI schema
curl http://localhost:5000/openapi.json
```

**Expected Output:**
```json
{
  "status": "healthy"
}
```

**Pass Criteria:**
- [ ] HTTP 200 response
- [ ] Response contains `"status": "healthy"`
- [ ] Swagger UI accessible at http://localhost:5000/docs
- [ ] OpenAPI schema available at http://localhost:5000/openapi.json

**Failure Debugging:**
```bash
# If connection refused, check API container
docker-compose logs quantum-api | tail -50

# Check if port 5000 is actually open
lsof -i :5000

# Check API environment variables
docker-compose exec quantum-api env | grep -E "DATABASE|RABBITMQ"
```

---

## Part 2: Core API Functionality (15 minutes)

### Test 2.1: POST /tasks - Submit Valid Circuit

**Objective:** API accepts a quantum circuit and returns a task ID

**Steps:**
```bash
# Submit a simple valid circuit
curl -X POST http://localhost:5000/tasks \
  -H "Content-Type: application/json" \
  -d '{"qc": "OPENQASM 3; qubit q; h q; measure q;"}'
```

**Expected Output:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Task submitted successfully."
}
```

**Pass Criteria:**
- [ ] HTTP 200 status code
- [ ] Response contains `task_id` field
- [ ] `task_id` is a valid UUID (format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)
- [ ] Response contains `message` field with success message
- [ ] Response is valid JSON
- [ ] No error in response body

**Verification:**
```bash
# Verify task was created in database
docker-compose exec postgres psql -U quantum_user -d quantum_db \
  -c "SELECT id, status, created_at FROM tasks ORDER BY created_at DESC LIMIT 1;"

# Should show:
#                   id                   | status  |         created_at
# ------------------------------------+----------+----------------------------
#  550e8400-e29b-41d4-a716-446655440000 | pending  | 2025-01-29 10:00:00.000000
```

**Failure Debugging:**
```bash
# If 500 error, check API logs
docker-compose logs quantum-api | tail -50

# If 422 error (validation), check request format
# Make sure JSON is valid and qc field is present

# If task not created in DB, check database connection
docker-compose exec quantum-api env | grep DATABASE_URL
```

---

### Test 2.2: Verify Task Was Published to RabbitMQ

**Objective:** Message appears in queue after submission

**Steps:**
```bash
# Check queue depth immediately after submission
docker-compose exec rabbitmq rabbitmqctl list_queues task_queue

# Or via RabbitMQ Management UI at http://localhost:15672
# Navigate to Queues → task_queue
```

**Expected Output:**
```
Listing queues ...
	name	    messages	consumers
	task_queue	1	        0
```

(1 message pending, 0 consumers since workers may already be processing)

**Pass Criteria:**
- [ ] Queue contains at least 1 message
- [ ] Message count increases with each submission
- [ ] Messages decrease as workers process them

**Failure Debugging:**
```bash
# If message not in queue, check worker logs
docker-compose logs quantum-worker-1 | head -20

# Check if publish was successful in API logs
docker-compose logs quantum-api | grep -i "publish\|rabbitmq"
```

---

### Test 2.3: GET /tasks/<id> - Check Pending Status

**Objective:** Status endpoint returns correct pending status

**Steps:**
```bash
# From Test 2.1, use the returned task_id
TASK_ID="550e8400-e29b-41d4-a716-446655440000"

# Immediately check status (before completion)
curl http://localhost:5000/tasks/$TASK_ID
```

**Expected Output (before completion):**
```json
{
  "status": "pending",
  "message": "Task is still in progress."
}
```

**Pass Criteria:**
- [ ] HTTP 200 status code
- [ ] Response contains `status: "pending"`
- [ ] Response contains informative message
- [ ] Response is valid JSON

**Failure Debugging:**
```bash
# Verify task exists in database
docker-compose exec postgres psql -U quantum_user -d quantum_db \
  -c "SELECT id, status FROM tasks WHERE id='$TASK_ID';"

# If not found, check if POST actually created it
```

---

### Test 2.4: Worker Processes Task and Completes

**Objective:** Workers pick up tasks and execute them successfully

**Steps:**
```bash
# Submit task
TASK_ID=$(curl -s -X POST http://localhost:5000/tasks \
  -H "Content-Type: application/json" \
  -d '{"qc": "OPENQASM 3; qubit q; h q; measure q;"}' | jq -r '.task_id')

echo "Task ID: $TASK_ID"

# Watch worker logs (separate terminal)
docker-compose logs -f quantum-worker-1

# In another terminal, poll for completion (max 10 seconds)
for i in {1..10}; do
  STATUS=$(curl -s http://localhost:5000/tasks/$TASK_ID | jq -r '.status')
  echo "Attempt $i: Status = $STATUS"
  if [ "$STATUS" = "completed" ]; then
    echo "✓ Task completed!"
    break
  fi
  sleep 1
done
```

**Expected Logs (Worker):**
```
INFO:     Application startup complete.
Processing task 550e8400-e29b-41d4-a716-446655440000
Task 550e8400-e29b-41d4-a716-446655440000 completed successfully
```

**Pass Criteria:**
- [ ] Worker logs show "Processing task {id}"
- [ ] Worker logs show "completed successfully"
- [ ] Status changes from "pending" to "completed"
- [ ] Completion happens within 10 seconds
- [ ] No errors in worker logs

**Failure Debugging:**
```bash
# If worker doesn't pick up task, check:
docker-compose logs quantum-worker-1 | grep -i "error\|exception\|connection"

# Verify worker is consuming from queue
docker-compose exec rabbitmq rabbitmqctl list_consumers

# Check if circuit is valid QASM3
```

---

### Test 2.5: GET /tasks/<id> - Check Completed Status with Results

**Objective:** Status endpoint returns results after completion

**Steps:**
```bash
# Use the task_id from Test 2.4
# Wait a few seconds for completion
sleep 3

# Check status
curl http://localhost:5000/tasks/$TASK_ID | jq .
```

**Expected Output:**
```json
{
  "status": "completed",
  "result": {
    "0": 512,
    "1": 512
  }
}
```

**Pass Criteria:**
- [ ] HTTP 200 status code
- [ ] Response contains `status: "completed"`
- [ ] Response contains `result` field with measurement counts
- [ ] Result contains measurement outcomes (e.g., "0" and "1")
- [ ] Counts are integers (≥ 0)
- [ ] Sum of counts ≈ 1024 (number of shots)

**Result Validation:**
```bash
# Verify counts add up to shots (1024)
RESULT=$(curl -s http://localhost:5000/tasks/$TASK_ID | jq '.result')
TOTAL=$(echo "$RESULT" | jq 'add')
echo "Total shots: $TOTAL (expected: 1024)"
```

**Failure Debugging:**
```bash
# If result is empty/null, check database
docker-compose exec postgres psql -U quantum_user -d quantum_db \
  -c "SELECT id, status, result FROM tasks WHERE id='$TASK_ID';"

# If result is there but not returned by API, check API logs
docker-compose logs quantum-api | grep -i "error\|exception"

# If counts seem wrong, check worker execution logs
docker-compose logs quantum-worker-1 | grep -i "shots\|execute\|result"
```

---

### Test 2.6: GET /tasks/<id> - Task Not Found

**Objective:** API returns proper error for nonexistent task

**Steps:**
```bash
# Request a task that doesn't exist
curl http://localhost:5000/tasks/00000000-0000-0000-0000-000000000000
```

**Expected Output:**
```json
{
  "status": "error",
  "message": "Task not found."
}
```

**Pass Criteria:**
- [ ] HTTP 200 or 404 status code
- [ ] Response contains `status: "error"`
- [ ] Response contains informative error message
- [ ] Response is valid JSON

**Failure Debugging:**
```bash
# Check if API is properly querying database
docker-compose logs quantum-api | grep -i "select\|query"

# Verify task truly doesn't exist
docker-compose exec postgres psql -U quantum_user -d quantum_db \
  -c "SELECT COUNT(*) FROM tasks WHERE id='00000000-0000-0000-0000-000000000000';"
```

---

### Test 2.7: End-to-End Flow Summary

**Objective:** Verify complete workflow works

**Steps:**
```bash
echo "=== End-to-End Test ==="

# 1. Submit
echo "1. Submitting task..."
RESPONSE=$(curl -s -X POST http://localhost:5000/tasks \
  -H "Content-Type: application/json" \
  -d '{"qc": "OPENQASM 3; qubit q; h q; measure q;"}')
TASK_ID=$(echo $RESPONSE | jq -r '.task_id')
echo "   Task ID: $TASK_ID"

# 2. Poll
echo "2. Polling for completion..."
for i in {1..20}; do
  RESULT=$(curl -s http://localhost:5000/tasks/$TASK_ID)
  STATUS=$(echo $RESULT | jq -r '.status')
  if [ "$STATUS" = "completed" ]; then
    echo "   ✓ Completed after $i attempts"
    echo "   Result: $(echo $RESULT | jq '.result')"
    break
  fi
  sleep 0.5
done

# 3. Verify database
echo "3. Verifying database state..."
docker-compose exec postgres psql -U quantum_user -d quantum_db \
  -c "SELECT id, status, result IS NOT NULL FROM tasks WHERE id='$TASK_ID';"
```

**Expected Output:**
```
=== End-to-End Test ===
1. Submitting task...
   Task ID: 550e8400-e29b-41d4-a716-446655440000
2. Polling for completion...
   ✓ Completed after 5 attempts
   Result: {
     "0": 512,
     "1": 512
   }
3. Verifying database state...
 550e8400-e29b-41d4-a716-446655440000 | completed | t
```

**Pass Criteria:**
- [ ] All 3 steps complete successfully
- [ ] Task submission returns valid UUID
- [ ] Task completes within 20 seconds
- [ ] Database state is consistent

---

## Summary Table

| Test | Requirement | Status |
|------|-------------|--------|
| 1.1 | Docker Compose startup | [ ] |
| 1.2 | PostgreSQL schema | [ ] |
| 1.3 | RabbitMQ queues | [ ] |
| 1.4 | API server | [ ] |
| 2.1 | POST /tasks | [ ] |
| 2.2 | Message in queue | [ ] |
| 2.3 | GET pending | [ ] |
| 2.4 | Worker processing | [ ] |
| 2.5 | GET completed | [ ] |
| 2.6 | GET not found | [ ] |
| 2.7 | End-to-end | [ ] |

**Overall Priority 1 Status:** [ ] PASS / [ ] FAIL

**If any test fails, STOP and fix before proceeding to Priority 2.**

---

## Next Steps

Once all Priority 1 tests pass:
1. Document results in test results file
2. Proceed to `TESTS_PRIORITY_2.md`
3. Focus on task integrity and reliability

---

**Last Updated:** 2025-01-29  
**Critical Path:** Infrastructure & Core API
