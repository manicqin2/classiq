# Research: Qiskit Circuit Execution Integration

**Feature**: 006-qiskit-execution
**Date**: 2025-12-29
**Status**: Complete

## Overview

This document captures research findings for integrating Qiskit into worker processes to execute quantum circuits. All technical decisions needed for implementation are documented below.

---

## 1. Qiskit Version Selection

### Decision
Use **Qiskit 1.0+** (latest stable 1.x release)

### Rationale
- Qiskit 1.0 was released in February 2024 as a major stable release
- Provides mature OpenQASM 3 support via `qiskit.qasm3` module
- Better performance and stability compared to 0.45.x
- Active maintenance and long-term support path
- Cleaner API design after 1.0 refactoring
- Production-ready for new projects as of late 2024/2025

### Alternatives Considered
- **Qiskit 0.45.x**: Has OpenQASM 3 support but considered legacy; 1.x is the recommended path
- **Qiskit 2.0**: Not yet released; 1.x is current stable

### Implementation
```python
# requirements.txt
qiskit>=1.0,<2.0
qiskit-aer>=0.13.0  # Simulator backend
```

---

## 2. OpenQASM 3 Parser

### Decision
Use `qiskit.qasm3.loads()` for parsing OpenQASM 3 strings

### Rationale
- Official Qiskit API for OpenQASM 3 parsing
- Returns `QuantumCircuit` object ready for execution
- Handles syntax validation and error reporting
- Supports full OpenQASM 3 specification

### Alternatives Considered
- **qiskit.QuantumCircuit.from_qasm_str()**: Only supports QASM 2.0, not QASM 3
- **Manual parsing**: Unnecessarily complex, error-prone

### Implementation
```python
from qiskit import qasm3

# Parse OpenQASM 3 string to circuit
circuit_string = "OPENQASM 3; qubit q; h q; measure q;"
circuit = qasm3.loads(circuit_string)

# Raises qiskit.qasm3.QASM3ImporterError on parse errors
```

### Error Handling
```python
from qiskit.qasm3 import QASM3ImporterError

try:
    circuit = qasm3.loads(circuit_string)
except QASM3ImporterError as e:
    # Syntax errors, undefined gates, invalid structure
    error_message = f"OpenQASM 3 parse error: {str(e)}"
```

---

## 3. AerSimulator Configuration

### Decision
Use `AerSimulator()` with default configuration for automatic method selection

### Rationale
- AerSimulator automatically selects optimal simulation method based on circuit size
- For small circuits (<15 qubits), uses statevector method (faster, exact)
- For larger circuits or when statevector exceeds memory, automatically switches to qasm_simulator
- No manual configuration needed for typical use cases
- Handles memory constraints gracefully

### Alternatives Considered
- **Explicit statevector simulator**: Less flexible, requires manual switching for larger circuits
- **QASM simulator only**: Slower for small circuits where statevector is efficient
- **GPU simulator**: Not needed for initial implementation; adds complexity

### Implementation
```python
from qiskit_aer import AerSimulator

# Create simulator with defaults (auto method selection)
simulator = AerSimulator()

# Execute circuit
job = simulator.run(circuit, shots=1024)
result = job.result()
counts = result.get_counts()
```

### Performance Characteristics
- Circuits ≤10 qubits: Statevector method, <1 second typical
- Circuits 11-15 qubits: Statevector or sampling based on depth
- Circuits >15 qubits: Automatic fallback to sampling methods
- Memory usage: ~2^n complex numbers for statevector (n = qubits)

---

## 4. Error Handling Patterns

### Decision
Implement three-tier exception handling: Import, Parse, Runtime

### Exception Hierarchy

**Import Errors**
```python
try:
    from qiskit import qasm3
    from qiskit_aer import AerSimulator
except ImportError as e:
    # Qiskit not installed or incompatible version
    # Worker should exit with error code
    sys.exit(1)
```

**Parse Errors**
```python
from qiskit.qasm3 import QASM3ImporterError

try:
    circuit = qasm3.loads(circuit_string)
except QASM3ImporterError as e:
    # Syntax errors, undefined gates/qubits, invalid QASM 3
    task.status = "failed"
    task.error_message = f"Circuit parse error: {str(e)}"
```

**Runtime Errors**
```python
from qiskit_aer import AerError

try:
    job = simulator.run(circuit, shots=shots)
    result = job.result()
except AerError as e:
    # Execution errors: memory exceeded, invalid circuit operations
    task.status = "failed"
    task.error_message = f"Execution error: {str(e)}"
except Exception as e:
    # Catch-all for unexpected errors
    task.status = "failed"
    task.error_message = f"Unexpected error: {type(e).__name__}: {str(e)}"
```

### Common Error Scenarios
- **QASM3ImporterError**: Invalid syntax, undefined gates, type errors
- **AerError**: Memory exhausted, invalid measurements, backend issues
- **QiskitError**: General Qiskit framework errors
- **MemoryError**: Python memory allocation failure (very large circuits)

---

## 5. Result Format

### Decision
Store Qiskit counts dictionary directly as JSONB (already compatible format)

### Result Structure
```python
# Qiskit returns counts as dict[str, int]
result = job.result()
counts = result.get_counts()

# Example for single qubit after H gate:
# counts = {"0": 512, "1": 512}

# Example for Bell state (2 qubits):
# counts = {"00": 501, "11": 523}

# Store directly in PostgreSQL JSONB field
task.result = counts  # SQLAlchemy handles dict → JSONB conversion
```

### Format Specifications
- **Keys**: Bitstrings (e.g., "00", "01", "10", "11" for 2 qubits)
- **Values**: Integer counts (number of times that state was measured)
- **Total shots**: Sum of all values equals requested shots
- **Sparse**: Only measured states appear (unmeasured states omitted)
- **Endianness**: Qiskit uses little-endian (rightmost bit is qubit 0)

### Empty Results
```python
# Circuit with no measurements
counts = {}  # Empty dict, store as valid result
```

---

## 6. Memory Management

### Decision
No explicit cleanup required; rely on Python garbage collection

### Rationale
- Qiskit circuits and results are regular Python objects
- Python's reference counting handles cleanup automatically
- No known memory leaks in Qiskit 1.x for typical usage
- Worker processes one task at a time, so no long-lived object accumulation

### Best Practices
```python
# Pattern: create, use, let GC clean up
def execute_circuit(circuit_string: str, shots: int):
    circuit = qasm3.loads(circuit_string)
    simulator = AerSimulator()
    job = simulator.run(circuit, shots=shots)
    result = job.result()
    counts = result.get_counts()
    return counts
    # circuit, simulator, job, result go out of scope → GC'd
```

### Monitoring Recommendations
- Log worker memory usage periodically
- If memory growth observed, investigate circuit/result retention
- Worker restart policies can handle any slow leaks

### Alternatives Considered
- **Explicit del statements**: Unnecessary with proper scoping
- **Manual garbage collection**: Adds overhead, not needed for single-task processing
- **Process pooling**: Over-engineering for initial implementation

---

## 7. Additional Findings

### Startup Validation

```python
# Validate Qiskit availability on worker startup
import sys

try:
    from qiskit import qasm3
    from qiskit_aer import AerSimulator

    # Test basic functionality
    test_circuit = qasm3.loads("OPENQASM 3; qubit q;")
    simulator = AerSimulator()

    # Log version for debugging
    import qiskit
    print(f"Qiskit version: {qiskit.__version__}")

except Exception as e:
    print(f"FATAL: Qiskit validation failed: {e}", file=sys.stderr)
    sys.exit(1)
```

### Shot Count Configuration

```python
# Pass shots parameter to simulator.run()
job = simulator.run(circuit, shots=1024)

# Qiskit validates shots > 0
# Invalid shots raises ValueError before execution
```

### Logging Recommendations

```python
import logging

logger = logging.getLogger(__name__)

# Log circuit characteristics
logger.info(f"Executing circuit: {circuit.num_qubits} qubits, "
           f"{circuit.depth()} depth, {shots} shots")

# Log execution time
start = time.time()
result = job.result()
duration = time.time() - start
logger.info(f"Execution completed in {duration:.2f}s")
```

---

## Summary

All research topics resolved:

1. ✅ **Version**: Qiskit 1.0+ (stable, production-ready)
2. ✅ **Parser**: `qiskit.qasm3.loads()` for OpenQASM 3
3. ✅ **Simulator**: `AerSimulator()` with automatic method selection
4. ✅ **Errors**: Three-tier handling (Import/Parse/Runtime)
5. ✅ **Results**: Counts dict directly to JSONB (compatible)
6. ✅ **Memory**: Standard Python GC sufficient, no explicit cleanup

No unresolved technical uncertainties. Ready for Phase 1 design artifacts.
