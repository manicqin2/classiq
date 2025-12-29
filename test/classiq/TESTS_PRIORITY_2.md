# Priority 2: Task Integrity & Reliability Tests

**Scope:** Error handling, message acknowledgment, task durability  
**Duration:** 20 minutes  
**Pass Rate Required:** 100%  
**Prerequisite:** All Priority 1 tests must pass  
**Status:** Guards against data loss and ensures production-grade reliability

---

## Part 1: RabbitMQ Message Behavior (5 minutes)

### Test 3.1: Messages Published to Queue on Task Submission

**Objective:** Verify message actually goes into RabbitMQ queue

**Steps:**
```bash
# Clear queue and reset
docker-compose exec rabbitmq rabbitmqctl purge_queue task_queue

# Check queue is empty
docker-compose exec rabbitmq rabbitmqctl list_queues task_queue

# Submit a task
TASK_ID=$(curl -s -X POST http://localhost:5000/tasks \
  -H "Content-Type: application/json" \
  -d '{"qc": "OPENQASM 3; qubit q; h q; measure q;"}' | jq -r '.task_id')

echo "Submitted: $TASK_ID"

# Immediately check queue (before worker picks up)
sleep 0.1
docker-compose exec rabbitmq rabbitmqctl list_queues task_queue
```

**Expected Output:**
```
Listing queues ...
	name	    messages	consumers
	task_queue	1	        3
```

(1 message queued, 3 consumers connected = 3 workers)

**Pass Criteria:**
- [ ] Queue depth is > 0 immediately after submission
- [ ] Consumer count matches number of workers (3)
- [ ] Message arrives before worker processes

**Failure Debugging:**
```bash
# If no message in queue, check API logs
docker-compose logs quantum-api | grep -i "publish\|error"

# If consumers = 0, workers not connected
docker-compose logs quantum-worker-1 quantum-worker-2 quantum-worker-3 | grep -i "connected\|error"
```

---

### Test 3.2: Worker Acknowledgment Removes Message from Queue

**Objective:** After completion, message is removed from queue via ACK

**Steps:**
```bash
# Monitor queue while task processes
# Terminal 1: Watch queue
docker-compose exec rabbitmq sh -c \
  'while true; do rabbitmqctl list_queues task_queue; sleep 1; done'

# Terminal 2: Submit task
TASK_ID=$(curl -s -X POST http://localhost:5000/tasks \
  -H "Content-Type: application/json" \
  -d '{"qc": "OPENQASM 3; qubit q; h q; measure q;"}' | jq -r '.task_id')

# Terminal 3: Poll status
for i in {1..30}; do
  STATUS=$(curl -s http://localhost:5000/tasks/$TASK_ID | jq -r '.status')
  echo "[$i] Status: $STATUS"
  if [ "$STATUS" = "completed" ]; then
    break
  fi
  sleep 0.5
done
```

**Expected Behavior:**
- Queue depth goes from 0 → 1 (submission)
- Queue depth goes from 1 → 0 (worker ACKs after completion)
- Task status goes from "pending" → "completed"

**Pass Criteria:**
- [ ] Message removed from queue after completion
- [ ] Queue becomes empty once all tasks processed
- [ ] No messages stuck in queue

**Failure Debugging:**
```bash
# If message stays in queue, check worker ACK logic
docker-compose logs quantum-worker-1 | grep -i "ack\|nack"

# Manually check for unacked messages
docker-compose exec rabbitmq rabbitmqctl list_consumers
```

---

## Part 2: Task Durability (5 minutes)

### Test 3.3: Task Survives Worker Crash

**Objective:** If worker crashes mid-processing, task is redelivered and eventually completes

**Steps:**

```bash
# Terminal 1: Watch worker logs
docker-compose logs -f quantum-worker-1

# Terminal 2: Submit a task (you'll kill the worker during processing)
TASK_ID=$(curl -s -X POST http://localhost:5000/tasks \
  -H "Content-Type: application/json" \
  -d '{"qc": "OPENQASM 3; qubit q; h q; measure q;"}' | jq -r '.task_id')

echo "Task: $TASK_ID"

# Wait ~2 seconds for worker to pick up
sleep 2

# Terminal 3: Kill the worker mid-processing
docker kill quantum-worker-1

# Watch what happens:
# - Worker stops
# - Message reappears in queue
# - Another worker (2 or 3) picks it up
# - Task eventually completes

# Restart the killed worker
docker-compose start quantum-worker-1

# Poll until completion
for i in {1..30}; do
  STATUS=$(curl -s http://localhost:5000/tasks/$TASK_ID | jq -r '.status')
  echo "[$i] Status: $STATUS"
  if [ "$STATUS" = "completed" ]; then
    echo "✓ Task completed after worker recovery"
    break
  fi
  sleep 1
done
```

**Expected Logs:**
```
# Worker-1 picks up task:
Processing task 550e8400-...

# (You kill worker-1 here)

# Worker-2 or 3 picks it up:
Processing task 550e8400-...
Task 550e8400-... completed successfully
```

**Pass Criteria:**
- [ ] Task does NOT remain stuck in "pending" state
- [ ] Task eventually completes after worker restart
- [ ] Different worker processes the task
- [ ] No data loss (task still in database)

**Verification:**
```bash
# Verify task completed
curl http://localhost:5000/tasks/$TASK_ID | jq .

# Verify it's in database with results
docker-compose exec postgres psql -U quantum_user -d quantum_db \
  -c "SELECT id, status, result IS NOT NULL FROM tasks WHERE id='$TASK_ID';"
```

**Failure Debugging:**
```bash
# If task stays pending, check:
# 1. Is message actually redelivered?
docker-compose exec rabbitmq rabbitmqctl list_queues

# 2. Did another worker connect?
docker-compose logs quantum-worker-2 quantum-worker-3 | grep -i "processing"

# 3. Is RabbitMQ properly configured for durability?
docker-compose logs quantum-rabbitmq | grep -i "durable\|persistent"
```

---

## Part 3: Error Handling (5 minutes)

### Test 3.4: Invalid Input Rejection

**Objective:** API rejects malformed input gracefully

**Steps:**

#### Test 3.4a: Missing Required Field
```bash
# Submit without "qc" field
curl -X POST http://localhost:5000/tasks \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Expected Output:**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "qc"],
      "msg": "Field required",
      "input": {}
    }
  ]
}
```

**HTTP Status:** 422 (Unprocessable Entity)

**Pass Criteria:**
- [ ] HTTP 422 status code
- [ ] Error message indicates "qc" field is missing
- [ ] Response is valid JSON with details

#### Test 3.4b: Empty String Circuit
```bash
curl -X POST http://localhost:5000/tasks \
  -H "Content-Type: application/json" \
  -d '{"qc": ""}'
```

**Expected Behavior:**
- [ ] Either: HTTP 422 (validation error) if field is required
- [ ] Or: HTTP 200 with task submission, but worker fails gracefully

**Expected Worker Behavior:**
```bash
# Check worker logs for graceful error handling
docker-compose logs quantum-worker-1 | grep -i "error\|empty"
```

**Expected Database:**
```bash
# Task should be marked as 'failed' in database
docker-compose exec postgres psql -U quantum_user -d quantum_db \
  -c "SELECT id, status FROM tasks ORDER BY created_at DESC LIMIT 1;"
```

Should show `status = 'failed'`

#### Test 3.4c: Malformed JSON
```bash
curl -X POST http://localhost:5000/tasks \
  -H "Content-Type: application/json" \
  -d '{invalid json}'
```

**Expected Output:**
```json
{
  "detail": "Invalid JSON"
}
```

**HTTP Status:** 400 (Bad Request)

**Pass Criteria:**
- [ ] HTTP 400 status code
- [ ] Clear error message
- [ ] No task created in database

#### Test 3.4d: Invalid QASM3 Circuit
```bash
curl -X POST http://localhost:5000/tasks \
  -H "Content-Type: application/json" \
  -d '{"qc": "not a valid circuit"}'
```

**Expected Behavior:**
- [ ] HTTP 200 (submission succeeds)
- [ ] Task created with `status = 'pending'`
- [ ] Worker picks up and fails gracefully
- [ ] Task marked as `status = 'failed'` in database

**Expected Logs:**
```bash
docker-compose logs quantum-worker-1 | grep -i "error\|invalid"
```

Should contain error about invalid circuit

**Database State:**
```bash
docker-compose exec postgres psql -U quantum_user -d quantum_db \
  -c "SELECT id, status FROM tasks ORDER BY created_at DESC LIMIT 1;"
```

Should show `status = 'failed'` or 'error'

---

### Test 3.5: Task Not Found Error

**Objective:** GET /tasks with nonexistent ID returns proper error

**Steps:**
```bash
# Request nonexistent task
curl http://localhost:5000/tasks/nonexistent-id
```

**Expected Output:**
```json
{
  "status": "error",
  "message": "Task not found."
}
```

**Pass Criteria:**
- [ ] HTTP 200 or 404 status code (depending on API design)
- [ ] Response contains error status
- [ ] Clear error message
- [ ] No database errors in logs

**Test with Invalid UUID Format:**
```bash
curl http://localhost:5000/tasks/not-a-uuid
```

**Expected Behavior:**
- [ ] Either: HTTP 400 (bad request) if UUID validation happens
- [ ] Or: HTTP 200 with "task not found" message

---

## Part 4: Database Consistency (3 minutes)

### Test 3.6: Task Status Consistency

**Objective:** Database state remains consistent throughout task lifecycle

**Steps:**
```bash
# Submit task and capture ID
TASK_ID=$(curl -s -X POST http://localhost:5000/tasks \
  -H "Content-Type: application/json" \
  -d '{"qc": "OPENQASM 3; qubit q; h q; measure q;"}' | jq -r '.task_id')

# Check status progression
echo "=== Task Status Progression ==="

# T=0: Just submitted
sleep 0.1
echo "T=0 (just submitted):"
docker-compose exec postgres psql -U quantum_user -d quantum_db -c \
  "SELECT id, status, result IS NOT NULL as has_result, completed_at FROM tasks WHERE id='$TASK_ID';"

# T=3: Processing
sleep 3
echo "T=3 (processing):"
docker-compose exec postgres psql -U quantum_user -d quantum_db -c \
  "SELECT id, status, result IS NOT NULL as has_result, completed_at FROM tasks WHERE id='$TASK_ID';"

# T=8: Should be complete
sleep 5
echo "T=8 (should be complete):"
docker-compose exec postgres psql -U quantum_user -d quantum_db -c \
  "SELECT id, status, result IS NOT NULL as has_result, completed_at FROM tasks WHERE id='$TASK_ID';"
```

**Expected Output:**
```
=== Task Status Progression ===
T=0 (just submitted):
                   id                   | status  | has_result | completed_at
 ------------------------------------+----------+------------+-----------
  550e8400-e29b-41d4-a716-446655440000 | pending  | f          | 
 
T=3 (processing):
                   id                   | status  | has_result | completed_at
 ------------------------------------+----------+------------+-----------
  550e8400-e29b-41d4-a716-446655440000 | pending  | f          | 
 
T=8 (should be complete):
                   id                   | status  | has_result | completed_at
 ------------------------------------+----------+------------+-----------
  550e8400-e29b-41d4-a716-446655440000 | completed | t        | 2025-01-29 10:05:30
```

**Pass Criteria:**
- [ ] Status progresses: pending → completed
- [ ] `completed_at` is NULL until completion
- [ ] `completed_at` is set when status becomes "completed"
- [ ] `result` is NULL until completion, then contains JSON
- [ ] No anomalies (e.g., result set but status pending)

**Failure Debugging:**
```bash
# If any inconsistency found, check worker logs
docker-compose logs quantum-worker-1 | grep -i "update\|database\|error"

# Check for transaction issues
docker-compose logs quantum-api | grep -i "transaction\|error"
```

---

### Test 3.7: No Lost Tasks Across Multiple Submissions

**Objective:** All submitted tasks eventually appear in database as completed

**Steps:**
```bash
# Count tasks before
BEFORE=$(docker-compose exec postgres psql -U quantum_user -d quantum_db -t \
  -c "SELECT COUNT(*) FROM tasks;")
echo "Tasks before: $BEFORE"

# Submit 5 tasks rapidly
echo "Submitting 5 tasks..."
for i in {1..5}; do
  curl -s -X POST http://localhost:5000/tasks \
    -H "Content-Type: application/json" \
    -d '{"qc": "OPENQASM 3; qubit q; h q; measure q;"}' &
done
wait

# Count tasks after submission
SUBMITTED=$(docker-compose exec postgres psql -U quantum_user -d quantum_db -t \
  -c "SELECT COUNT(*) FROM tasks;")
echo "Tasks after submission: $SUBMITTED (should be $BEFORE + 5)"

# Wait for all to complete
echo "Waiting for completion..."
sleep 15

# Count completed tasks
COMPLETED=$(docker-compose exec postgres psql -U quantum_user -d quantum_db -t \
  -c "SELECT COUNT(*) FROM tasks WHERE status='completed';")
echo "Completed tasks: $COMPLETED"

# Show any failed tasks
FAILED=$(docker-compose exec postgres psql -U quantum_user -d quantum_db -t \
  -c "SELECT COUNT(*) FROM tasks WHERE status='failed';")
echo "Failed tasks: $FAILED"

# Verify no pending/orphaned tasks remain
PENDING=$(docker-compose exec postgres psql -U quantum_user -d quantum_db -t \
  -c "SELECT COUNT(*) FROM tasks WHERE status='pending';")
echo "Pending tasks (should be 0): $PENDING"
```

**Expected Output:**
```
Tasks before: 10
Submitting 5 tasks...
Tasks after submission: 15 (should be 10 + 5)
Waiting for completion...
Completed tasks: 15
Failed tasks: 0
Pending tasks (should be 0): 0
```

**Pass Criteria:**
- [ ] All submitted tasks appear in database
- [ ] All tasks eventually reach terminal state (completed or failed)
- [ ] No tasks remain in "pending" state after sufficient time
- [ ] Zero data loss: submitted count = completed count + failed count

**Failure Debugging:**
```bash
# If pending tasks remain, check:
docker-compose logs quantum-worker-1 quantum-worker-2 quantum-worker-3 | tail -100

# Check queue depth
docker-compose exec rabbitmq rabbitmqctl list_queues task_queue

# Check for stuck workers
docker-compose ps
```

---

## Summary Table

| Test | Requirement | Status |
|------|-------------|--------|
| 3.1 | Message published | [ ] |
| 3.2 | ACK removes message | [ ] |
| 3.3 | Worker crash recovery | [ ] |
| 3.4a | Missing field rejection | [ ] |
| 3.4b | Empty string handling | [ ] |
| 3.4c | Invalid JSON rejection | [ ] |
| 3.4d | Invalid circuit handling | [ ] |
| 3.5 | Task not found | [ ] |
| 3.6 | Status consistency | [ ] |
| 3.7 | No lost tasks | [ ] |

**Overall Priority 2 Status:** [ ] PASS / [ ] FAIL

**If any test fails, debug and fix before proceeding to Priority 3.**

---

## Key Insights

**Message Durability:** RabbitMQ's ACK mechanism ensures:
- Messages persist on disk until acknowledged
- Unacknowledged messages are redelivered
- Worker crashes don't cause message loss

**Error Handling Strategy:**
- API validates input (JSON, required fields)
- Worker handles circuit execution errors gracefully
- Failed tasks marked in database, not lost

**Database Consistency:**
- Status transitions are atomic
- Timestamps track lifecycle
- Results only set on successful completion

---

## Next Steps

Once all Priority 2 tests pass:
1. Document results
2. Proceed to `TESTS_PRIORITY_3.md` for scalability tests
3. Verify system handles load

---

**Last Updated:** 2025-01-29  
**Focus:** Reliability & Durability
