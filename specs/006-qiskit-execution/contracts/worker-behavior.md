# Worker Behavior Contract

**Feature**: 006-qiskit-execution
**Date**: 2025-12-29

## Overview

This document defines the behavioral contracts for quantum circuit execution workers. While there are no API contract changes (worker is internal), this formalizes worker startup, execution, and error handling contracts.

---

## Worker Startup Contract

### Qiskit Validation

**Requirement**: Worker MUST validate Qiskit availability before consuming messages

**Success Criteria**:
```python
# Successful validation
- Qiskit imports without ImportError
- qiskit.qasm3 module available
- AerSimulator importable from qiskit_aer
- Basic circuit parsing works
→ Worker proceeds to consume messages
→ Logs: "Qiskit version: X.Y.Z" at INFO level
```

**Failure Criteria**:
```python
# Failed validation
- ImportError on qiskit or qiskit_aer
- qiskit.__version__ incompatible (<1.0)
- Test circuit parse fails
→ Worker logs error to stderr
→ Worker exits with code 1
→ Container orchestration detects failure
```

**Implementation**:
```python
import sys
import logging

logger = logging.getLogger(__name__)

def validate_qiskit():
    try:
        from qiskit import qasm3, __version__
        from qiskit_aer import AerSimulator

        # Test basic functionality
        test_circuit = qasm3.loads("OPENQASM 3; qubit q;")
        simulator = AerSimulator()

        logger.info(f"Qiskit validation successful: version {__version__}")
        return True

    except ImportError as e:
        logger.error(f"FATAL: Qiskit import failed: {e}", file=sys.stderr)
        return False
    except Exception as e:
        logger.error(f"FATAL: Qiskit validation failed: {e}", file=sys.stderr)
        return False

# In worker startup
if not validate_qiskit():
    sys.exit(1)
```

**Exit Codes**:
- `0`: Normal shutdown (SIGTERM, graceful stop)
- `1`: Fatal error (Qiskit unavailable, critical failure)

---

## Circuit Execution Contract

### Input Contract

**Source**: RabbitMQ queue message
**Format**: JSON message with task_id

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Worker Responsibilities**:
1. Fetch full task from database using task_id
2. Extract `circuit` field (OpenQASM 3 string)
3. Extract execution parameters (shots from task or default 1024)

### Processing Contract

**State Transitions**:
```
1. Receive message → query database for task
2. Task exists → update status to "processing"
3. Parse circuit with qiskit.qasm3.loads()
4. Execute with AerSimulator.run(circuit, shots=shots)
5. Get results with job.result().get_counts()
6. Update task: status="completed", result=counts
7. Acknowledge message (remove from queue)
```

**Timing Guarantees**:
- Status update to "processing" within 100ms of message receipt
- Parse errors detected within 1 second
- Circuit execution: No timeout (user responsibility)
- Database update after execution: within 100ms
- Message acknowledge: Only after database commit

### Output Contract

**Success Case**:
```python
# Database update
task.current_status = "completed"
task.result = {
    "0": 512,
    "1": 512
}  # Qiskit counts dict
task.completed_at = datetime.utcnow()

# Status history entry
StatusHistory(
    task_id=task.task_id,
    status="completed",
    notes="Task completed successfully"
)

# Message acknowledged (removed from queue)
```

**Failure Case**:
```python
# Database update
task.current_status = "failed"
task.error_message = "Circuit parse error: QASM3ImporterError: ..."
task.completed_at = datetime.utcnow()
task.result = null  # Remains null

# Status history entry
StatusHistory(
    task_id=task.task_id,
    status="failed",
    notes="Task failed: parse error"
)

# Message acknowledged (removed from queue)
```

---

## Error Handling Contract

### Exception Categories

**1. Import Errors (Startup)**
```python
ImportError during Qiskit import
→ Log to stderr
→ Exit with code 1
→ Never consume messages
```

**2. Parse Errors (Per Task)**
```python
QASM3ImporterError during qasm3.loads()
→ Update task: status=failed, error_message=details
→ Create status history entry
→ Acknowledge message
→ Continue processing next task
```

**3. Execution Errors (Per Task)**
```python
AerError, MemoryError during simulation
→ Update task: status=failed, error_message=details
→ Create status history entry
→ Acknowledge message
→ Continue processing next task
```

**4. Database Errors (Per Task)**
```python
SQLAlchemy errors during task update
→ Log error with task_id
→ DO NOT acknowledge message (will be retried)
→ Continue attempting next task
```

**5. Unexpected Errors (Per Task)**
```python
Any other Exception
→ Log full stack trace
→ Update task if possible: status=failed
→ Acknowledge message (prevent retry loop)
→ Continue processing next task
```

### Retry Behavior

**Message Retry**:
- Database errors → message NOT acknowledged → RabbitMQ redelivers
- All other errors → message acknowledged → no retry
- Max retries: Handled by RabbitMQ (dead letter queue if configured)

**Worker Crash**:
- Unacknowledged message → returned to queue
- Another worker processes task
- Idempotent status updates prevent duplicate work

---

## Resource Management Contract

### Memory

**Guarantee**: Worker processes one task at a time (prefetch_count=1)

**Behavior**:
- Circuit and result objects created in function scope
- Python GC reclaims memory after task completion
- No explicit cleanup required (per research.md findings)

**Monitoring**:
- Log worker memory usage periodically (optional)
- Restart workers if memory growth detected (operational concern)

### CPU

**Guarantee**: No artificial limits on circuit execution time

**Behavior**:
- Large circuits may take significant time (user responsibility)
- No timeout enforcement (clarification decision)
- One circuit at a time prevents CPU saturation

### Connections

**Guarantee**: Database and queue connections maintained

**Behavior**:
- Connection pool managed by existing infrastructure
- Reconnection on transient failures (existing behavior)
- Worker exits on persistent connection failures

---

## Observability Contract

### Logging Requirements

**Startup**:
```
INFO: Starting quantum task worker
INFO: Qiskit validation successful: version 1.0.0
INFO: Started consuming messages from queue
```

**Per Task**:
```
INFO: message_received task_id=... correlation_id=...
INFO: Processing task task_id=...
INFO: Transitioning task to PROCESSING task_id=...
INFO: Executing circuit: 2 qubits, 3 depth, 1024 shots task_id=...
INFO: Quantum circuit execution completed task_id=... result={'0': 512, '1': 512}
INFO: Transitioning task to COMPLETED task_id=...
INFO: Task successfully completed task_id=...
INFO: message_acknowledged task_id=...
```

**Errors**:
```
ERROR: Circuit parse error task_id=... error=QASM3ImporterError: ...
ERROR: Execution error task_id=... error=AerError: ...
ERROR: Database update failed task_id=... error=...
ERROR: Unexpected error task_id=... error=... traceback=...
```

### Metrics (Recommended)

- Circuit execution time per task
- Task success/failure rate
- Queue message processing rate
- Worker memory usage

---

## Queue Message Format

### Input Message (Unchanged)

**Source**: Published by API when task created

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "correlation_id": "abc123..."
}
```

**Validation**:
- task_id must be valid UUID
- task_id must exist in database
- If invalid → log error, acknowledge message, continue

### No Output Messages

Worker does not publish messages; results stored in database only.

---

## Contract Verification

### Unit Tests

```python
def test_qiskit_validation_success():
    """Worker validates Qiskit on startup"""
    assert validate_qiskit() == True

def test_qiskit_validation_failure():
    """Worker exits if Qiskit unavailable"""
    # Mock ImportError
    with patch('qiskit.qasm3.loads', side_effect=ImportError):
        assert validate_qiskit() == False

def test_parse_error_handling():
    """Worker handles QASM parse errors gracefully"""
    invalid_circuit = "invalid qasm"
    # Should not crash, should return error
    result = execute_circuit(invalid_circuit, shots=1024)
    assert result.status == "failed"
    assert "parse error" in result.error_message.lower()
```

### Integration Tests

```python
def test_end_to_end_execution():
    """Worker executes valid circuit and stores results"""
    # Submit task
    task_id = submit_task(circuit="OPENQASM 3; qubit q; h q;")

    # Wait for completion
    task = poll_until_complete(task_id, timeout=30)

    # Verify
    assert task.status == "completed"
    assert task.result is not None
    assert "0" in task.result
    assert "1" in task.result
    assert sum(task.result.values()) == 1024  # default shots
```

---

## Summary

**Worker Startup**:
- ✅ Validates Qiskit availability
- ✅ Exits with code 1 if validation fails
- ✅ Logs version on success

**Task Processing**:
- ✅ Updates status to "processing" immediately
- ✅ Parses OpenQASM 3 with Qiskit
- ✅ Executes with AerSimulator
- ✅ Stores counts in result field
- ✅ Handles errors gracefully
- ✅ Acknowledges message after database commit

**Error Handling**:
- ✅ Three-tier: Import/Parse/Runtime
- ✅ Startup errors → exit
- ✅ Task errors → update and continue
- ✅ Database errors → retry via message redelivery

**Resource Management**:
- ✅ One task at a time
- ✅ No enforced timeout
- ✅ Automatic memory cleanup via GC

All contracts defined and ready for implementation.
