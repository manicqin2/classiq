# Priority 3: Scalability & Performance Tests

**Scope:** Load handling, worker distribution, performance metrics  
**Duration:** 15 minutes  
**Pass Rate Required:** ≥95%

## Multi-Worker Tests

### Test 4.1: Load Balancing Across Workers
Verify that 10 concurrent tasks are distributed evenly among 3 workers (roughly 33% each).

### Test 4.2: Queue Handles 50 Pending Messages
RabbitMQ queue remains stable with 50 messages while API stays responsive.

### Test 4.3: Database Query Performance Under Load
PostgreSQL responds to queries in < 1s even with hundreds of task records.

## Queue Performance Tests

### Test 4.4: Rapid Fire Submissions
Submit 20 tasks in quick succession and verify all are queued and eventually processed.

### Test 4.5: Queue Doesn't Drop Messages
Verify that queue depth matches number of unprocessed tasks exactly.

### Test 4.6: Worker Throughput
Measure how many tasks 3 workers can process per minute (baseline: ~20-30 tasks/min).

## System Stability Tests

### Test 4.7: No Memory Leaks Over Time
Run 100 task submissions and check that memory usage remains stable (no growth).

### Test 4.8: API Latency Doesn't Degrade
POST /tasks latency stays < 100ms regardless of queue depth or task count.

### Test 4.9: Database Connection Pool Doesn't Exhaust
Multiple workers accessing DB simultaneously without connection errors.

## Concurrent Access Tests

### Test 4.10: Concurrent GET Requests
10 simultaneous GET /tasks/<id> requests complete without errors or timeouts.

### Test 4.11: Mixed GET/POST Under Load
Interleaved submissions and status checks while workers process tasks.

### Test 4.12: Worker Scale Performance
Adding a 4th worker dynamically shows improved throughput.

---

**Pass/Fail:** [ ] PASS / [ ] FAIL  
**Notes:** Performance tests may show graceful degradation; focus on task completion, not latency.
