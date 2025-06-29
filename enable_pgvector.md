# How to Enable pgvector on PostgreSQL

## For PostgreSQL 15 (your current version)

### Option 1: Install from Package Manager (Ubuntu/Debian)
```bash
# Update package list
sudo apt update

# Install pgvector for PostgreSQL 15
sudo apt install postgresql-15-pgvector

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### Option 2: Install from Source
```bash
# Install build dependencies
sudo apt install postgresql-server-dev-15 git make gcc

# Clone pgvector
git clone https://github.com/pgvector/pgvector.git
cd pgvector

# Build and install
make
sudo make install

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### Option 3: Using Docker (if running PostgreSQL in Docker)
Use the pgvector Docker image:
```yaml
services:
  postgres:
    image: pgvector/pgvector:pg15
    environment:
      POSTGRES_PASSWORD: yourpassword
      POSTGRES_DB: ai
```

## Enable pgvector in Your Database

Once installed, connect to your database and run:

```sql
-- Connect to your database
psql -U ai -d ai -h localhost

-- Create the extension
CREATE EXTENSION vector;

-- Verify it's installed
\dx vector
```

## Re-run Migration After Installing pgvector

After pgvector is installed and enabled:

```bash
# Re-run the migration to add vector columns
python3 run_knowledge_base_migration.py
```

This will:
- Add the `embedding vector(1536)` column to knowledge_base table
- Create the vector similarity index for semantic search
- Enable AI-powered similarity matching for products

## Benefits of pgvector

With pgvector enabled, the knowledge base can:
1. **Semantic Product Search** - Find similar products even with different names
2. **Intelligent Pattern Matching** - Match URL patterns based on similarity
3. **Better Variant Detection** - Identify product variants using embeddings
4. **Correction Clustering** - Group similar corrections together

## Checking if pgvector is Working

```sql
-- Check if vector type is available
SELECT 1::vector;

-- Check if extension is installed
SELECT * FROM pg_extension WHERE extname = 'vector';

-- Test vector operations
SELECT '[1,2,3]'::vector <-> '[4,5,6]'::vector as distance;
```