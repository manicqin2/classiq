# Quickstart: Qiskit Circuit Execution

**Feature**: 006-qiskit-execution
**Date**: 2025-12-29

## Overview

This guide helps developers get started with Qiskit integration for quantum circuit execution. Follow these steps to set up your development environment, run workers with Qiskit, and test with real quantum circuits.

---

## Prerequisites

- Python 3.11+ installed
- Docker and Docker Compose installed
- Existing project infrastructure running (postgres, rabbitmq, api)
- Access to project repository

---

## Installation

### 1. Install Qiskit Locally

For local development and testing outside Docker:

```bash
# Create/activate virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Qiskit
pip install 'qiskit>=1.0,<2.0' 'qiskit-aer>=0.13.0'

# Verify installation
python -c "import qiskit; print(f'Qiskit {qiskit.__version__}')"
```

Expected output:
```
Qiskit 1.0.x
```

### 2. Update Docker Configuration

Add Qiskit to worker container dependencies:

**File**: `api/requirements.txt`
```txt
# Existing dependencies
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy[asyncio]==2.0.23
asyncpg==0.29.0
aio-pika==9.3.1
structlog==23.2.0

# Add Qiskit (new)
qiskit>=1.0,<2.0
qiskit-aer>=0.13.0
```

**Rebuild worker image**:
```bash
docker-compose build worker-1 worker-2 worker-3
```

---

## Running Workers with Qiskit

### Start All Services

```bash
# Start entire stack
docker-compose up -d

# Verify all services healthy
docker-compose ps
```

Expected output:
```
NAME               STATUS
quantum-api        Up (healthy)
quantum-postgres   Up (healthy)
quantum-rabbitmq   Up (healthy)
quantum-worker-1   Up (healthy)
quantum-worker-2   Up (healthy)
quantum-worker-3   Up (healthy)
```

### Verify Qiskit in Workers

Check worker logs for Qiskit validation:

```bash
docker-compose logs worker-1 | grep -i qiskit
```

Expected output:
```
INFO: Qiskit validation successful: version 1.0.0
INFO: Qiskit AerSimulator backend available
```

If you see errors:
```bash
# Check for import errors
docker-compose logs worker-1 | grep -i error

# Common issue: requirements.txt not updated
# Solution: Rebuild worker images
docker-compose build worker-1 worker-2 worker-3
docker-compose up -d
```

---

## Testing with Sample Circuits

### 1. Simple Single-Qubit Circuit (Hadamard Gate)

**Circuit**: Places qubit in superposition (50/50 probability)

```bash
# Submit task
curl -X POST http://localhost:8001/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "circuit": "OPENQASM 3; qubit q; h q; measure q;"
  }'
```

Response:
```json
{
  "task_id": "abc-123...",
  "message": "Task submitted successfully.",
  "submitted_at": "2025-12-29T10:00:00Z",
  "correlation_id": "..."
}
```

**Wait for completion** (typically <1 second):
```bash
# Query task status
curl http://localhost:8001/tasks/abc-123...
```

Expected result:
```json
{
  "task_id": "abc-123...",
  "status": "completed",
  "result": {
    "0": 512,  # Approximately 50%
    "1": 512   # Approximately 50%
  },
  "status_history": [
    {"status": "pending", "transitioned_at": "..."},
    {"status": "processing", "transitioned_at": "..."},
    {"status": "completed", "transitioned_at": "..."}
  ]
}
```

**Verification**: Result shows ~50/50 distribution (within statistical variance)

### 2. Bell State (Two-Qubit Entanglement)

**Circuit**: Creates entangled qubits (only |00⟩ and |11⟩ states)

```bash
curl -X POST http://localhost:8001/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "circuit": "OPENQASM 3; qubit[2] q; h q[0]; cnot q[0], q[1]; measure q;"
  }'
```

Expected result:
```json
{
  "status": "completed",
  "result": {
    "00": 501,  # Approximately 50%
    "11": 523   # Approximately 50%
    // Note: No "01" or "10" (entanglement works!)
  }
}
```

**Verification**: Only |00⟩ and |11⟩ states appear (no |01⟩ or |10⟩)

### 3. Deterministic Circuit (No Gates)

**Circuit**: Identity operation, always measures |0⟩

```bash
curl -X POST http://localhost:8001/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "circuit": "OPENQASM 3; qubit q; measure q;"
  }'
```

Expected result:
```json
{
  "status": "completed",
  "result": {
    "0": 1024  # 100% in |0⟩ state
  }
}
```

**Verification**: All shots measure |0⟩ (deterministic)

### 4. Custom Shot Count

**Circuit**: Hadamard with 100 shots instead of default 1024

```bash
curl -X POST http://localhost:8001/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "circuit": "OPENQASM 3; qubit q; h q; measure q;",
    "shots": 100
  }'
```

Expected result:
```json
{
  "status": "completed",
  "result": {
    "0": 48,  # Approximately 50 (out of 100)
    "1": 52   # Sum = 100 shots
  }
}
```

---

## Error Testing

### Invalid Circuit Syntax

```bash
curl -X POST http://localhost:8001/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "circuit": "invalid qasm syntax here"
  }'
```

Expected result:
```json
{
  "status": "failed",
  "error_message": "Circuit parse error: QASM3ImporterError: ..."
}
```

### Undefined Gate

```bash
curl -X POST http://localhost:8001/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "circuit": "OPENQASM 3; qubit q; undefined_gate q;"
  }'
```

Expected result:
```json
{
  "status": "failed",
  "error_message": "Circuit parse error: QASM3ImporterError: undefined gate 'undefined_gate'"
}
```

---

## Troubleshooting

### Worker Not Starting

**Symptom**: Workers show unhealthy or exit immediately

**Solution**:
```bash
# Check worker logs
docker-compose logs worker-1

# Look for Qiskit import errors
docker-compose logs worker-1 | grep -i "importerror\|fatal"

# Common causes:
# 1. Qiskit not in requirements.txt → Add and rebuild
# 2. Python version mismatch → Verify Dockerfile uses Python 3.11
# 3. Missing dependencies → Check aio-pika, structlog installed
```

### Slow Execution

**Symptom**: Circuits take longer than expected

**Investigation**:
```bash
# Check worker logs for execution time
docker-compose logs worker-1 | grep "Execution completed"

# Example: INFO: Execution completed in 2.34s
```

**Common causes**:
- Large circuit (many qubits) → Expected, no timeout enforced
- Many shots (100,000) → Increase will slow down simulation
- Worker container CPU/memory limits → Check docker-compose.yml resources

### Incorrect Results

**Symptom**: Results don't match expected probability distribution

**Debugging**:
```python
# Local test with known circuit
from qiskit import qasm3
from qiskit_aer import AerSimulator

circuit = qasm3.loads("OPENQASM 3; qubit q; h q; measure q;")
simulator = AerSimulator()
job = simulator.run(circuit, shots=10000)  # More shots = more accuracy
counts = job.result().get_counts()
print(counts)
# Expected: ~{"0": 5000, "1": 5000}
```

**Verification**:
- Small shot counts have high variance (use 1000+ shots)
- Check circuit definition matches expectation
- Verify OpenQASM 3 syntax (not QASM 2)

### Memory Errors

**Symptom**: Worker logs "MemoryError" or "AerError: memory allocation failed"

**Causes**:
- Circuit too large (>15 qubits on 2GB worker)
- Too many shots for large circuit

**Solutions**:
```bash
# Option 1: Increase worker memory (docker-compose.yml)
worker-1:
  deploy:
    resources:
      limits:
        memory: 4G  # Increase from 2G

# Option 2: User submits smaller circuits (design decision)
# Option 3: Reduce shots for large circuits (user choice)
```

---

## Development Workflow

### Local Development (Without Docker)

```bash
# Activate venv
source venv/bin/activate

# Run worker locally
cd api
python worker.py
```

**Note**: Requires postgres and rabbitmq running (via docker-compose or local install)

### Running Tests

```bash
# Unit tests
pytest tests/unit/test_qiskit_executor.py -v

# Integration tests (requires services running)
pytest tests/integration/test_worker_qiskit.py -v

# All tests
pytest tests/ -v
```

### Adding New Test Circuits

Create file `tests/fixtures/circuits.py`:
```python
# Test circuit definitions
HADAMARD_SINGLE = "OPENQASM 3; qubit q; h q; measure q;"
BELL_STATE = "OPENQASM 3; qubit[2] q; h q[0]; cnot q[0], q[1]; measure q;"
DETERMINISTIC = "OPENQASM 3; qubit q; measure q;"
```

Use in tests:
```python
from tests.fixtures.circuits import HADAMARD_SINGLE

def test_hadamard_circuit():
    result = execute_circuit(HADAMARD_SINGLE, shots=1024)
    assert result.status == "completed"
    assert "0" in result.result
    assert "1" in result.result
```

---

## Verifying Results Match Expected Distributions

### Chi-Squared Test (Statistical Validation)

```python
from scipy.stats import chisquare

# Expected: 50/50 distribution for H gate
observed = [512, 512]  # From result
expected = [512, 512]  # Theoretical

chi2, p_value = chisquare(observed, expected)
print(f"Chi-squared: {chi2}, p-value: {p_value}")

# p_value > 0.05 → result statistically matches expectation
# p_value < 0.05 → result differs significantly (rerun with more shots)
```

### Tolerance Checking

```python
def verify_hadamard(result, shots=1024, tolerance=0.1):
    """Verify H gate produces ~50/50 distribution"""
    count_0 = result.get("0", 0)
    count_1 = result.get("1", 0)

    expected_each = shots / 2
    assert abs(count_0 - expected_each) < tolerance * shots
    assert abs(count_1 - expected_each) < tolerance * shots
```

---

## Next Steps

1. ✅ Install Qiskit and verify installation
2. ✅ Test with sample circuits (H gate, Bell state)
3. ✅ Review worker logs for successful execution
4. ✅ Verify results match expected distributions
5. ⏭️ Proceed with implementation tasks
6. ⏭️ Write unit and integration tests
7. ⏭️ Update documentation

---

## Resources

- **Qiskit Documentation**: https://qiskit.org/documentation/
- **OpenQASM 3 Spec**: https://openqasm.com/
- **AerSimulator Guide**: https://qiskit.org/ecosystem/aer/tutorials/1_aersimulator.html
- **Project Architecture**: [ARCHITECTURE.md](../../ARCHITECTURE.md)

---

## Support

If you encounter issues:
1. Check worker logs: `docker-compose logs worker-1`
2. Verify Qiskit version: `docker-compose exec worker-1 python -c "import qiskit; print(qiskit.__version__)"`
3. Review this quickstart guide
4. Check existing test circuits in `tests/fixtures/`
