#!/bin/bash
# Integration test script for Quantum Circuit API
# Tests all three main endpoints with various scenarios

set -e  # Exit on error

API_BASE="http://localhost:8000"

echo "========================================"
echo "Quantum Circuit API - Integration Tests"
echo "========================================"
echo

# Test 1: Health Check
echo "=== Test 1: Health Check ==="
HEALTH_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" $API_BASE/health)
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | grep "HTTP_CODE" | cut -d':' -f2)
BODY=$(echo "$HEALTH_RESPONSE" | sed '/HTTP_CODE/d')

echo "Response: $BODY"
if [ "$HTTP_CODE" -eq 200 ]; then
    echo "✓ PASS: Health check returned 200"
else
    echo "✗ FAIL: Expected 200, got $HTTP_CODE"
    exit 1
fi
echo

# Test 2: Submit Valid Task
echo "=== Test 2: Submit Valid Task ==="
SUBMIT_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
    -X POST $API_BASE/tasks \
    -H "Content-Type: application/json" \
    -d '{"circuit": "OPENQASM 3; qubit q; h q; measure q;"}')

HTTP_CODE=$(echo "$SUBMIT_RESPONSE" | grep "HTTP_CODE" | cut -d':' -f2)
BODY=$(echo "$SUBMIT_RESPONSE" | sed '/HTTP_CODE/d')

echo "Response: $BODY"
if [ "$HTTP_CODE" -eq 200 ]; then
    echo "✓ PASS: Task submission returned 200"
    TASK_ID=$(echo "$BODY" | grep -o '"task_id":"[^"]*"' | cut -d'"' -f4)
    echo "  Task ID: $TASK_ID"
else
    echo "✗ FAIL: Expected 200, got $HTTP_CODE"
    exit 1
fi
echo

# Test 3: Query Task Status
echo "=== Test 3: Query Task Status ==="
STATUS_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
    $API_BASE/tasks/$TASK_ID)

HTTP_CODE=$(echo "$STATUS_RESPONSE" | grep "HTTP_CODE" | cut -d':' -f2)
BODY=$(echo "$STATUS_RESPONSE" | sed '/HTTP_CODE/d')

echo "Response: $BODY"
if [ "$HTTP_CODE" -eq 200 ]; then
    echo "✓ PASS: Task status query returned 200"
else
    echo "✗ FAIL: Expected 200, got $HTTP_CODE"
    exit 1
fi
echo

# Test 4: Submit Task Without Circuit Field
echo "=== Test 4: Validation Error (Missing Field) ==="
ERROR_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
    -X POST $API_BASE/tasks \
    -H "Content-Type: application/json" \
    -d '{}')

HTTP_CODE=$(echo "$ERROR_RESPONSE" | grep "HTTP_CODE" | cut -d':' -f2)
BODY=$(echo "$ERROR_RESPONSE" | sed '/HTTP_CODE/d')

echo "Response: $BODY"
if [ "$HTTP_CODE" -eq 400 ]; then
    echo "✓ PASS: Validation error returned 400"
else
    echo "✗ FAIL: Expected 400, got $HTTP_CODE"
    exit 1
fi
echo

# Test 5: Invalid Task ID Format
echo "=== Test 5: Invalid UUID Format ==="
INVALID_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
    $API_BASE/tasks/not-a-uuid)

HTTP_CODE=$(echo "$INVALID_RESPONSE" | grep "HTTP_CODE" | cut -d':' -f2)
BODY=$(echo "$INVALID_RESPONSE" | sed '/HTTP_CODE/d')

echo "Response: $BODY"
if [ "$HTTP_CODE" -eq 400 ]; then
    echo "✓ PASS: Invalid UUID returned 400"
else
    echo "✗ FAIL: Expected 400, got $HTTP_CODE"
    exit 1
fi
echo

echo "========================================"
echo "All integration tests passed! ✓"
echo "========================================"
