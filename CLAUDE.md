# classiq Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-12-29

## Active Technologies
- Python 3.11 (existing) + Qiskit (version TBD - likely 0.45.x or 1.x for OpenQASM 3 support), existing FastAPI 0.104.1, SQLAlchemy 2.0+, aio-pika 9.0+ (006-qiskit-execution)
- PostgreSQL (existing) - JSONB field for measurement results (006-qiskit-execution)

- Python 3.11 (existing) + FastAPI 0.104.1 (existing), SQLAlchemy 2.0+ (new - ORM), Alembic (new - migrations), aio-pika 9.0+ (new - async RabbitMQ client) (003-persistence-message-queue)

## Project Structure

```text
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.11 (existing): Follow standard conventions

## Recent Changes
- 006-qiskit-execution: Added Python 3.11 (existing) + Qiskit (version TBD - likely 0.45.x or 1.x for OpenQASM 3 support), existing FastAPI 0.104.1, SQLAlchemy 2.0+, aio-pika 9.0+

- 003-persistence-message-queue: Added Python 3.11 (existing) + FastAPI 0.104.1 (existing), SQLAlchemy 2.0+ (new - ORM), Alembic (new - migrations), aio-pika 9.0+ (new - async RabbitMQ client)

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
