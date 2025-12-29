# Data Model: Qiskit Circuit Execution

**Feature**: 006-qiskit-execution
**Date**: 2025-12-29

## Overview

This document defines the data structures for quantum circuit execution. The existing Task model is sufficient; no schema changes required. This document formalizes the JSONB structure for measurement results.

---

## Entities

### Task (Existing)

**Table**: `tasks`
**Source**: `api/src/db/models.py`

Represents a quantum circuit execution request and its results.

**Fields**:
- `task_id` (UUID, PK): Unique identifier for the task
- `circuit` (TEXT): OpenQASM 3 circuit definition
- `submitted_at` (TIMESTAMP): When task was submitted
- `current_status` (ENUM: pending, processing, completed, failed): Task state
- `completed_at` (TIMESTAMP, nullable): When task finished (completed or failed)
- `result` (JSONB, nullable): Measurement counts (structure defined below)
- `error_message` (TEXT, nullable): Error details if status=failed

**State Transitions**:
```
pending → processing → completed (success path)
pending → processing → failed (error path)
```

**Changes for This Feature**: None (schema unchanged)

---

## JSONB Structures

### Measurement Result (result field)

**Type**: JSONB dictionary mapping basis states to counts

**Structure**:
```json
{
  "00": 512,
  "01": 0,
  "10": 0,
  "11": 512
}
```

**Specification**:
- **Keys**: Bitstrings representing measured quantum states
  - Format: `"0"`, `"1"` for 1 qubit; `"00"`, `"01"`, `"10"`, `"11"` for 2 qubits, etc.
  - Length: Number of measured qubits
  - Endianness: Little-endian (rightmost bit = qubit 0)
  - Character set: Only `'0'` and `'1'`

- **Values**: Non-negative integers
  - Meaning: Number of times this state was measured
  - Range: 0 to total shots
  - Sum: All values sum to total shots executed

- **Sparse Representation**: Only states with count > 0 need to be included
  - Example: `{"0": 1024}` for deterministic circuit (all measurements → |0⟩)
  - Unmeasured states may be omitted or included with count 0

**Validation Rules**:
- Keys must be valid bitstrings (only '0' and '1')
- All keys must have same length (same number of qubits)
- Values must be non-negative integers
- Sum of values should equal requested shots (within rounding for sampling methods)

**Examples**:

*Single qubit after Hadamard gate (50/50 superposition)*:
```json
{
  "0": 512,
  "1": 512
}
```

*Bell state (2-qubit entanglement, only |00⟩ and |11⟩)*:
```json
{
  "00": 501,
  "11": 523
}
```

*Deterministic circuit (all measurements → |0⟩)*:
```json
{
  "0": 1024
}
```

*Circuit with no measurements (valid but empty)*:
```json
{}
```

**Storage Considerations**:
- PostgreSQL JSONB handles sparse dictionaries efficiently
- No enforced size limit (clarification: user responsibility for circuit complexity)
- Typical circuit (≤15 qubits, sparse results): <1KB JSONB
- Large circuits (20+ qubits, many outcomes): Could reach MB scale, but rare

---

### Error Message (error_message field)

**Type**: TEXT

**Format**: Structured error string with error type prefix

**Examples**:

*Parse error*:
```
Circuit parse error: QASM3ImporterError: undefined gate 'invalid_gate' at line 3
```

*Execution error*:
```
Execution error: AerError: memory allocation failed for circuit with 25 qubits
```

*Unexpected error*:
```
Unexpected error: ValueError: shots must be positive integer
```

**Structure**:
```
{error_category}: {exception_type}: {error_details}
```

**Categories**:
- `Circuit parse error`: QASM3ImporterError during qasm3.loads()
- `Execution error`: AerError or runtime issues during simulation
- `Unexpected error`: Catch-all for unhandled exceptions

**Purpose**: Human-readable error messages for debugging and user feedback

---

## Relationships

### Task → Status History (Existing)

**Table**: `status_history`
**Relationship**: One task has many status history entries

**Relevant for This Feature**:
- Worker creates status history entries when transitioning task states
- Entry created when task goes `pending → processing`
- Entry created when task goes `processing → completed/failed`

**No changes required**: Existing status history tracking sufficient

---

## Data Flow

### Successful Execution Flow

```
1. Task created: status=pending, result=null, error_message=null
2. Worker picks up task
3. Worker updates: status=processing (status history entry created)
4. Qiskit executes circuit
5. Worker updates: status=completed, result={counts}, completed_at=now()
6. Status history entry created for completion
```

### Failed Execution Flow

```
1. Task created: status=pending, result=null, error_message=null
2. Worker picks up task
3. Worker updates: status=processing (status history entry created)
4. Qiskit raises exception
5. Worker updates: status=failed, error_message="...", completed_at=now()
6. Status history entry created for failure
```

---

## Database Queries

### No Changes Required

Existing queries in `api/src/db/repository.py` handle:
- Creating tasks with JSONB result field
- Updating task status and result
- Retrieving tasks by ID
- Updating task with error messages

**Example usage** (existing pattern):
```python
# Update task with Qiskit result
task = await repository.get_task(task_id)
task.current_status = TaskStatus.COMPLETED
task.result = {"0": 512, "1": 512}  # Qiskit counts dict
task.completed_at = datetime.utcnow()
await repository.update_task(task)
```

---

## Validation

### Input Validation (API Layer - Existing)

Already handled by `api/models.py`:
- Circuit is non-empty string
- Shots is positive integer in range 1-100,000

### Result Validation (Worker Layer - This Feature)

Worker validates Qiskit output before storing:
```python
def validate_counts(counts: dict) -> bool:
    """Validate Qiskit measurement counts"""
    if not isinstance(counts, dict):
        return False

    # All keys must be bitstrings
    for key in counts.keys():
        if not isinstance(key, str) or not all(c in '01' for c in key):
            return False

    # All values must be non-negative integers
    for value in counts.values():
        if not isinstance(value, int) or value < 0:
            return False

    return True
```

**Note**: Qiskit guarantees valid output format, so validation is defensive programming rather than expected to catch errors.

---

## Migration Impact

### Schema Changes
**None required**. Existing `tasks.result` JSONB field stores measurement counts.

### Data Migration
**None required**. Existing mock results will be overwritten as tasks are re-executed with Qiskit.

### Backward Compatibility
**Maintained**. API contract unchanged; clients receive same response structure with different (real) result values.

---

## Summary

- ✅ No database schema changes
- ✅ Existing Task model sufficient
- ✅ JSONB result field stores Qiskit counts directly
- ✅ Error messages structured for debugging
- ✅ State transitions unchanged
- ✅ Validation patterns defined

Ready for implementation with existing data model.
