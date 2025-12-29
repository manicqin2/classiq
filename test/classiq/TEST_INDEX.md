# Classiq Quantum Circuits API - Test Index

## Quick Navigation

| Document | Purpose | Duration | Critical |
|----------|---------|----------|----------|
| **TESTING_GUIDE.md** | Overview & strategy | 5 min | ✓ Start here |
| **TESTS_PRIORITY_1.md** | Infrastructure & core API | 25 min | ✓ MUST PASS |
| **TESTS_PRIORITY_2.md** | Task integrity & reliability | 20 min | ✓ MUST PASS |
| **TESTS_PRIORITY_3.md** | Scalability & performance | 15 min | ~ Nice to have |
| **TESTS_PRIORITY_4.md** | Production readiness | 10 min | ~ Nice to have |
| **TESTS_PRIORITY_5.md** | Edge cases | 10 min | ~ Optional |
| **TEST_SCRIPT.sh** | Automated execution | - | ✓ Use for batch |

---

## Test Execution Path

```
START
  ↓
Read: TESTING_GUIDE.md (understand strategy)
  ↓
Run: TESTS_PRIORITY_1.md (25 min)
  ├─ If FAIL → Debug & fix infrastructure
  ├─ If PASS → Continue
  ↓
Run: TESTS_PRIORITY_2.md (20 min)
  ├─ If FAIL → Debug error handling
  ├─ If PASS → Continue
  ↓
Run: TESTS_PRIORITY_3.md (15 min)
  ├─ If FAIL → Analyze bottlenecks (may be acceptable)
  ├─ If PASS → Continue
  ↓
Run: TESTS_PRIORITY_4.md (10 min)
  ├─ If FAIL → Improve logging/monitoring (nice to have)
  ├─ If PASS → Continue
  ↓
Run: TESTS_PRIORITY_5.md (10 min) - OPTIONAL
  ├─ If FAIL → Fix edge cases (low priority)
  ├─ If PASS → Ready for submission
  ↓
READY FOR SUBMISSION
```

---

## What Each Priority Tests

### Priority 1: Critical Path (MUST PASS)

**Validates:** Basic infrastructure and API functionality

**Tests:**
- Docker Compose startup
- PostgreSQL schema initialization
- RabbitMQ queue/exchange setup
- FastAPI server responsiveness
- POST /tasks submission
- GET /tasks status retrieval
- End-to-end task execution

**Time:** 25 minutes  
**Pass Rate:** 100% required

---

### Priority 2: Task Integrity & Reliability (MUST PASS)

**Validates:** Data is never lost, errors handled gracefully

**Tests:**
- Message published to queue
- Message acknowledgment
- Worker crash recovery
- Invalid input rejection
- Task not found error
- Database consistency
- No lost tasks across submissions

**Time:** 20 minutes  
**Pass Rate:** 100% required

---

### Priority 3: Scalability & Performance (NICE TO HAVE)

**Validates:** System handles moderate load efficiently

**Tests:**
- Load balancing among workers
- Queue performance with 50+ messages
- Database query performance
- Rapid submissions
- Worker throughput measurement
- Concurrent GET requests
- Mixed workload handling

**Time:** 15 minutes  
**Pass Rate:** ≥95% expected

---

### Priority 4: Production Readiness (NICE TO HAVE)

**Validates:** System is observable and debuggable

**Tests:**
- API logging
- Worker logging
- Error logging with context
- RabbitMQ management UI
- API Swagger documentation
- Database persistence across restart
- RabbitMQ message persistence
- Container health checks
- Graceful shutdown

**Time:** 10 minutes  
**Pass Rate:** ≥90% expected

---

### Priority 5: Edge Cases (OPTIONAL)

**Validates:** Unusual inputs don't cause catastrophic failures

**Tests:**
- Large circuits
- Empty/null inputs
- Invalid QASM3
- High concurrency (100 submissions)
- API crashes
- Database unavailability
- Race conditions
- Zombie worker recovery

**Time:** 10 minutes  
**Pass Rate:** ≥80% acceptable

---

## Quick Test Commands

### Start System
```bash
docker-compose down -v
docker-compose up -d
sleep 30
docker-compose ps
```

### Check Health
```bash
curl http://localhost:5000/health
docker-compose exec rabbitmq rabbitmqctl list_queues
docker-compose exec postgres psql -U quantum_user -d quantum_db -c "SELECT COUNT(*) FROM tasks;"
```

### Submit Task
```bash
curl -X POST http://localhost:5000/tasks \
  -H "Content-Type: application/json" \
  -d '{"qc": "OPENQASM 3; qubit q; h q; measure q;"}'
```

### Monitor
```bash
docker-compose logs -f quantum-worker-1
docker-compose logs -f quantum-api
docker-compose logs -f quantum-rabbitmq
```

### Access UIs
- **API Docs:** http://localhost:5000/docs
- **RabbitMQ Management:** http://localhost:15672 (quantum_user / quantum_pass)

---

## Debugging Quick Reference

| Issue | Solution |
|-------|----------|
| Container won't start | `docker-compose logs {service}` |
| Port already in use | `lsof -i :5000` or `docker-compose down -v` |
| Task not processing | Check worker logs + RabbitMQ consumers |
| Database connection error | Verify PostgreSQL health check |
| Task stays pending | Check if worker is consuming from queue |
| Queue doesn't clear | Verify workers have ACK enabled |

---

## Submission Checklist

Before submitting, ensure:

- [ ] Priority 1 tests: 100% pass rate
- [ ] Priority 2 tests: 100% pass rate
- [ ] Priority 3 tests: ≥95% pass rate
- [ ] Priority 4 tests: ≥90% pass rate
- [ ] No test requires manual code changes between runs
- [ ] `docker-compose up -d` works cleanly
- [ ] All test results documented in TEST_RESULTS.md
- [ ] No hardcoded test data in production code

---

## Testing Tips

1. **Run tests in quiet terminal** to focus on output
2. **Use separate terminals** for logs, testing, monitoring
3. **Wait after docker-compose up** - health checks take ~30 seconds
4. **Test in order** - Priority 1 must pass before 2, etc.
5. **Document failures** - Note exact error, container logs snippet
6. **Check logs first** - Most issues visible in `docker-compose logs`
7. **Test with fresh data** - Clear database between Priority tests: `docker-compose exec postgres psql -U quantum_user -d quantum_db -c "DELETE FROM tasks;"`

---

## Performance Baselines

These are target metrics for Priority 3+ tests:

| Metric | Target | Acceptable Range |
|--------|--------|------------------|
| Task submission latency | < 100ms | < 500ms |
| Task completion time | 2-5s | < 10s |
| Queue processing | 20-30 tasks/min | > 10 tasks/min |
| API response (health check) | < 50ms | < 500ms |
| Database query | < 100ms | < 1000ms |
| Worker load balance | ±1 task | ±2 tasks |

---

## FAQ

**Q: Do I need to pass all tests to submit?**  
A: Priority 1 and 2 (critical path + reliability) must pass. Priority 3+ are nice to have.

**Q: What if my system is slower than baselines?**  
A: Focus on correctness (Priority 1/2) over performance (Priority 3/4). Slow systems that work are better than fast systems that lose data.

**Q: Can I run tests while developing?**  
A: Yes! Test frequently. Each Priority level takes 10-25 minutes to run.

**Q: What if a test fails intermittently?**  
A: Usually a timing issue. Increase sleep durations and rerun. If still intermittent, check logs for race conditions.

**Q: Should I automate all tests?**  
A: Optional. Manual testing following these guides is sufficient. TEST_SCRIPT.sh is provided as starting point.

---

## File Organization

```
classiq-exercise/
├── TESTING_GUIDE.md          ← Start here (strategy)
├── TESTS_PRIORITY_1.md       ← Critical path (MUST PASS)
├── TESTS_PRIORITY_2.md       ← Reliability (MUST PASS)
├── TESTS_PRIORITY_3.md       ← Scalability (nice to have)
├── TESTS_PRIORITY_4.md       ← Production (nice to have)
├── TESTS_PRIORITY_5.md       ← Edge cases (optional)
├── TEST_SCRIPT.sh            ← Automated runner
├── TEST_RESULTS.md           ← Fill this after testing
│
├── docker-compose.yml
├── README.md
├── ARCHITECTURE.md
│
├── api/                       ← Your implementation
├── worker/                    ← Your implementation
├── migrations/
└── tests/
```

---

## Next Steps

1. Read **TESTING_GUIDE.md** (5 minutes)
2. Run **TESTS_PRIORITY_1.md** (25 minutes)
3. Debug any failures
4. Run **TESTS_PRIORITY_2.md** (20 minutes)
5. Continue through remaining priorities as time allows
6. Document results in TEST_RESULTS.md
7. Submit when ready

**Happy testing!** 🚀

---

**Last Updated:** 2025-01-29  
**Test Framework:** Docker Compose + curl + psql  
**Estimated Total Time:** 90 minutes
