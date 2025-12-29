# Implementation Plan: Qiskit Circuit Execution in Workers

**Branch**: `006-qiskit-execution` | **Date**: 2025-12-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/006-qiskit-execution/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Replace mock quantum circuit execution in workers with real Qiskit simulation. Workers will parse OpenQASM 3 circuits, execute them using Qiskit AerSimulator, and store actual measurement results. This enables the system to provide genuine quantum computation results instead of fixed mock data, transforming it from a task queuing demo into a functional quantum circuit execution platform.

## Technical Context

**Language/Version**: Python 3.11 (existing)
**Primary Dependencies**: Qiskit (version TBD - likely 0.45.x or 1.x for OpenQASM 3 support), existing FastAPI 0.104.1, SQLAlchemy 2.0+, aio-pika 9.0+
**Storage**: PostgreSQL (existing) - JSONB field for measurement results
**Testing**: pytest (existing)
**Target Platform**: Docker containers on Linux (existing infrastructure)
**Project Type**: Backend service (worker process modification)
**Performance Goals**: 100 circuit executions/minute across 3 workers, <30 seconds for 10-qubit circuits
**Constraints**: No enforced timeout (user responsibility), no size restrictions on results, memory limited to 2GB per worker
**Scale/Scope**: Handles circuits up to 15 qubits efficiently, supports 1-100,000 shots per execution

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Status**: Constitution file is template-only (not yet customized for project). Proceeding with standard best practices:
- ✅ Modifying existing worker.py (not creating new library)
- ✅ Existing test infrastructure (pytest)
- ✅ Follows existing architecture (worker processes quantum tasks)
- ✅ No new services or breaking changes to API contracts

## Project Structure

### Documentation (this feature)

```text
specs/006-qiskit-execution/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
api/
├── worker.py                  # MODIFY: Replace mock execution with Qiskit
├── src/
│   ├── execution/             # NEW: Qiskit execution module
│   │   ├── __init__.py
│   │   ├── qiskit_executor.py # Circuit parsing and execution
│   │   └── result_formatter.py # Convert Qiskit results to DB format
│   ├── db/                    # EXISTING: Database models
│   │   ├── models.py          # REVIEW: Task model (result field already exists)
│   │   └── repository.py      # EXISTING: Task CRUD operations
│   ├── queue/                 # EXISTING: Queue handling
│   │   └── consumer.py        # EXISTING: Message consumption
│   └── services/              # EXISTING: Business logic
│       └── task_service.py    # EXISTING: Task state management
├── requirements.txt           # MODIFY: Add qiskit dependency
└── tests/
    ├── unit/
    │   └── test_qiskit_executor.py # NEW: Unit tests for execution
    └── integration/
        └── test_worker_qiskit.py   # NEW: End-to-end with real circuits
```

**Structure Decision**: Modifying existing worker infrastructure. New `src/execution/` module encapsulates Qiskit-specific logic, keeping worker.py focused on queue message handling. This follows separation of concerns and makes testing easier (can test execution logic independently of queue infrastructure).

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations detected. Implementation follows existing architecture patterns.

---

## Phase 0: Research & Technical Decisions

### Research Topics

The following areas require investigation to resolve technical uncertainties:

1. **Qiskit Version Selection**: Determine optimal Qiskit version (0.45.x vs 1.x) for OpenQASM 3 support, stability, and performance
2. **OpenQASM 3 Parser**: Identify correct Qiskit module/class for parsing OpenQASM 3 strings
3. **AerSimulator Configuration**: Research default vs optimal simulator settings for circuits up to 15 qubits
4. **Error Handling Patterns**: Document Qiskit exception hierarchy and error types for proper catch/translate logic
5. **Memory Management**: Investigate Qiskit memory usage patterns and garbage collection for long-running worker processes
6. **Result Format**: Understand Qiskit measurement result format and conversion to PostgreSQL JSONB

### Research Output Location

All findings will be documented in `research.md` following the decision/rationale/alternatives format.

---

## Phase 1: Design Artifacts

### Data Model

**File**: `data-model.md`

**Entities to Document**:
- Task model (existing) - review result JSONB field structure
- Measurement result format (Qiskit counts dict → JSONB)
- Error message format for Qiskit exceptions

**Changes from Existing**:
- No database schema changes required (result field already JSONB)
- Document expected JSONB structure for consistency

### API Contracts

**Directory**: `contracts/`

**Artifacts**:
- No API contract changes (worker-internal modification)
- Document worker startup validation contract (exit code behavior)
- Document queue message format expectations (existing, verify compatibility)

### Developer Quickstart

**File**: `quickstart.md`

**Content**:
- Installing Qiskit locally for development
- Running workers with Qiskit
- Testing with sample circuits (H gate, Bell state)
- Troubleshooting common Qiskit issues
- Verifying results match expected distributions

---

## Phase 2: Task Breakdown

Generated by `/speckit.tasks` command (not included in this plan).

Tasks will be derived from:
- Qiskit integration and dependency management
- worker.py refactoring to use Qiskit executor
- Error handling implementation
- Unit and integration testing
- Documentation updates

---

## Notes

- Existing API submission endpoint already supports arbitrary circuit strings - no changes needed
- Database schema already uses JSONB for results - no migration required
- Queue infrastructure unchanged - workers still process one task at a time
- Docker configuration will need Qiskit added to requirements.txt and built into image
