# Priority 5: Edge Cases & Advanced Scenarios

**Scope:** Boundary conditions, unusual inputs, recovery scenarios  
**Duration:** 10 minutes  
**Pass Rate Required:** ≥80% (optional to pass)

## Input Validation Edge Cases

### Test 6.1: Very Large QASM3 Circuit
Submit a circuit with 50+ qubits; system handles gracefully or rejects with clear error.

### Test 6.2: Empty String Circuit
Submit `{"qc": ""}` and verify worker fails gracefully with status='failed'.

### Test 6.3: Null Circuit Value
Submit `{"qc": null}` and verify API returns validation error (422).

### Test 6.4: Extremely Long Task ID Lookup
Query GET /tasks with 1000-character string; returns 400 or clear error.

## Concurrency Edge Cases

### Test 6.5: Duplicate Task Submission
Submit same circuit twice rapidly; both get unique task IDs and both complete.

### Test 6.6: Resubmit After Completion
Query completed task, then submit again with same circuit; new task created.

### Test 6.7: High Concurrency POST
100 submissions in 5 seconds; all succeed without 429 (rate limit) errors.

## Recovery Scenarios

### Test 6.8: API Container Crashes
Kill API container with `docker kill quantum-api`; tasks already in queue are still processed.

### Test 6.9: Database Connection Loss
Simulate DB unavailability; API returns error, worker retries, no tasks lost.

### Test 6.10: Partial Worker Failure
Two workers operational, one dead; remaining workers handle all tasks (slower but complete).

## Race Conditions

### Test 6.11: GET While Status Transitioning
Query status simultaneously with worker marking task complete; consistent result.

### Test 6.12: Multiple Workers Process Same Task
Configure workers to not ACK (if possible); verify only one ultimately wins.

### Test 6.13: Rapid Status Changes
Query task status 100 times per second during completion; no inconsistent states.

## Boundary & Stress Tests

### Test 6.14: Database Row Limit Behavior
Insert 10,000 tasks; queries still work, no performance collapse.

### Test 6.15: Very Rapid Create/Delete
Submit 50 tasks, delete them from DB, submit 50 more; no ID conflicts.

### Test 6.16: Circuit with Special Characters
Submit circuit containing unicode or escaped characters; handling is correct.

## Unusual Execution Scenarios

### Test 6.17: Worker Takes Very Long Time
Simulate long-running circuit (100+ seconds); task eventually completes.

### Test 6.18: Worker Completes But Can't Write DB
Worker executes circuit successfully but DB connection fails; automatic retry.

### Test 6.19: Zombie Worker State
Worker crash leaves message unacked; verify it's redelivered within 30 seconds.

---

**Pass/Fail:** [ ] PASS / [ ] FAIL  
**Notes:** Edge cases are optional for MVP; focus on ensuring no catastrophic failures or data corruption.
