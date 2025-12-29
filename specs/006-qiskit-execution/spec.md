# Feature Specification: Qiskit Circuit Execution in Workers

**Feature Branch**: `006-qiskit-execution`
**Created**: 2025-12-29
**Status**: Draft
**Input**: User description: "Consume queue, execute Qiskit, store results"

## Clarifications

### Session 2025-12-29

- Q: What should happen when a circuit execution exceeds the timeout limit? → A: No enforced timeout - rely on user to submit reasonably-sized circuits
- Q: How should the system handle measurement results that are too large to store (e.g., 20+ qubit circuits with sparse results)? → A: Don't enforce size restriction
- Q: What should happen if a worker starts but Qiskit is not available? → A: Worker exits with error code, preventing message consumption

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Execute Quantum Circuits with Real Results (Priority: P1)

When a developer submits a quantum circuit task, the worker processes the circuit using Qiskit's quantum simulator and returns actual measurement results that reflect the quantum state distribution. This replaces the current mock execution that always returns fixed 50/50 results.

**Why this priority**: This is the core value proposition of the quantum circuit execution system. Without real Qiskit execution, the system provides no actual utility beyond task queuing infrastructure. Users cannot validate circuit correctness or obtain meaningful quantum computation results.

**Independent Test**: Can be fully tested by submitting a known quantum circuit (e.g., Hadamard gate on single qubit) via POST /tasks, waiting for completion, then verifying GET /tasks/{id} returns measurement results that match expected quantum probability distributions (e.g., approximately 50% |0⟩ and 50% |1⟩ for H gate).

**Acceptance Scenarios**:

1. **Given** a worker receives a task message containing a valid OpenQASM 3 circuit, **When** the worker processes the task, **Then** the circuit is executed using Qiskit AerSimulator with the specified number of shots and measurement results are stored in the database
2. **Given** a simple single-qubit circuit with Hadamard gate, **When** execution completes, **Then** measurement results show approximately equal distribution between |0⟩ and |1⟩ states (within statistical variance)
3. **Given** a multi-qubit entangled circuit (e.g., Bell state), **When** execution completes, **Then** measurement results show expected correlations between qubits (e.g., only |00⟩ and |11⟩ for Bell state)
4. **Given** a task has been executed with Qiskit, **When** querying task status, **Then** the result contains actual measurement counts from quantum simulation (not mock data)

---

### User Story 2 - Handle Circuit Execution Errors Gracefully (Priority: P2)

When a worker attempts to execute an invalid or malformed quantum circuit, the system detects the error during Qiskit execution, transitions the task to failed status, and stores a descriptive error message that helps users understand what went wrong.

**Why this priority**: Error handling is essential for production readiness but secondary to basic execution functionality. Users need clear feedback when circuits fail, but this can be implemented after proving the happy path works.

**Independent Test**: Can be fully tested by submitting circuits with various error conditions (invalid gates, undefined qubits, syntax errors), then verifying tasks transition to "failed" status with specific error messages that identify the problem.

**Acceptance Scenarios**:

1. **Given** a worker receives a circuit with invalid OpenQASM 3 syntax, **When** Qiskit attempts to parse the circuit, **Then** the task status transitions to "failed" and error message contains the parse error details
2. **Given** a worker encounters a Qiskit runtime error during execution, **When** the error occurs, **Then** the task status transitions to "failed", error message is stored, and the worker acknowledges the message to remove it from queue
3. **Given** a circuit references undefined quantum registers, **When** Qiskit validates the circuit, **Then** the error is caught and task fails with descriptive error message indicating the undefined register

---

### User Story 3 - Configure Execution Parameters (Priority: P3)

When submitting a quantum circuit task, users can specify execution parameters such as number of measurement shots, and the worker respects these parameters when executing the circuit with Qiskit.

**Why this priority**: Configurable parameters improve flexibility but are not essential for initial functionality. Default parameters (e.g., 1024 shots) can serve most use cases initially, with parameter customization added as an enhancement.

**Independent Test**: Can be fully tested by submitting tasks with different shot counts specified in the request, then verifying the measurement results reflect the requested number of shots in the statistical sample size.

**Acceptance Scenarios**:

1. **Given** a task submission includes a shots parameter, **When** the worker executes the circuit, **Then** Qiskit runs the simulation with the specified number of shots
2. **Given** a task submission omits the shots parameter, **When** the worker executes the circuit, **Then** Qiskit uses the default shots value (1024)
3. **Given** a task specifies an invalid shots value (e.g., negative or zero), **When** validating the request, **Then** the API returns a validation error before queuing the task

---

### Edge Cases

- What happens when a circuit execution takes longer than expected (e.g., very large circuit)? Worker continues processing without enforced timeout; users are responsible for submitting circuits that complete in reasonable time
- How does the system handle circuits that consume excessive memory during simulation? Qiskit may raise memory errors; worker should catch these and transition task to failed status with appropriate error message
- What happens if Qiskit library is not properly installed or configured in the worker container? Worker validates Qiskit on startup and exits with non-zero error code if missing, preventing message consumption
- How does the system handle concurrent execution of multiple circuits by the same worker? Each worker processes one task at a time (prefetch_count=1), so concurrency is managed at the queue level across multiple workers
- What happens when measurement results contain very large state spaces (many qubits)? All measurement results are stored as JSONB in PostgreSQL without size restrictions; users are responsible for circuit complexity
- How does the system handle circuits with no measurement operations? Qiskit will execute the circuit but return empty measurement results; this should be stored as valid output (empty counts dictionary)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Workers MUST parse OpenQASM 3 circuit strings using Qiskit's QASM3 parser
- **FR-002**: Workers MUST execute quantum circuits using Qiskit AerSimulator backend
- **FR-003**: Workers MUST perform measurements with configurable shot count (default: 1024 shots)
- **FR-004**: Workers MUST store measurement results as counts dictionary in the task's result field
- **FR-005**: Workers MUST transition tasks to "failed" status when Qiskit execution raises exceptions
- **FR-006**: Workers MUST capture and store Qiskit error messages in the task's error_message field when execution fails
- **FR-007**: Workers MUST validate that Qiskit library is available on startup and exit with non-zero error code if missing or non-functional
- **FR-008**: System MUST support OpenQASM 3 circuit syntax as the input format
- **FR-009**: Workers MUST handle Qiskit import errors, parse errors, and runtime errors separately with appropriate error messages
- **FR-010**: Workers MUST acknowledge queue messages only after successfully storing execution results or error states in the database

### Key Entities

- **Quantum Circuit**: Represents the quantum program to execute, encoded as OpenQASM 3 text. Key attributes include circuit definition (text), number of qubits (derived), gate operations (derived), measurement operations (derived).

- **Measurement Result**: Represents the output of quantum circuit execution, containing counts of each measured quantum state. Key attributes include basis state (bitstring like "00", "01", "10", "11"), count (number of times this state was measured), total shots (sum of all counts).

- **Execution Configuration**: Represents parameters controlling circuit execution. Key attributes include shots (number of measurements), backend type (simulator vs real hardware - simulator only for this feature), noise model (none for initial implementation).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Submitted quantum circuits execute and return measurement results that statistically match expected quantum probability distributions (verified by chi-squared test on known circuits)
- **SC-002**: Circuit execution completes within 30 seconds for circuits with up to 10 qubits under typical workloads
- **SC-003**: Invalid circuits are detected and fail with descriptive error messages within 5 seconds of worker processing starting
- **SC-004**: 95% of valid circuit submissions complete successfully without worker crashes or data corruption
- **SC-005**: Measurement results for deterministic circuits (e.g., no gates, identity operations) show 100% in expected basis state
- **SC-006**: System handles at least 100 circuit executions per minute across three workers without degradation

## Scope & Boundaries *(mandatory)*

### In Scope

- Integration of Qiskit library into worker containers
- Parsing OpenQASM 3 circuit syntax using Qiskit
- Execution of circuits using AerSimulator (statevector or qasm simulator)
- Measurement result collection and storage
- Configurable shot count parameter
- Error handling for Qiskit parse errors, execution errors, and import errors
- Validation that Qiskit is properly installed on worker startup
- Removal of mock execution logic currently in worker.py
- Testing with standard quantum circuits (H gate, CNOT, Bell states)

### Out of Scope

- Real quantum hardware backends (IBM Quantum, AWS Braket, etc.) - simulator only
- Noise models or error mitigation techniques
- Circuit optimization or transpilation beyond Qiskit defaults
- Custom gate definitions or pulse-level control
- Quantum circuit visualization or analysis tools
- Support for circuit formats other than OpenQASM 3 (e.g., QASM 2, Quil, Cirq)
- Advanced execution parameters (optimization level, basis gates, coupling map)
- Caching or memoization of circuit execution results
- Partial circuit execution or checkpointing for long-running circuits
- Multi-backend execution or backend selection based on circuit characteristics

**Rationale for exclusions**: This feature focuses on establishing the core execution pipeline using Qiskit's simulator. Real hardware integration, advanced features, and alternative circuit formats can be added as separate enhancements once the foundational execution is proven. Noise models and optimization are valuable but not essential for initial functionality.

## Dependencies & Assumptions *(mandatory)*

### Dependencies

- **Qiskit Library**: Qiskit must be installed in worker containers (specific version to be determined during implementation)
- **Existing Worker Infrastructure**: Feature 003-persistence-message-queue provides the worker framework, queue consumption, and database updates
- **Existing API**: Feature 002-api-server-docker provides task submission endpoint
- **OpenQASM 3 Support**: Qiskit must support OpenQASM 3 parsing (available in Qiskit >= 0.45.0)

### Assumptions

- **Circuit Size**: Most submitted circuits will have fewer than 15 qubits, which AerSimulator can handle efficiently on standard hardware
- **Execution Time**: Typical circuit execution completes within 10 seconds; no enforced timeout - users submit circuits that complete in reasonable time
- **Memory Availability**: Worker containers have sufficient memory (at least 2GB) to simulate circuits up to 12-15 qubits
- **Input Validation**: API layer handles basic input validation (circuit is not empty, is valid string), workers focus on Qiskit-specific validation
- **Shot Count Range**: Valid shot counts range from 1 to 100,000; API validates this range before queuing
- **Error Handling Strategy**: Workers catch all Qiskit exceptions and convert them to failed task states rather than allowing worker crashes
- **Simulator Backend**: AerSimulator with default settings (statevector method for small circuits, qasm_simulator for larger) is sufficient
- **Result Storage**: PostgreSQL JSONB field stores all measurement results without size restrictions; sparse representation used for efficiency
- **Concurrent Workers**: Multiple workers can execute different circuits concurrently without interference
- **Qiskit Version**: Workers will use the latest stable Qiskit release available at implementation time (likely 0.45.x or 1.x)

## Non-Functional Requirements *(mandatory)*

### Observability

- **Execution Logging**: Each circuit execution logged with task ID, circuit summary (qubit count, gate count), execution time, and result summary
- **Error Logging**: Qiskit exceptions logged with full stack trace, circuit that caused error (truncated if very long), and task ID
- **Performance Metrics**: Log execution time for each circuit to identify performance outliers
- **Qiskit Version**: Log Qiskit library version on worker startup for debugging version-related issues

### Fault Tolerance

- **Exception Handling**: All Qiskit operations wrapped in try-except blocks to prevent worker crashes
- **Graceful Degradation**: If Qiskit execution fails, task transitions to failed state and worker continues processing other tasks
- **Resource Cleanup**: Circuit objects and simulation results properly disposed after execution to prevent memory leaks
- **Validation on Startup**: Worker validates Qiskit is importable and functional on startup; exits with non-zero error code if validation fails, preventing message consumption

### Scalability

- **Stateless Execution**: Each circuit execution is independent; workers maintain no state between tasks
- **Memory Management**: Large circuits may require more memory; workers should handle memory errors gracefully rather than crashing
- **Horizontal Scaling**: Multiple workers can execute circuits concurrently without coordination

## Approval *(optional)*

**Stakeholders:**
- Development Team Lead: Pending Review
- Quantum Computing Domain Expert: Pending Review (validation of circuit execution approach)
- DevOps/Infrastructure: Pending Review (Qiskit dependencies in containers)

**Notes:** This feature transforms the system from a task queuing demo to a functional quantum circuit execution platform. It builds on the infrastructure from features 002 and 003.

---

## Document History

| Version | Date       | Changes                  | Author |
|---------|------------|--------------------------|--------|
| 1.0     | 2025-12-29 | Initial specification    | Claude |
