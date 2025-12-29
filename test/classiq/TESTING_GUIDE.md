# Classiq Quantum Circuits API - Complete Testing Guide

## Overview

This guide provides a comprehensive testing strategy for the Classiq Quantum Circuits API exercise. Tests are organized by priority, ensuring critical functionality is validated before advanced scenarios.

**Total Testing Time Estimate:** 90 minutes

## Test Organization

Tests are grouped into 5 priority levels:

- **PRIORITY 1:** Critical Path - Must work for submission
- **PRIORITY 2:** Task Integrity & Reliability - Core business logic
- **PRIORITY 3:** Scalability & Performance - Under load
- **PRIORITY 4:** Production Readiness - Monitoring & observability
- **PRIORITY 5:** Edge Cases - Advanced scenarios

## Quick Reference

| Phase | Tests | Duration | Pass Rate |
|-------|-------|----------|-----------|
| Setup | Infrastructure validation | 10 min | 100% required |
| Core | API functionality | 15 min | 100% required |
| Reliability | Error handling & durability | 20 min | 100% required |
| Scale | Multi-task processing | 15 min | ≥95% |
| Persistence | Data survival | 10 min | 100% required |
| Edge Cases | Boundary conditions | 10 min | ≥90% |

## Pre-Testing Checklist

Before running tests:

- [ ] Docker is installed and running
- [ ] All source code is committed
- [ ] No uncommitted changes that affect runtime
- [ ] Recent `docker-compose build` completed
- [ ] Previous containers cleaned up: `docker-compose down -v`
- [ ] Sufficient disk space for containers (~5GB)
- [ ] Port 5000, 5432, 5672 are available
- [ ] Test scripts have execute permissions

## Testing by Phase

### Phase 1: Setup (10 minutes)

See: `TESTS_PRIORITY_1.md` → "Infrastructure & Setup"

```bash
docker-compose up -d
sleep 30
docker-compose ps
```

**Pass Criteria:**
- All containers show "Up" or "Up (healthy)"
- No container restart loops
- Logs contain no FATAL/CRITICAL errors

### Phase 2: Core Functionality (15 minutes)

See: `TESTS_PRIORITY_1.md` → "Core API Functionality"

```bash
# 1. Health check
curl http://localhost:5000/health

# 2. Submit task
curl -X POST http://localhost:5000/tasks \
  -H "Content-Type: application/json" \
  -d '{"qc": "OPENQASM 3; qubit q; h q; measure q;"}'

# 3. Check status
curl http://localhost:5000/tasks/{task_id}
```

**Pass Criteria:**
- HTTP 200 responses
- Valid JSON responses
- Task completes within 10 seconds
- Result contains measurement counts

### Phase 3: Reliability (20 minutes)

See: `TESTS_PRIORITY_2.md`

**Key Tests:**
- Task durability (worker crash recovery)
- Invalid input rejection
- Error handling
- Message acknowledgment

**Pass Criteria:**
- No lost tasks across all tests
- Proper HTTP status codes
- Database state remains consistent

### Phase 4: Scale (15 minutes)

See: `TESTS_PRIORITY_3.md`

**Key Tests:**
- 10 concurrent task submissions
- Worker load balancing
- Queue performance

**Pass Criteria:**
- All tasks complete successfully
- Load distributed evenly across workers
- No timeouts or dropped messages

### Phase 5: Persistence (10 minutes)

See: `TESTS_PRIORITY_4.md` → "Data Persistence"

```bash
docker-compose down
docker-compose up -d
sleep 30

# Verify old tasks are still retrievable
curl http://localhost:5000/tasks/{old_task_id}
```

**Pass Criteria:**
- Old task data survives restart
- No data loss
- RabbitMQ messages persisted

### Phase 6: Edge Cases (10 minutes)

See: `TESTS_PRIORITY_5.md`

**Key Tests:**
- Invalid JSON input
- Large circuits
- Nonexistent task IDs
- Rapid submissions

**Pass Criteria:**
- Graceful error handling
- No system crashes
- Appropriate error messages

## Test Execution Workflow

```
START
  │
  ├─→ Run Phase 1 (Setup)
  │   └─→ FAIL? Stop. Fix infrastructure.
  │   └─→ PASS? Continue.
  │
  ├─→ Run Phase 2 (Core Functionality)
  │   └─→ FAIL? Stop. Fix API/Workers.
  │   └─→ PASS? Continue.
  │
  ├─→ Run Phase 3 (Reliability)
  │   └─→ FAIL? Stop. Fix error handling.
  │   └─→ PASS? Continue.
  │
  ├─→ Run Phase 4 (Scale)
  │   └─→ FAIL? Analyze logs. May be acceptable for MVP.
  │   └─→ PASS? Continue.
  │
  ├─→ Run Phase 5 (Persistence)
  │   └─→ FAIL? Stop. Fix volume mounts.
  │   └─→ PASS? Continue.
  │
  └─→ Run Phase 6 (Edge Cases)
      └─→ REVIEW results
      └─→ Ready for submission
```

## Automated Test Script

See: `TEST_SCRIPT.sh` for automated execution of all phases.

```bash
chmod +x TEST_SCRIPT.sh
./TEST_SCRIPT.sh
```

This runs all tests sequentially and generates a summary report.

## Manual Testing Approach

If running tests manually:

1. Open 3 terminals:
   - Terminal 1: `docker-compose logs -f` (watch logs)
   - Terminal 2: `docker-compose exec rabbitmq rabbitmqctl list_queues` (monitor RabbitMQ)
   - Terminal 3: Run test commands

2. After each test, verify:
   - Expected HTTP response
   - Expected log output
   - Expected database state
   - Expected queue depth change

## Debugging Failed Tests

### Issue: Container won't start

```bash
docker-compose logs {service_name}
# Look for: connection refused, port already in use, image not found

# Fix:
docker-compose down -v
docker-compose build
docker-compose up -d
```

### Issue: Task submission succeeds but worker doesn't process

```bash
# Check RabbitMQ connection
docker-compose logs quantum-worker-1 | grep -i "rabbitmq\|connection\|error"

# Check message in queue
docker-compose exec rabbitmq rabbitmqctl list_queues

# Check worker logs
docker-compose logs quantum-worker-1 | tail -50
```

### Issue: Database connection errors

```bash
# Verify PostgreSQL is healthy
docker-compose ps postgres
docker-compose exec postgres psql -U quantum_user -d quantum_db -c "SELECT 1;"

# Check database URL in API/workers
docker-compose exec quantum-api env | grep DATABASE_URL
```

### Issue: Task doesn't complete

```bash
# Check task status in DB
docker-compose exec postgres psql -U quantum_user -d quantum_db -c \
  "SELECT id, status, created_at FROM tasks ORDER BY created_at DESC LIMIT 5;"

# Check worker logs for errors
docker-compose logs quantum-worker-1 quantum-worker-2 quantum-worker-3 | grep -i "error\|exception"

# Check circuit is valid QASM3
# Try a simple circuit: "OPENQASM 3; qubit q; h q; measure q;"
```

## Test Metrics Dashboard

After running all tests, compile results in `TEST_RESULTS.md`:

```markdown
# Test Results Summary

**Date:** 2025-01-XX  
**Duration:** 90 minutes  
**Total Tests:** 28  
**Passed:** 28  
**Failed:** 0  
**Pass Rate:** 100%

## By Priority

| Priority | Tests | Passed | Failed | Status |
|----------|-------|--------|--------|--------|
| P1 | 7 | 7 | 0 | ✅ PASS |
| P2 | 7 | 7 | 0 | ✅ PASS |
| P3 | 6 | 6 | 0 | ✅ PASS |
| P4 | 5 | 5 | 0 | ✅ PASS |
| P5 | 3 | 3 | 0 | ✅ PASS |

## Performance Metrics

- Startup time: 25s (target: < 30s) ✅
- Task completion latency: 2.3s (target: < 5s) ✅
- Worker pickup latency: 0.8s (target: < 1s) ✅
- Zero task loss: 100% (target: 100%) ✅
```

## Key Success Criteria

**Mandatory (100% Pass Rate):**
- All PRIORITY 1 tests pass
- All PRIORITY 2 tests pass
- No data loss across any test
- All containers stable (no crashes/restarts)

**Strongly Recommended (≥95% Pass Rate):**
- PRIORITY 3 tests (scalability)
- PRIORITY 4 tests (observability)

**Nice to Have (≥90% Pass Rate):**
- PRIORITY 5 tests (edge cases)

## Environment Variables for Testing

```bash
# Enable verbose logging
export RUST_LOG=debug
export LOG_LEVEL=debug

# Timeout tests faster
export TASK_TIMEOUT=5

# Small dataset for quick testing
export TEST_MODE=fast
```

## Useful Commands

```bash
# View all logs
docker-compose logs -f

# View specific service
docker-compose logs -f quantum-api
docker-compose logs -f quantum-worker-1
docker-compose logs -f rabbitmq

# Get recent logs only
docker-compose logs --tail=100

# Monitor containers in real-time
watch -n 1 'docker-compose ps'

# Access PostgreSQL
docker-compose exec postgres psql -U quantum_user -d quantum_db

# Access RabbitMQ management
# Open browser: http://localhost:15672
# User: quantum_user / Pass: quantum_pass

# API Swagger docs
# Open browser: http://localhost:5000/docs
```

## Common Test Patterns

### Pattern 1: Submit and Poll

```bash
# Submit
RESPONSE=$(curl -s -X POST http://localhost:5000/tasks \
  -H "Content-Type: application/json" \
  -d '{"qc": "OPENQASM 3; qubit q; h q; measure q;"}')
TASK_ID=$(echo $RESPONSE | jq -r '.task_id')

# Poll until complete
for i in {1..30}; do
  STATUS=$(curl -s http://localhost:5000/tasks/$TASK_ID | jq -r '.status')
  if [ "$STATUS" = "completed" ]; then
    curl -s http://localhost:5000/tasks/$TASK_ID | jq .
    break
  fi
  sleep 1
done
```

### Pattern 2: Batch Submit and Verify All Complete

```bash
# Submit 10 tasks
for i in {1..10}; do
  curl -s -X POST http://localhost:5000/tasks \
    -H "Content-Type: application/json" \
    -d '{"qc": "OPENQASM 3; qubit q; h q; measure q;"}' &
done
wait

# Count completed
docker-compose exec postgres psql -U quantum_user -d quantum_db \
  -c "SELECT status, COUNT(*) FROM tasks GROUP BY status;"
```

### Pattern 3: Verify Load Distribution

```bash
# Check which worker processed which task
docker-compose logs quantum-worker-1 quantum-worker-2 quantum-worker-3 | \
  grep "Processing task" | awk '{print $0}' | sort

# Count tasks per worker
docker-compose logs quantum-worker-1 | grep "completed" | wc -l
docker-compose logs quantum-worker-2 | grep "completed" | wc -l
docker-compose logs quantum-worker-3 | grep "completed" | wc -l
```

## Submission Readiness Checklist

Before submitting, ensure:

- [ ] All PRIORITY 1 tests pass (100%)
- [ ] All PRIORITY 2 tests pass (100%)
- [ ] At least 95% of PRIORITY 3 tests pass
- [ ] At least 90% of PRIORITY 4 tests pass
- [ ] At least 80% of PRIORITY 5 tests pass (optional)
- [ ] `docker-compose up -d` works cleanly
- [ ] No hardcoded credentials in code
- [ ] All configuration in environment variables
- [ ] README.md documents architecture decisions
- [ ] Git repository has clean history
- [ ] No large binary files committed
- [ ] `.gitignore` excludes Docker volumes and build artifacts

## Next Steps

1. Read `TESTS_PRIORITY_1.md` for critical path tests
2. Read corresponding priority file as you progress
3. Use `TEST_SCRIPT.sh` for automated testing
4. Document results in `TEST_RESULTS.md`
5. Fix any failures before submission

---

**Last Updated:** 2025-01-29  
**Maintainer:** Testing Guide for Classiq Quantum Circuits API
