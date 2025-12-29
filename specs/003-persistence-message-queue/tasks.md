# Tasks: Persistence Layer and Message Queue Integration

**Input**: Design documents from `/specs/003-persistence-message-queue/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are NOT explicitly requested in the specification. Implementation tasks focus on functionality and integration testing via manual verification in quickstart.md.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Based on plan.md, this is a web application structure:
- API code: `api/` directory
- Source code reorganization: `api/src/` with subdirectories
- Migrations: `api/migrations/`
- Worker: `api/worker.py`
- Docker configuration: Repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and dependency updates

- [x] T001 Update api/requirements.txt with new dependencies (sqlalchemy[asyncio]>=2.0, alembic>=1.13, asyncpg>=0.29, aio-pika>=9.0)
- [x] T002 [P] Create api/src/ directory structure (db/, queue/, services/ subdirectories)
- [x] T003 [P] Initialize Alembic for database migrations in api/migrations/
- [x] T004 [P] Create api/alembic.ini configuration file with database connection settings

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 Create database connection and session management in api/src/db/session.py
- [x] T006 [P] Define TaskStatus enum and SQLAlchemy Base in api/src/db/models.py
- [x] T007 [P] Create RabbitMQ connection manager in api/src/queue/__init__.py
- [x] T008 Update api/src/config.py to add DATABASE_URL and RABBITMQ_URL environment variables
- [x] T009 [P] Create Alembic migration 001: Create tasks and status_history tables in api/migrations/versions/001_create_tasks_table.py
- [x] T010 Update docker-compose.yml to add postgres and rabbitmq services with health checks
- [x] T011 [P] Create .env.example file with DATABASE_URL and RABBITMQ_URL templates

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Task Persistence Across Server Restarts (Priority: P1) 🎯 MVP

**Goal**: Tasks are permanently stored in PostgreSQL and survive server restarts with zero data loss

**Independent Test**: Submit task via POST /tasks, record task_id, restart API container (`docker-compose restart api`), query GET /tasks/{id}, verify task still exists with all details

### Implementation for User Story 1

- [x] T012 [P] [US1] Create Task SQLAlchemy model in api/src/db/models.py (task_id, circuit, submitted_at, current_status, completed_at, result, error_message)
- [x] T013 [P] [US1] Create StatusHistory SQLAlchemy model in api/src/db/models.py (id, task_id FK, status, transitioned_at, notes)
- [x] T014 [US1] Implement TaskRepository with create_task() and get_task() methods in api/src/db/repository.py
- [x] T015 [US1] Update api/src/routes.py POST /tasks to persist task to database using TaskRepository
- [x] T016 [US1] Update api/src/routes.py GET /tasks/{id} to retrieve task from database using TaskRepository
- [x] T017 [US1] Update api/src/routes.py GET /health to check database connectivity and return database_status field
- [x] T018 [US1] Update api/src/app.py lifespan to initialize database connection pool on startup
- [x] T019 [US1] Add database connection error handling in api/src/routes.py (return 503 on connection failures)
- [x] T020 [US1] Update api/src/models.py TaskSubmitResponse to include submitted_at field
- [x] T021 [US1] Update api/src/models.py TaskStatusResponse to include task_id and submitted_at fields

**Checkpoint**: At this point, User Story 1 should be fully functional - tasks persist and survive restarts

**Validation**:
```bash
# Run quickstart.md steps 1-3 (start services, run migrations, verify health)
# Submit task, restart API, verify task still exists
curl -X POST http://localhost:8001/tasks -d '{"circuit":"test"}' -H "Content-Type: application/json"
docker-compose restart api
curl http://localhost:8001/tasks/{TASK_ID}  # Should return task with all details
```

---

## Phase 4: User Story 2 - Asynchronous Task Processing via Message Queue (Priority: P2)

**Goal**: Tasks are queued for background processing by worker processes, API returns immediately

**Independent Test**: Submit task via POST /tasks (returns immediately with pending status), verify message appears in RabbitMQ management UI (http://localhost:15672), start worker (`docker-compose up -d worker`), observe task status transitions to processing then completed

### Implementation for User Story 2

- [x] T022 [P] [US2] Implement QueuePublisher class with publish_task_message() in api/src/queue/publisher.py
- [x] T023 [P] [US2] Implement QueueConsumer class with consume_messages() in api/src/queue/consumer.py
- [x] T024 [US2] Create TaskService with submit_task() method in api/src/services/task_service.py (coordinates DB + queue)
- [x] T025 [US2] Update api/src/routes.py POST /tasks to use TaskService.submit_task() instead of direct repository call
- [x] T026 [US2] Update api/src/routes.py POST /tasks to handle queue connection failures (return 503)
- [x] T027 [US2] Update api/src/routes.py GET /health to check queue connectivity and return queue_status field
- [x] T028 [US2] Implement TaskRepository.update_task_status() with optimistic locking in api/src/db/repository.py
- [x] T029 [US2] Create api/worker.py entrypoint that consumes queue messages and processes tasks
- [x] T030 [US2] Implement worker task processing logic in api/worker.py (transition pending→processing→completed with mock results)
- [x] T031 [US2] Add worker idempotency check in api/worker.py (skip if task already processing/completed)
- [x] T032 [US2] Add worker error handling in api/worker.py (catch exceptions, set task status to failed with error_message)
- [x] T033 [US2] Update docker-compose.yml to add worker service (runs api/worker.py)
- [x] T034 [US2] Configure RabbitMQ queue as durable with persistent messages in api/src/queue/publisher.py
- [x] T035 [US2] Configure worker to set prefetch_count=1 for fair distribution in api/worker.py

**Checkpoint**: At this point, User Stories 1 AND 2 should both work - tasks persist and are processed asynchronously

**Validation**:
```bash
# Run quickstart.md steps 1-7 (full workflow including worker)
# Submit task, verify immediate response, check RabbitMQ UI, observe worker logs
curl -X POST http://localhost:8001/tasks -d '{"circuit":"test"}' -H "Content-Type: application/json"
# Open http://localhost:15672 (guest/guest) - verify message count increases
docker-compose logs -f worker  # Should show "Processing task {id}"
curl http://localhost:8001/tasks/{TASK_ID}  # Status should transition: pending→processing→completed
```

---

## Phase 5: User Story 3 - Task Status History Tracking (Priority: P3)

**Goal**: All task state transitions are recorded with timestamps for observability

**Independent Test**: Submit task via POST /tasks, allow worker to process it, query GET /tasks/{id}, verify response includes status_history array with all transitions (pending→processing→completed) and timestamps

### Implementation for User Story 3

- [ ] T036 [P] [US3] Implement TaskRepository.create_status_history_entry() in api/src/db/repository.py
- [ ] T037 [US3] Update TaskRepository.create_task() to create initial status history entry (status=pending, notes="Task created")
- [ ] T038 [US3] Update TaskRepository.update_task_status() to create status history entry on each transition
- [ ] T039 [US3] Implement TaskRepository.get_task_with_history() with eager loading in api/src/db/repository.py
- [ ] T040 [US3] Update api/src/routes.py GET /tasks/{id} to use get_task_with_history() and include status_history in response
- [ ] T041 [US3] Create StatusHistoryEntry Pydantic model in api/src/models.py (status, transitioned_at, notes)
- [ ] T042 [US3] Update TaskStatusResponse model to include status_history list field in api/src/models.py
- [ ] T043 [US3] Update api/worker.py to add notes field when updating status ("Worker started processing", "Task completed successfully", etc.)

**Checkpoint**: All user stories should now be independently functional with full observability

**Validation**:
```bash
# Run full quickstart.md workflow
# Submit task, wait for completion, verify history
curl -X POST http://localhost:8001/tasks -d '{"circuit":"test"}' -H "Content-Type: application/json"
sleep 10  # Wait for worker to process
curl http://localhost:8001/tasks/{TASK_ID} | jq '.status_history'
# Should show 3 entries: pending (created), processing (worker started), completed (finished)
```

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T044 [P] Add database query logging with execution time in api/src/db/session.py (use structlog)
- [ ] T045 [P] Add queue message publish/consume logging with correlation IDs in api/src/queue/
- [ ] T046 Update API logging to include database and queue operations in api/src/logging_config.py
- [ ] T047 [P] Update api/README.md with database and queue setup instructions
- [ ] T048 [P] Create api/tests/integration/test-persistence.sh to verify database persistence across restarts
- [ ] T049 [P] Create api/tests/integration/test-worker.py to verify queue consumption and status updates
- [ ] T050 Add graceful shutdown handling for worker in api/worker.py (acknowledge in-flight messages before exit)
- [ ] T051 Validate all quickstart.md steps work end-to-end
- [ ] T052 [P] Document database migration rollback procedure in api/migrations/README.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Integrates with US1 (uses same Task model and repository) but can be tested independently by mocking worker
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Extends US1 database model, integrates with US2 worker, but independent test verifies history tracking works

### Within Each User Story

**User Story 1** (Persistence):
1. Create models (T012, T013) in parallel
2. Implement repository (T014) - depends on models
3. Update routes (T015-T017) - depends on repository
4. Update app/models (T018-T021) in parallel

**User Story 2** (Queue Processing):
1. Create queue classes (T022, T023) in parallel
2. Create service (T024) - depends on queue publisher
3. Update routes (T025-T027) - depends on service
4. Implement repository updates (T028)
5. Create worker (T029-T032) - depends on repository and queue consumer
6. Update docker-compose (T033-T035)

**User Story 3** (History Tracking):
1. Repository methods (T036-T039) can be done sequentially
2. Update routes and models (T040-T042) in parallel after repository done
3. Worker updates (T043)

### Parallel Opportunities

- All Setup tasks (T001-T004) marked [P] can run in parallel
- Foundational tasks marked [P] can run in parallel: T006, T007, T009, T011
- User Story 1 models (T012, T013) can run in parallel
- User Story 2 queue classes (T022, T023) can run in parallel
- Polish tasks marked [P] (T044, T045, T047-T049, T052) can run in parallel
- **Different user stories can be worked on in parallel by different team members after Foundational phase**

---

## Parallel Example: User Story 1

```bash
# Launch all models for User Story 1 together:
Task T012: "Create Task SQLAlchemy model in api/src/db/models.py"
Task T013: "Create StatusHistory SQLAlchemy model in api/src/db/models.py"

# After repository is done, update multiple files in parallel:
Task T018: "Update api/src/app.py lifespan"
Task T020: "Update api/src/models.py TaskSubmitResponse"
Task T021: "Update api/src/models.py TaskStatusResponse"
```

## Parallel Example: User Story 2

```bash
# Launch queue classes together:
Task T022: "Implement QueuePublisher in api/src/queue/publisher.py"
Task T023: "Implement QueueConsumer in api/src/queue/consumer.py"

# After worker core is done, update docker and configuration:
Task T033: "Update docker-compose.yml to add worker service"
Task T034: "Configure RabbitMQ queue as durable"
Task T035: "Configure worker prefetch_count=1"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T004)
2. Complete Phase 2: Foundational (T005-T011) - CRITICAL
3. Complete Phase 3: User Story 1 (T012-T021)
4. **STOP and VALIDATE**: Run persistence test from quickstart.md
5. Deploy/demo if ready - **You now have production-grade persistence!**

At this point you have:
- ✅ Tasks stored in PostgreSQL
- ✅ Zero data loss on server restart
- ✅ All FR-001, FR-002, FR-006 requirements met
- ✅ SC-001 success criteria met (100% persistence reliability)

### Incremental Delivery

1. Complete Setup + Foundational (T001-T011) → Foundation ready
2. Add User Story 1 (T012-T021) → Test independently → **Deploy/Demo (MVP!)**
3. Add User Story 2 (T022-T035) → Test independently → **Deploy/Demo (Full async processing!)**
4. Add User Story 3 (T036-T043) → Test independently → **Deploy/Demo (Complete observability!)**
5. Polish (T044-T052) → Final production hardening

Each story adds value without breaking previous stories.

### Parallel Team Strategy

With multiple developers:

1. **Team completes Setup + Foundational together** (T001-T011)
2. **Once Foundational is done**:
   - Developer A: User Story 1 (T012-T021) - Persistence
   - Developer B: User Story 2 (T022-T035) - Queue + Worker
   - Developer C: User Story 3 (T036-T043) - History Tracking
3. Stories complete and integrate independently
4. All developers: Polish tasks (T044-T052) in parallel

---

## Task Summary

- **Total Tasks**: 52
- **Setup Phase**: 4 tasks
- **Foundational Phase**: 7 tasks (BLOCKS all stories)
- **User Story 1 (P1)**: 10 tasks - Persistence MVP
- **User Story 2 (P2)**: 14 tasks - Async processing
- **User Story 3 (P3)**: 8 tasks - History tracking
- **Polish Phase**: 9 tasks - Production hardening

**Parallel Opportunities**: 20 tasks marked [P] can run in parallel within their phases

**Independent Testing**:
- User Story 1: Submit task → restart server → verify task exists (quickstart.md step 6)
- User Story 2: Submit task → verify worker processes it → check status transitions (quickstart.md step 5)
- User Story 3: Submit task → wait for completion → verify history array (quickstart.md validation)

**Suggested MVP Scope**: Setup + Foundational + User Story 1 (21 tasks) delivers production-grade persistence

---

## Notes

- [P] tasks = different files/modules, no dependencies, can run in parallel
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable per spec.md acceptance criteria
- Stop at any checkpoint to validate story independently using quickstart.md
- All file paths follow plan.md structure (api/ directory with src/ reorganization)
- Tests are NOT included as they were not requested in specification; use quickstart.md for manual validation
- Commit after each task or logical group
- Database migrations are version controlled in api/migrations/versions/
- Worker runs as separate container sharing codebase with API
