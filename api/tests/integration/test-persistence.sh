#!/bin/bash
# Integration test script for Database Persistence
# Verifies that tasks persist across API server restarts
#
# Prerequisites:
# - Docker and Docker Compose must be installed
# - jq must be installed (for JSON parsing): brew install jq / apt-get install jq
# - Services must be running: docker-compose up -d
#
# Usage:
#   ./test-persistence.sh
#
# The script will:
# 1. Check prerequisites
# 2. Start services (if not running)
# 3. Submit a test task
# 4. Restart the API container
# 5. Verify the task still exists with all original data
# 6. Clean up (optional)

set -e  # Exit on error

API_BASE="http://localhost:8001"
COMPOSE_FILE="docker-compose.yml"
API_CONTAINER="quantum-api"

echo "========================================"
echo "Database Persistence - Integration Test"
echo "========================================"
echo

# Check Prerequisites
echo "=== Checking Prerequisites ==="

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo "✗ FAIL: jq is not installed"
    echo "  Install with: brew install jq (macOS) or apt-get install jq (Linux)"
    exit 1
fi
echo "✓ jq is installed"

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "✗ FAIL: docker-compose is not installed"
    exit 1
fi
echo "✓ docker-compose is available"

# Determine docker-compose command
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    DOCKER_COMPOSE="docker compose"
fi

echo

# Function to wait for health check
wait_for_health() {
    local max_attempts=30
    local attempt=1

    echo "Waiting for API health check to pass..."

    while [ $attempt -le $max_attempts ]; do
        if curl -s -f $API_BASE/health > /dev/null 2>&1; then
            echo "✓ API is healthy"
            return 0
        fi
        echo "  Attempt $attempt/$max_attempts - waiting..."
        sleep 2
        attempt=$((attempt + 1))
    done

    echo "✗ FAIL: API did not become healthy after $max_attempts attempts"
    return 1
}

# Step 1: Ensure services are running
echo "=== Step 1: Starting Services ==="
$DOCKER_COMPOSE up -d
echo "✓ Services started"
echo

# Step 2: Wait for initial health check
echo "=== Step 2: Initial Health Check ==="
if ! wait_for_health; then
    exit 1
fi
echo

# Step 3: Submit a test task
echo "=== Step 3: Submit Test Task ==="
CIRCUIT_DATA='{"circuit": "OPENQASM 3; qubit[2] q; h q[0]; cx q[0], q[1]; measure q;"}'

SUBMIT_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
    -X POST $API_BASE/tasks \
    -H "Content-Type: application/json" \
    -d "$CIRCUIT_DATA")

HTTP_CODE=$(echo "$SUBMIT_RESPONSE" | grep "HTTP_CODE" | cut -d':' -f2)
BODY=$(echo "$SUBMIT_RESPONSE" | sed '/HTTP_CODE/d')

if [ "$HTTP_CODE" -ne 200 ]; then
    echo "✗ FAIL: Task submission failed with HTTP $HTTP_CODE"
    echo "Response: $BODY"
    exit 1
fi

echo "Response: $BODY"

# Step 4: Extract task_id using jq
TASK_ID=$(echo "$BODY" | jq -r '.task_id')

if [ -z "$TASK_ID" ] || [ "$TASK_ID" = "null" ]; then
    echo "✗ FAIL: Could not extract task_id from response"
    exit 1
fi

echo "✓ Task submitted successfully"
echo "  Task ID: $TASK_ID"
echo

# Step 5: Query task to get baseline data
echo "=== Step 4: Query Task (Before Restart) ==="
QUERY1_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
    $API_BASE/tasks/$TASK_ID)

HTTP_CODE=$(echo "$QUERY1_RESPONSE" | grep "HTTP_CODE" | cut -d':' -f2)
BODY_BEFORE=$(echo "$QUERY1_RESPONSE" | sed '/HTTP_CODE/d')

if [ "$HTTP_CODE" -ne 200 ]; then
    echo "✗ FAIL: Task query failed with HTTP $HTTP_CODE"
    echo "Response: $BODY_BEFORE"
    exit 1
fi

echo "Response: $BODY_BEFORE"

# Extract original task data
ORIGINAL_TASK_ID=$(echo "$BODY_BEFORE" | jq -r '.task_id')
ORIGINAL_STATUS=$(echo "$BODY_BEFORE" | jq -r '.status')
ORIGINAL_SUBMITTED_AT=$(echo "$BODY_BEFORE" | jq -r '.submitted_at')
ORIGINAL_CIRCUIT=$(echo "$BODY_BEFORE" | jq -r '.circuit')

echo "✓ Task retrieved successfully"
echo "  Task ID: $ORIGINAL_TASK_ID"
echo "  Status: $ORIGINAL_STATUS"
echo "  Submitted At: $ORIGINAL_SUBMITTED_AT"
echo

# Step 6: Restart API container
echo "=== Step 5: Restart API Container ==="
echo "Restarting $API_CONTAINER..."
$DOCKER_COMPOSE restart api

echo "✓ API container restarted"
echo

# Step 7: Wait for health check after restart
echo "=== Step 6: Health Check After Restart ==="
if ! wait_for_health; then
    exit 1
fi
echo

# Step 8: Query task again and verify persistence
echo "=== Step 7: Query Task (After Restart) ==="
QUERY2_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
    $API_BASE/tasks/$TASK_ID)

HTTP_CODE=$(echo "$QUERY2_RESPONSE" | grep "HTTP_CODE" | cut -d':' -f2)
BODY_AFTER=$(echo "$QUERY2_RESPONSE" | sed '/HTTP_CODE/d')

if [ "$HTTP_CODE" -ne 200 ]; then
    echo "✗ FAIL: Task query after restart failed with HTTP $HTTP_CODE"
    echo "Response: $BODY_AFTER"
    exit 1
fi

echo "Response: $BODY_AFTER"

# Extract task data after restart
AFTER_TASK_ID=$(echo "$BODY_AFTER" | jq -r '.task_id')
AFTER_STATUS=$(echo "$BODY_AFTER" | jq -r '.status')
AFTER_SUBMITTED_AT=$(echo "$BODY_AFTER" | jq -r '.submitted_at')
AFTER_CIRCUIT=$(echo "$BODY_AFTER" | jq -r '.circuit')

echo "✓ Task retrieved successfully after restart"
echo

# Step 9: Verify all fields match
echo "=== Step 8: Verify Data Persistence ==="
VERIFICATION_FAILED=0

# Verify task_id
if [ "$ORIGINAL_TASK_ID" != "$AFTER_TASK_ID" ]; then
    echo "✗ FAIL: task_id mismatch"
    echo "  Before: $ORIGINAL_TASK_ID"
    echo "  After:  $AFTER_TASK_ID"
    VERIFICATION_FAILED=1
else
    echo "✓ task_id matches: $AFTER_TASK_ID"
fi

# Verify status
if [ "$ORIGINAL_STATUS" != "$AFTER_STATUS" ]; then
    echo "✗ FAIL: status mismatch"
    echo "  Before: $ORIGINAL_STATUS"
    echo "  After:  $AFTER_STATUS"
    VERIFICATION_FAILED=1
else
    echo "✓ status matches: $AFTER_STATUS"
fi

# Verify submitted_at
if [ "$ORIGINAL_SUBMITTED_AT" != "$AFTER_SUBMITTED_AT" ]; then
    echo "✗ FAIL: submitted_at mismatch"
    echo "  Before: $ORIGINAL_SUBMITTED_AT"
    echo "  After:  $AFTER_SUBMITTED_AT"
    VERIFICATION_FAILED=1
else
    echo "✓ submitted_at matches: $AFTER_SUBMITTED_AT"
fi

# Verify circuit
if [ "$ORIGINAL_CIRCUIT" != "$AFTER_CIRCUIT" ]; then
    echo "✗ FAIL: circuit mismatch"
    echo "  Before: $ORIGINAL_CIRCUIT"
    echo "  After:  $AFTER_CIRCUIT"
    VERIFICATION_FAILED=1
else
    echo "✓ circuit matches"
fi

echo

if [ $VERIFICATION_FAILED -eq 1 ]; then
    echo "========================================"
    echo "✗ Persistence test FAILED"
    echo "========================================"
    exit 1
fi

# Step 10: Optional cleanup
echo "=== Step 9: Cleanup (Optional) ==="
echo "Task $TASK_ID left in database for manual inspection"
echo "To clean up manually, you can:"
echo "  - Delete the task via API (if DELETE endpoint exists)"
echo "  - Reset database: docker-compose down -v && docker-compose up -d"
echo

echo "========================================"
echo "✓ Persistence test PASSED"
echo "========================================"
echo "Task persisted successfully across API restart"
echo "All fields verified: task_id, status, submitted_at, circuit"
echo "========================================"
