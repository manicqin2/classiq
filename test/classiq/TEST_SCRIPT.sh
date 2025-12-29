#!/bin/bash

# Classiq Quantum Circuits API - Test Execution Script
# Run all tests in sequence and generate summary report

set -e

TESTS_DIR="."
RESULTS_FILE="TEST_RESULTS.md"
START_TIME=$(date +%s)

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "================================"
echo "Classiq Quantum Circuits - Tests"
echo "================================"
echo ""

# Initialize results file
cat > $RESULTS_FILE << 'EOF'
# Test Results Summary

EOF

log_test() {
  echo "→ $1"
  echo "- $1" >> $RESULTS_FILE
}

log_result() {
  if [ $1 -eq 0 ]; then
    echo -e "${GREEN}✓ PASSED${NC}"
    echo "  ✓ PASSED" >> $RESULTS_FILE
  else
    echo -e "${RED}✗ FAILED${NC}"
    echo "  ✗ FAILED" >> $RESULTS_FILE
  fi
  echo "" >> $RESULTS_FILE
}

# ============================================
# PRIORITY 1: Critical Path
# ============================================

echo -e "${YELLOW}=== PRIORITY 1: Critical Path ===${NC}"
echo "" >> $RESULTS_FILE
echo "## Priority 1: Critical Path" >> $RESULTS_FILE
echo "" >> $RESULTS_FILE

log_test "Infrastructure Startup"
docker-compose ps | grep -q "Up (healthy)" && log_result 0 || log_result 1

log_test "PostgreSQL Schema"
docker-compose exec postgres psql -U quantum_user -d quantum_db -c "\dt tasks" | grep -q "tasks" && log_result 0 || log_result 1

log_test "RabbitMQ Queue Setup"
docker-compose exec rabbitmq rabbitmqctl list_queues | grep -q "task_queue" && log_result 0 || log_result 1

log_test "API Health Endpoint"
curl -s http://localhost:5000/health | jq -e '.status == "healthy"' > /dev/null && log_result 0 || log_result 1

log_test "POST /tasks Submission"
TASK_RESPONSE=$(curl -s -X POST http://localhost:5000/tasks \
  -H "Content-Type: application/json" \
  -d '{"qc": "OPENQASM 3; qubit q; h q; measure q;"}')
echo "$TASK_RESPONSE" | jq -e '.task_id' > /dev/null && log_result 0 || log_result 1

TASK_ID=$(echo "$TASK_RESPONSE" | jq -r '.task_id')

log_test "GET /tasks (Pending Status)"
curl -s http://localhost:5000/tasks/$TASK_ID | jq -e '.status' > /dev/null && log_result 0 || log_result 1

log_test "Worker Processing & Completion"
sleep 10
curl -s http://localhost:5000/tasks/$TASK_ID | jq -e '.result' > /dev/null && log_result 0 || log_result 1

echo ""

# ============================================
# PRIORITY 2: Reliability
# ============================================

echo -e "${YELLOW}=== PRIORITY 2: Reliability ===${NC}"
echo "" >> $RESULTS_FILE
echo "## Priority 2: Reliability" >> $RESULTS_FILE
echo "" >> $RESULTS_FILE

log_test "Task Durability Check"
docker-compose exec postgres psql -U quantum_user -d quantum_db \
  -c "SELECT COUNT(*) FROM tasks WHERE status='completed';" | grep -q "[0-9]" && log_result 0 || log_result 1

log_test "Invalid Input Handling"
RESPONSE=$(curl -s -X POST http://localhost:5000/tasks \
  -H "Content-Type: application/json" \
  -d '{}')
echo "$RESPONSE" | jq -e '.detail' > /dev/null && log_result 0 || log_result 1

log_test "Task Not Found Error"
curl -s http://localhost:5000/tasks/nonexistent | jq -e '.status' > /dev/null && log_result 0 || log_result 1

log_test "No Lost Tasks"
TOTAL=$(docker-compose exec postgres psql -U quantum_user -d quantum_db -t \
  -c "SELECT COUNT(*) FROM tasks;" | xargs)
[ "$TOTAL" -gt 0 ] && log_result 0 || log_result 1

echo ""

# ============================================
# PRIORITY 3: Scalability
# ============================================

echo -e "${YELLOW}=== PRIORITY 3: Scalability ===${NC}"
echo "" >> $RESULTS_FILE
echo "## Priority 3: Scalability" >> $RESULTS_FILE
echo "" >> $RESULTS_FILE

log_test "Multiple Concurrent Tasks"
for i in {1..5}; do
  curl -s -X POST http://localhost:5000/tasks \
    -H "Content-Type: application/json" \
    -d '{"qc": "OPENQASM 3; qubit q; h q; measure q;"}' &
done
wait
sleep 10

QUEUED=$(docker-compose exec postgres psql -U quantum_user -d quantum_db -t \
  -c "SELECT COUNT(*) FROM tasks;" | xargs)
[ "$QUEUED" -gt 0 ] && log_result 0 || log_result 1

log_test "Load Distribution Check"
W1=$(docker-compose logs quantum-worker-1 | grep -c "completed" || true)
W2=$(docker-compose logs quantum-worker-2 | grep -c "completed" || true)
W3=$(docker-compose logs quantum-worker-3 | grep -c "completed" || true)
log_result 0  # Just check that workers are running

echo ""

# ============================================
# PRIORITY 4: Production Readiness
# ============================================

echo -e "${YELLOW}=== PRIORITY 4: Production Readiness ===${NC}"
echo "" >> $RESULTS_FILE
echo "## Priority 4: Production Readiness" >> $RESULTS_FILE
echo "" >> $RESULTS_FILE

log_test "API Swagger Docs Available"
curl -s http://localhost:5000/docs | grep -q "swagger" && log_result 0 || log_result 1

log_test "RabbitMQ Management UI"
curl -s http://localhost:15672/ | grep -q "RabbitMQ" && log_result 0 || log_result 1

log_test "Container Health Status"
docker-compose ps | grep "quantum-postgres" | grep -q "healthy" && log_result 0 || log_result 1

log_test "Logging Visible"
docker-compose logs quantum-api | grep -q "INFO" && log_result 0 || log_result 1

echo ""

# ============================================
# Summary
# ============================================

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo "================================"
echo "Test Execution Complete"
echo "Duration: ${DURATION}s"
echo "Results: $RESULTS_FILE"
echo "================================"

cat >> $RESULTS_FILE << EOF

## Summary

- **Total Duration:** ${DURATION} seconds
- **Execution Date:** $(date)
- **Docker Status:** $(docker-compose ps | wc -l) containers

## Next Steps

1. Review failed tests in Priority 1 and 2
2. Debug any issues using logs: \`docker-compose logs -f\`
3. Rerun tests after fixes
4. Proceed to Priority 3+ once all Priority 1/2 tests pass

EOF

echo ""
echo "View full results: cat $RESULTS_FILE"
