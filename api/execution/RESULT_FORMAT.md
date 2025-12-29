# Measurement Result JSONB Format

## Overview

This document defines the JSON/JSONB structure for quantum circuit measurement results stored in the `tasks.result` database field.

## Format Specification

### Structure
Results are stored as a JSON object mapping basis states (bitstrings) to measurement counts.

```json
{
  "00": 512,
  "01": 0,
  "10": 0,
  "11": 512
}
```

### Field Specifications

**Keys** (Basis States):
- Format: Bitstrings containing only '0' and '1' characters
- Length: Number of measured qubits (all keys must have same length)
- Endianness: Little-endian (rightmost bit = qubit 0)
- Example: `"01"` means qubit 0 in state |1⟩, qubit 1 in state |0⟩

**Values** (Counts):
- Type: Non-negative integers
- Meaning: Number of times this basis state was measured
- Range: 0 to total shots
- Sum: All values sum to total shots executed

### Sparse Representation

Only basis states with count > 0 need to be included.

**Example**: Deterministic circuit (all measurements → |0⟩)
```json
{
  "0": 1024
}
```

States with 0 counts may be omitted entirely.

## Examples

### Single-Qubit Hadamard Gate
50/50 superposition between |0⟩ and |1⟩:
```json
{
  "0": 512,
  "1": 512
}
```

### Two-Qubit Bell State
Entanglement creates only |00⟩ and |11⟩ states:
```json
{
  "00": 501,
  "11": 523
}
```
Note: No "01" or "10" states appear (entanglement signature).

### Deterministic Circuit
No gates applied, always measures |0⟩:
```json
{
  "0": 1024
}
```

### Circuit With No Measurements
Valid but empty result:
```json
{}
```

## Qiskit Integration

This format is **directly compatible** with Qiskit's `result.get_counts()` output:

```python
from qiskit import qasm3
from qiskit_aer import AerSimulator

circuit = qasm3.loads("OPENQASM 3; qubit q; h q; measure q;")
simulator = AerSimulator()
job = simulator.run(circuit, shots=1024)
counts = job.result().get_counts()

# counts is already in correct format for database storage:
# {"0": 512, "1": 512}

# Store directly in PostgreSQL JSONB field
task.result = counts  # SQLAlchemy handles dict → JSONB conversion
```

## Validation

### Valid Result Checks
- All keys are strings containing only '0' and '1'
- All keys have same length (same number of qubits)
- All values are non-negative integers
- Sum of values equals requested shots (within rounding tolerance)

### Example Validation Function
```python
def validate_counts(counts: dict) -> bool:
    """Validate Qiskit measurement counts."""
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

## Storage Considerations

### PostgreSQL JSONB Performance
- Sparse dictionaries stored efficiently
- Typical circuit (≤15 qubits, sparse results): <1KB
- Large circuits (20+ qubits, many outcomes): Could reach MB scale (rare)
- No enforced size limit (user responsibility for circuit complexity)

### Database Schema
No schema changes required. Existing `tasks.result` JSONB field is sufficient:

```sql
-- Existing column definition (no changes)
result JSONB NULL
```

## Source

Based on:
- Qiskit 1.0+ `result.get_counts()` output format
- `/Users/bzpysmn/work/classiq/specs/006-qiskit-execution/data-model.md`
- OpenQASM 3 measurement conventions
