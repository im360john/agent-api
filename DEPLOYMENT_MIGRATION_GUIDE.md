# Remote Deployment Migration Guide

## The tables will NOT be created automatically on service restart!

You need to manually run the migration on your remote database. Here are your options:

## Option 1: Run Migration Script Remotely (Recommended)

1. **SSH into your remote server** or run this from your deployment environment:

```bash
# Set your remote database credentials
export DB_HOST=your-remote-host
export DB_PORT=5432
export DB_DATABASE=your-db-name
export DB_USER=your-db-user
export DB_PASS=your-db-password

# Run the migration
python3 run_knowledge_base_migration.py
```

## Option 2: Direct SQL Execution

Connect to your remote PostgreSQL database and run the migration SQL directly:

```bash
# Connect to remote database
psql -h your-remote-host -U your-db-user -d your-db-name

# Run the migration SQL
\i migrations/add_scraping_knowledge_base.sql
```

## Option 3: Add to Your CI/CD Pipeline

Add a migration step to your deployment process:

```yaml
# Example for GitHub Actions
- name: Run Database Migrations
  env:
    DB_HOST: ${{ secrets.DB_HOST }}
    DB_USER: ${{ secrets.DB_USER }}
    DB_PASS: ${{ secrets.DB_PASS }}
    DB_DATABASE: ${{ secrets.DB_DATABASE }}
  run: |
    python3 run_knowledge_base_migration.py
```

## Option 4: Use a Database Migration Tool

Consider using tools like:
- **Alembic** (Python)
- **Flyway** (Java-based but language agnostic)
- **migrate** (Go)

Example with Alembic:
```bash
# Initialize alembic
alembic init alembic

# Create migration
alembic revision -m "add knowledge base tables"

# Run migration
alembic upgrade head
```

## Important Notes

1. **The enhanced agent will still work** without these tables, but:
   - No scraping metrics will be stored
   - No learning from corrections
   - No confidence tracking
   - You'll see errors in logs when it tries to write to missing tables

2. **To verify tables were created**, run:
```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'pricing' 
AND table_name IN ('scraping_metrics', 'knowledge_base', 'user_corrections', 'learned_patterns');
```

3. **For production**, you might want to:
   - Run migration in a transaction
   - Take a backup first
   - Run during low-traffic period

## Quick Remote Migration Command

If you have direct access to the production database:

```bash
# One-liner to run migration remotely (adjust credentials)
psql "postgresql://user:password@host:port/database" -f migrations/add_scraping_knowledge_base.sql
```

## Temporary Workaround

If you can't run migrations immediately, the agent will continue working with the existing functionality. The new features (confidence tracking, user corrections) simply won't be available until the tables are created.