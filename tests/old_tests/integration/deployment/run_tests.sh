#!/bin/bash
#
# CI/CD Test Runner for Deployment Integration Tests
#
# This script orchestrates integration test execution in CI/CD pipelines.
# It waits for services to be healthy, runs Priority 1 and Priority 2 tests,
# and generates reports in multiple formats.
#
# Exit codes:
#   0 - All P1 tests passed (P2 failures are warnings only)
#   1 - P1 tests failed or services unhealthy
#   2 - Script usage error or configuration missing
#
# Usage:
#   ./run_tests.sh [options]
#
# Options:
#   --skip-health-check    Skip waiting for services to be healthy
#   --p1-only              Run only Priority 1 tests
#   --timeout SECONDS      Health check timeout (default: 120)
#   --help                 Show this help message
#
# Environment Variables:
#   TEST_API_URL           API endpoint (default: http://localhost:8001)
#   TEST_DATABASE_URL      PostgreSQL connection string
#   TEST_RABBITMQ_URL      RabbitMQ AMQP URL
#   TEST_RABBITMQ_MGMT_URL RabbitMQ Management API URL
#   TEST_TIMEOUT           Test timeout in seconds (default: 30)
#   TEST_POLL_INTERVAL     Polling interval in seconds (default: 0.5)

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
HEALTH_CHECK_TIMEOUT="${TEST_HEALTH_CHECK_TIMEOUT:-120}"
SKIP_HEALTH_CHECK=false
P1_ONLY=false

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-health-check)
            SKIP_HEALTH_CHECK=true
            shift
            ;;
        --p1-only)
            P1_ONLY=true
            shift
            ;;
        --timeout)
            HEALTH_CHECK_TIMEOUT="$2"
            shift 2
            ;;
        --help)
            grep '^#' "$0" | sed 's/^# //' | sed 's/^#!//'
            exit 0
            ;;
        *)
            echo -e "${RED}Error: Unknown option $1${NC}" >&2
            echo "Use --help for usage information" >&2
            exit 2
            ;;
    esac
done

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

# Check required environment variables
check_environment() {
    log_info "Checking environment configuration..."

    local required_vars=(
        "TEST_API_URL"
        "TEST_DATABASE_URL"
        "TEST_RABBITMQ_URL"
        "TEST_RABBITMQ_MGMT_URL"
    )

    local missing_vars=()

    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            missing_vars+=("$var")
        fi
    done

    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        log_error "Missing required environment variables:"
        for var in "${missing_vars[@]}"; do
            echo "  - $var"
        done
        log_info "See tests/integration/deployment/README.md for configuration details"
        exit 2
    fi

    log_success "Environment configuration valid"
}

# Wait for API health endpoint to respond
wait_for_health() {
    if [[ "$SKIP_HEALTH_CHECK" == true ]]; then
        log_warning "Skipping health check (--skip-health-check specified)"
        return 0
    fi

    log_info "Waiting for services to be healthy (timeout: ${HEALTH_CHECK_TIMEOUT}s)..."

    local api_url="${TEST_API_URL:-http://localhost:8001}"
    local elapsed=0
    local interval=5

    while [[ $elapsed -lt $HEALTH_CHECK_TIMEOUT ]]; do
        if curl -sf "${api_url}/health" > /dev/null 2>&1; then
            log_success "Services are healthy"
            return 0
        fi

        sleep $interval
        elapsed=$((elapsed + interval))
        log_info "Still waiting... (${elapsed}s / ${HEALTH_CHECK_TIMEOUT}s)"
    done

    log_error "Services did not become healthy within ${HEALTH_CHECK_TIMEOUT}s"
    log_error "Check that API, database, and RabbitMQ are running"
    return 1
}

# Run Priority 1 tests (must pass)
run_p1_tests() {
    log_info "Running Priority 1 tests (critical - must pass)..."

    cd "$PROJECT_ROOT"

    pytest \
        tests/integration/deployment \
        -m p1 \
        -v \
        --tb=short \
        --json-report \
        --json-report-file=test-results-p1.json \
        --html=test-report-p1.html \
        --self-contained-html

    local exit_code=$?

    if [[ $exit_code -eq 0 ]]; then
        log_success "Priority 1 tests PASSED"
    else
        log_error "Priority 1 tests FAILED (exit code: $exit_code)"
    fi

    return $exit_code
}

# Run Priority 2 tests (failures are warnings)
run_p2_tests() {
    if [[ "$P1_ONLY" == true ]]; then
        log_info "Skipping Priority 2 tests (--p1-only specified)"
        return 0
    fi

    log_info "Running Priority 2 tests (quality checks - failures are warnings)..."

    cd "$PROJECT_ROOT"

    pytest \
        tests/integration/deployment \
        -m p2 \
        -v \
        --tb=short \
        --json-report \
        --json-report-file=test-results-p2.json \
        --html=test-report-p2.html \
        --self-contained-html

    local exit_code=$?

    if [[ $exit_code -eq 0 ]]; then
        log_success "Priority 2 tests PASSED"
    else
        log_warning "Priority 2 tests FAILED (exit code: $exit_code)"
        log_warning "P2 failures do not fail the build, but should be investigated"
    fi

    # Always return 0 for P2 tests (failures are non-blocking)
    return 0
}

# Generate combined report summary
generate_summary() {
    log_info "Generating test summary..."

    if [[ -f "test-results-p1.json" ]]; then
        echo ""
        echo "======================================================================"
        echo "Priority 1 Test Results:"
        echo "======================================================================"
        if command -v jq &> /dev/null; then
            jq -r '.summary | "Total: \(.total) | Passed: \(.passed // 0) | Failed: \(.failed // 0) | Errors: \(.error // 0)"' \
                test-results-p1.json || echo "See test-results-p1.json for details"
        else
            echo "See test-results-p1.json for details (install jq for formatted output)"
        fi
        echo "Report: test-report-p1.html"
    fi

    if [[ -f "test-results-p2.json" ]]; then
        echo ""
        echo "======================================================================"
        echo "Priority 2 Test Results:"
        echo "======================================================================"
        if command -v jq &> /dev/null; then
            jq -r '.summary | "Total: \(.total) | Passed: \(.passed // 0) | Failed: \(.failed // 0) | Errors: \(.error // 0)"' \
                test-results-p2.json || echo "See test-results-p2.json for details"
        else
            echo "See test-results-p2.json for details (install jq for formatted output)"
        fi
        echo "Report: test-report-p2.html"
    fi

    echo ""
    echo "======================================================================"
}

# Main execution
main() {
    log_info "Starting deployment integration tests..."
    echo ""

    # Check environment
    check_environment

    # Wait for services
    if ! wait_for_health; then
        exit 1
    fi

    echo ""

    # Run P1 tests (critical)
    local p1_exit_code=0
    if ! run_p1_tests; then
        p1_exit_code=1
    fi

    echo ""

    # Run P2 tests (warnings only)
    run_p2_tests

    echo ""

    # Generate summary
    generate_summary

    # Exit based on P1 results
    if [[ $p1_exit_code -eq 0 ]]; then
        log_success "All critical tests passed - deployment validated"
        exit 0
    else
        log_error "Critical tests failed - deployment validation failed"
        exit 1
    fi
}

# Run main function
main
