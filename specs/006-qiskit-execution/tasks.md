# Tasks: Qiskit Circuit Execution in Workers

**Input**: Design documents from `/specs/006-qiskit-execution/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/worker-behavior.md, quickstart.md

**Tests**: Not explicitly requested in specification - focusing on implementation tasks

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Per plan.md - modifying existing `api/` directory structure:
- Worker code: `api/worker.py`, `api/src/execution/`
- Tests: `api/tests/unit/`, `api/tests/integration/`
- Configuration: `api/requirements.txt`, `Dockerfile`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Qiskit integration and basic infrastructure setup

- [ ] T001 Add Qiskit dependencies to api/requirements.txt (qiskit>=1.0,<2.0 and qiskit-aer>=0.13.0)
- [ ] T002 [P] Create api/src/execution/__init__.py module initialization
- [ ] T003 [P] Create api/tests/unit/execution/ test directory structure
- [ ] T004 [P] Create api/tests/integration/ directory if not exists
- [ ] T005 Rebuild Docker images with Qiskit dependencies (docker-compose build worker-1 worker-2 worker-3)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core Qiskit integration that MUST be complete before user stories

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T006 Implement Qiskit startup validation in api/src/execution/qiskit_validator.py with exit-on-failure behavior
- [ ] T007 Add Qiskit version logging on worker startup in api/worker.py
- [ ] T008 Document measurement result JSONB format based on data-model.md

**Checkpoint**: Qiskit validated on worker startup - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Execute Quantum Circuits with Real Results (Priority: P1) 🎯 MVP

**Goal**: Replace mock execution with real Qiskit simulation, enabling workers to parse OpenQASM 3 circuits, execute using AerSimulator, and store actual measurement results

**Independent Test**: Submit Hadamard gate circuit via POST /tasks, verify GET /tasks/{id} returns approximately 50/50 distribution between |0⟩ and |1⟩ states

### Implementation for User Story 1

- [ ] T009 [P] [US1] Create QiskitExecutor class in api/src/execution/qiskit_executor.py with circuit parsing method using qasm3.loads()
- [ ] T010 [P] [US1] Implement circuit execution method in api/src/execution/qiskit_executor.py using AerSimulator with configurable shots
- [ ] T011 [P] [US1] Create ResultFormatter class in api/src/execution/result_formatter.py to convert Qiskit counts dict to JSONB format
- [ ] T012 [US1] Integrate QiskitExecutor into worker task processing in api/worker.py replacing mock execution (depends on T009, T010)
- [ ] T013 [US1] Add circuit execution logging in api/src/execution/qiskit_executor.py (log qubit count, gate count, shots, execution time)
- [ ] T014 [US1] Store Qiskit measurement results in task.result field via existing repository pattern in api/worker.py
- [ ] T015 [US1] Remove mock execution logic from api/worker.py (lines implementing fixed 50/50 results)

**Checkpoint**: At this point, User Story 1 should be fully functional - workers execute real circuits and store actual results

---

## Phase 4: User Story 2 - Handle Circuit Execution Errors Gracefully (Priority: P2)

**Goal**: Detect and handle Qiskit parse errors, runtime errors, and memory errors, transitioning tasks to failed status with descriptive error messages

**Independent Test**: Submit invalid circuit syntax, verify task transitions to "failed" with parse error details in error_message field

### Implementation for User Story 2

- [ ] T016 [P] [US2] Implement QASM3ImporterError handling in api/src/execution/qiskit_executor.py for parse errors
- [ ] T017 [P] [US2] Implement AerError handling in api/src/execution/qiskit_executor.py for runtime/memory errors
- [ ] T018 [P] [US2] Implement catch-all exception handling in api/src/execution/qiskit_executor.py for unexpected errors
- [ ] T019 [US2] Add error message formatting in api/src/execution/result_formatter.py with error category prefixes (depends on T016, T017, T018)
- [ ] T020 [US2] Integrate error handling in api/worker.py to transition task to failed status and store error_message
- [ ] T021 [US2] Add error logging with full stack traces in api/src/execution/qiskit_executor.py for all error categories
- [ ] T022 [US2] Ensure queue message acknowledged after error handling (worker continues processing) in api/worker.py

**Checkpoint**: At this point, User Stories 1 AND 2 should both work - valid circuits succeed, invalid circuits fail gracefully

---

## Phase 5: User Story 3 - Configure Execution Parameters (Priority: P3)

**Goal**: Support configurable shot count parameter from task submission, respecting user-specified shots or using default 1024

**Independent Test**: Submit task with shots=100, verify measurement results sum to 100; submit without shots parameter, verify sum to 1024

### Implementation for User Story 3

- [ ] T023 [P] [US3] Add shots parameter extraction from task in api/worker.py with default value 1024
- [ ] T024 [US3] Pass shots parameter to QiskitExecutor.execute() method in api/src/execution/qiskit_executor.py
- [ ] T025 [US3] Update circuit execution to use configurable shots in simulator.run() call in api/src/execution/qiskit_executor.py
- [ ] T026 [US3] Add shots validation in API layer (api/models.py) to ensure range 1-100,000 before queuing
- [ ] T027 [US3] Log configured shots value in execution logging in api/src/execution/qiskit_executor.py

**Checkpoint**: All user stories should now be independently functional - circuit execution with custom parameters works

---

## Phase 6: Integration & Validation

**Purpose**: End-to-end testing and validation using quickstart.md test scenarios

- [ ] T028 [P] Test Hadamard circuit (single qubit superposition) per quickstart.md section "Simple Single-Qubit Circuit"
- [ ] T029 [P] Test Bell state circuit (two-qubit entanglement) per quickstart.md section "Bell State"
- [ ] T030 [P] Test deterministic circuit (no gates, always |0⟩) per quickstart.md section "Deterministic Circuit"
- [ ] T031 [P] Test custom shot count (100 shots) per quickstart.md section "Custom Shot Count"
- [ ] T032 [P] Test invalid circuit syntax error handling per quickstart.md section "Invalid Circuit Syntax"
- [ ] T033 [P] Test undefined gate error handling per quickstart.md section "Undefined Gate"
- [ ] T034 Verify worker health checks pass for all three workers (docker-compose ps shows all healthy)
- [ ] T035 Verify Qiskit version logged on worker startup (check docker-compose logs worker-1)
- [ ] T036 Run performance test: submit 20 tasks concurrently, verify all complete without errors
- [ ] T037 Validate results match expected probability distributions using statistical tests (chi-squared per research.md)

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, cleanup, and final validation

- [ ] T038 [P] Update ARCHITECTURE.md if exists to document Qiskit integration
- [ ] T039 [P] Update README.md with Qiskit dependency installation instructions
- [ ] T040 [P] Create test fixtures file api/tests/fixtures/circuits.py with sample OpenQASM 3 circuits
- [ ] T041 Code cleanup: Remove any commented-out mock execution code from api/worker.py
- [ ] T042 Add inline documentation for QiskitExecutor and ResultFormatter classes
- [ ] T043 Run full quickstart.md validation workflow end-to-end
- [ ] T044 Verify worker-1, worker-2, worker-3 all execute circuits successfully (load balancing check)
- [ ] T045 Performance validation: verify 10-qubit circuits complete within 30 seconds per spec SC-002

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup (T001-T005) completion - BLOCKS all user stories
- **User Stories (Phases 3-5)**: All depend on Foundational phase completion
  - User Story 1 (P1): Can start after Foundational - No dependencies on other stories
  - User Story 2 (P2): Can start after Foundational - Enhances US1 error handling
  - User Story 3 (P3): Can start after Foundational - Enhances US1 configuration
- **Integration (Phase 6)**: Depends on all user stories being complete
- **Polish (Phase 7)**: Depends on Integration validation

### User Story Dependencies

- **User Story 1 (P1)**: Independent - basic circuit execution
- **User Story 2 (P2)**: Builds on US1 (adds error handling to execution flow)
- **User Story 3 (P3)**: Builds on US1 (adds parameter configuration to execution)

**Recommended Order**: US1 → US2 → US3 (enables incremental delivery of working features)

### Within Each User Story

**User Story 1**:
- T009, T010, T011 can run in parallel (different classes/files)
- T012 depends on T009, T010 (integration requires executor ready)
- T013, T014, T015 sequential after T012 (worker integration complete)

**User Story 2**:
- T016, T017, T018 can run in parallel (different error types)
- T019 depends on T016-T018 (formatting uses error types)
- T020, T021, T022 sequential (worker integration)

**User Story 3**:
- T023, T024, T025, T026, T027 mostly sequential (parameter flow through layers)
- T023 and T026 can run in parallel (API vs worker changes)

### Parallel Opportunities

**Phase 1 (Setup)**:
- T002, T003, T004 can run in parallel (different directories)
- T001 and T005 sequential (dependency update → rebuild)

**Phase 2 (Foundational)**:
- T006, T007, T008 can run in parallel

**Phase 6 (Integration)**:
- T028-T033 can all run in parallel (independent test scenarios)
- T034-T037 sequential (validation progression)

**Phase 7 (Polish)**:
- T038, T039, T040 can run in parallel (different documentation files)
- T041, T042 can run in parallel (different cleanup tasks)

---

## Parallel Example: User Story 1

```bash
# Step 1: Launch all independent implementation tasks together:
Task T009: "Create QiskitExecutor class in api/src/execution/qiskit_executor.py"
Task T010: "Implement circuit execution method in api/src/execution/qiskit_executor.py"
Task T011: "Create ResultFormatter class in api/src/execution/result_formatter.py"

# Step 2: After T009 and T010 complete, integrate:
Task T012: "Integrate QiskitExecutor into worker task processing in api/worker.py"

# Step 3: After T012, finalize:
Task T013: "Add circuit execution logging"
Task T014: "Store results in database"
Task T015: "Remove mock execution logic"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T005)
2. Complete Phase 2: Foundational (T006-T008) - CRITICAL
3. Complete Phase 3: User Story 1 (T009-T015)
4. **STOP and VALIDATE**: Test with Hadamard circuit
5. Deploy/demo basic Qiskit execution

**MVP delivers**: Workers execute real quantum circuits and return actual results (no error handling, default shots only)

### Incremental Delivery

1. MVP (Setup + Foundational + US1) → Deploy: Basic circuit execution ✅
2. Add US2 (Error Handling) → Deploy: Production-ready error handling ✅
3. Add US3 (Parameters) → Deploy: Full feature with configuration ✅
4. Integration testing → Validate: All scenarios work ✅
5. Polish → Final: Documentation and performance validated ✅

Each increment adds value without breaking previous functionality.

### Parallel Team Strategy

With multiple developers:

**Phase 1-2 (Together)**: All devs complete Setup + Foundational

**Phase 3-5 (Parallel)**:
- Developer A: User Story 1 (T009-T015) - Core execution
- Developer B: User Story 2 (T016-T022) - Error handling (waits for US1 complete)
- Developer C: User Story 3 (T023-T027) - Parameters (waits for US1 complete)

**Phase 6-7 (Together)**: Integration and Polish

---

## Task Statistics

**Total Tasks**: 45

**By Phase**:
- Setup: 5 tasks
- Foundational: 3 tasks
- User Story 1 (P1): 7 tasks
- User Story 2 (P2): 7 tasks
- User Story 3 (P3): 5 tasks
- Integration: 10 tasks
- Polish: 8 tasks

**Parallel Opportunities**: 23 tasks marked [P] can run in parallel within their phase

**MVP Scope**: 15 tasks (Setup + Foundational + US1)

**Independent Test Criteria**:
- US1: Submit Hadamard circuit → verify ~50/50 distribution
- US2: Submit invalid circuit → verify failed status with error message
- US3: Submit circuit with shots=100 → verify total counts = 100

---

## Notes

- All tasks include exact file paths for implementation
- [P] tasks = different files/modules, no dependencies within phase
- [Story] label (US1, US2, US3) maps task to specific user story
- Each user story independently completable and testable
- Stop at any checkpoint to validate story independently
- Qiskit 1.0+ used per research.md decision
- No database schema changes required (existing JSONB field sufficient)
- No API contract changes (worker-internal modification only)
- Tests not included (not requested in specification) - focus on implementation
