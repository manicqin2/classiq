# Database Migrations Guide

## Overview

This project uses [Alembic](https://alembic.sqlalchemy.org/) for database schema version control and migrations. Alembic allows us to:

- Track all database schema changes over time
- Apply changes incrementally across environments
- Rollback changes when needed
- Maintain a clear history of database evolution
- Ensure consistency between development, staging, and production databases

Each migration file contains both `upgrade()` and `downgrade()` functions, enabling bidirectional schema changes.

## Migration Commands

All migration commands should be executed within the API container using `docker-compose exec`.

### View Migration Status

```bash
# Check current migration version
docker-compose exec api alembic current

# View migration history
docker-compose exec api alembic history --verbose

# Show pending migrations
docker-compose exec api alembic heads
```

### Apply Migrations

```bash
# Upgrade to the latest version
docker-compose exec api alembic upgrade head

# Upgrade by one revision
docker-compose exec api alembic upgrade +1

# Upgrade to a specific revision
docker-compose exec api alembic upgrade 001
```

### Rollback Migrations

```bash
# Downgrade by one revision
docker-compose exec api alembic downgrade -1

# Downgrade to a specific revision
docker-compose exec api alembic downgrade 001

# Downgrade to the beginning (empty database)
docker-compose exec api alembic downgrade base
```

## Creating Migrations

### Step-by-Step Guide

1. **Make changes to your SQLAlchemy models** in `api/models/`

2. **Generate a migration automatically** (recommended):
   ```bash
   docker-compose exec api alembic revision --autogenerate -m "description of changes"
   ```

   Example:
   ```bash
   docker-compose exec api alembic revision --autogenerate -m "add user authentication tables"
   ```

3. **Review the generated migration file** in `api/migrations/versions/`:
   - Verify the `upgrade()` function contains the correct changes
   - Verify the `downgrade()` function properly reverses those changes
   - Add any custom SQL or data migrations if needed

4. **Test the migration**:
   ```bash
   # Apply the migration
   docker-compose exec api alembic upgrade head

   # Test rollback
   docker-compose exec api alembic downgrade -1

   # Reapply
   docker-compose exec api alembic upgrade head
   ```

5. **Commit the migration file** to version control

### Manual Migration Creation

For complex changes, create a migration manually:

```bash
docker-compose exec api alembic revision -m "description of changes"
```

Then edit the generated file to add your custom `upgrade()` and `downgrade()` logic.

### Migration Best Practices

- **One logical change per migration**: Keep migrations focused and atomic
- **Always write downgrade functions**: Enable rollbacks for all migrations
- **Test rollbacks before deploying**: Ensure `downgrade()` works correctly
- **Avoid data loss**: Use caution with operations like dropping columns or tables
- **Document complex migrations**: Add comments explaining non-obvious logic

## Rollback Procedures

### Rolling Back the Last Migration

Use this when the most recent migration has issues:

```bash
# Check current version
docker-compose exec api alembic current

# Rollback one version
docker-compose exec api alembic downgrade -1

# Verify rollback
docker-compose exec api alembic current
```

**WARNING**: Rolling back may result in data loss if the migration included:
- Dropping columns or tables
- Data transformations
- Constraint removals

### Rolling Back to a Specific Version

Use this to return to a known good state:

```bash
# View migration history to find target revision
docker-compose exec api alembic history

# Downgrade to specific revision (e.g., 001)
docker-compose exec api alembic downgrade 001

# Verify the target version
docker-compose exec api alembic current
```

Example output from `alembic history`:
```
001 -> 002 (head), add user authentication
<base> -> 001, create tasks and status_history tables
```

To rollback to revision 001:
```bash
docker-compose exec api alembic downgrade 001
```

### Rolling Back All Migrations

Use this to return to an empty database schema:

```bash
# WARNING: This will drop all tables managed by migrations
docker-compose exec api alembic downgrade base

# Verify (should show no current revision)
docker-compose exec api alembic current
```

**CRITICAL WARNING**: This operation will destroy all schema objects created by migrations. Ensure you have a database backup before proceeding.

### Verifying Rollback Success

After any rollback operation:

1. **Check the migration version**:
   ```bash
   docker-compose exec api alembic current
   ```

2. **Verify database state**:
   ```bash
   # Connect to the database
   docker-compose exec postgres psql -U quantum_user -d quantum_db

   # List tables
   \dt

   # Describe a specific table
   \d tasks

   # Exit
   \q
   ```

3. **Test application functionality**:
   ```bash
   # Check API health
   curl http://localhost:8001/health

   # Run application tests
   docker-compose exec api pytest
   ```

4. **Review migration history**:
   ```bash
   docker-compose exec api alembic history --verbose
   ```

## Troubleshooting

### Migration Fails During Upgrade

```bash
# Check the error message
docker-compose exec api alembic upgrade head

# If migration partially applied, check current state
docker-compose exec api alembic current

# Manually fix issues in database if needed
docker-compose exec postgres psql -U quantum_user -d quantum_db

# Mark migration as applied without running it (use with caution)
docker-compose exec api alembic stamp head
```

### Migration Fails During Downgrade

```bash
# Check the error message
docker-compose exec api alembic downgrade -1

# If downgrade is impossible, you may need to:
# 1. Fix the downgrade() function in the migration file
# 2. Or manually revert database changes
# 3. Then stamp the correct version

# Mark a specific version as current (use with extreme caution)
docker-compose exec api alembic stamp 001
```

### "Can't locate revision" Error

```bash
# Ensure migration files exist
ls api/migrations/versions/

# Rebuild the container to pick up new migration files
docker-compose up -d --build api
```

### Database Out of Sync

```bash
# Check current database version
docker-compose exec api alembic current

# Check expected version
docker-compose exec api alembic heads

# If versions don't match, either:
# 1. Upgrade to latest
docker-compose exec api alembic upgrade head

# 2. Or stamp the database with current code version (risky)
docker-compose exec api alembic stamp head
```

### Conflicting Migrations

When multiple developers create migrations simultaneously:

```bash
# Alembic will detect the conflict
docker-compose exec api alembic upgrade head
# Error: Multiple head revisions found

# Merge the heads
docker-compose exec api alembic merge heads -m "merge migrations"

# This creates a new migration that merges both branches
```

## Production Considerations

### Before Running Migrations in Production

1. **Backup the database**:
   ```bash
   # Create a backup
   docker-compose exec postgres pg_dump -U quantum_user quantum_db > backup_$(date +%Y%m%d_%H%M%S).sql

   # Or use your cloud provider's backup tools
   ```

2. **Test migrations in staging**:
   - Apply migrations to a staging environment that mirrors production
   - Verify application functionality
   - Test rollback procedures
   - Measure migration execution time

3. **Plan for downtime**:
   - Some migrations require exclusive database locks
   - Schedule migrations during maintenance windows
   - Communicate downtime to stakeholders

4. **Review migration SQL**:
   ```bash
   # Generate SQL without applying
   docker-compose exec api alembic upgrade head --sql > migration.sql

   # Review the SQL before applying
   cat migration.sql
   ```

### Running Migrations in Production

```bash
# 1. Backup database (critical!)
docker-compose exec postgres pg_dump -U quantum_user quantum_db > backup.sql

# 2. Check current version
docker-compose exec api alembic current

# 3. Review pending migrations
docker-compose exec api alembic history

# 4. Apply migrations
docker-compose exec api alembic upgrade head

# 5. Verify success
docker-compose exec api alembic current

# 6. Test application
curl http://localhost:8001/health
```

### Rollback in Production

**Only rollback if absolutely necessary.** Rolling forward with a new migration is often safer.

```bash
# 1. Verify backup exists
ls -lh backup_*.sql

# 2. Stop application traffic (if possible)
docker-compose stop api worker

# 3. Rollback migration
docker-compose exec api alembic downgrade -1

# 4. Verify database state
docker-compose exec postgres psql -U quantum_user -d quantum_db -c "\dt"

# 5. Restart services
docker-compose start api worker

# 6. Monitor for errors
docker-compose logs -f api worker
```

### Zero-Downtime Migrations

For migrations that must run without downtime:

1. **Use backward-compatible changes**:
   - Add new columns as nullable initially
   - Create new tables without removing old ones
   - Use multi-step migrations

2. **Example: Renaming a column**:
   - Migration 1: Add new column
   - Deploy code that writes to both columns
   - Migration 2: Backfill data
   - Deploy code that reads from new column
   - Migration 3: Remove old column

3. **Avoid**:
   - Dropping columns or tables still in use
   - Adding NOT NULL constraints without defaults
   - Renaming columns in a single step

## Reference: Existing Migration

The initial migration `001_create_tasks_table.py` demonstrates proper migration structure:

- Creates `taskstatus` ENUM type
- Creates `tasks` table with indexes
- Creates `status_history` table with foreign key
- Downgrade properly reverses all operations in correct order

Review this migration as a template for creating new migrations.

## Additional Resources

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [Alembic Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)

## Quick Reference

```bash
# Most common commands
docker-compose exec api alembic current              # Check current version
docker-compose exec api alembic history              # View history
docker-compose exec api alembic upgrade head         # Apply all pending
docker-compose exec api alembic downgrade -1         # Rollback last
docker-compose exec api alembic revision --autogenerate -m "message"  # Create new

# Emergency rollback
docker-compose exec postgres pg_dump -U quantum_user quantum_db > backup.sql
docker-compose exec api alembic downgrade <revision>
```
