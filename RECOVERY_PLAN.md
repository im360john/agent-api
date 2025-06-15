# Agent API Recovery Plan

## Current State Analysis
The project has several code quality issues and missing infrastructure. This document outlines the plan to fix these issues.

## Virtual Environment Setup
1. Check for existing venv: `ls -la | grep venv`
   - Found: `.venv` and `venv` directories exist
2. Activate the correct venv:
   ```bash
   source venv/bin/activate  # or source .venv/bin/activate
   ```
3. Install development dependencies:
   ```bash
   pip install ruff mypy pytest pytest-asyncio pytest-cov
   ```

## Issues to Fix (Priority Order)

### High Priority
1. **Fix unused imports** (23 errors found)
   - Run: `source venv/bin/activate && ruff check --fix .`
   - Files affected: agents/client.py, agents/image_evaluator_agent.py, agents/product_image_agent.py, start_server.py, start_test_server.py

2. **Fix bare except statements**
   - agents/client.py: lines 72, 231
   - agents/image_evaluator_agent.py: line 203
   - Replace with specific exception handling

3. **Add proper test suite**
   - Create tests/ directory
   - Add pytest configuration
   - Write tests for each agent
   - Add test for API endpoints

### Medium Priority
4. **Fix f-string formatting issues**
   - Remove unnecessary f-strings in debug statements
   - Can be auto-fixed with ruff

5. **Database session management**
   - Consolidate db/session.py and db/session_fixed.py
   - Use single source of truth for database configuration

### Low Priority
6. **Fix module import ordering**
   - Move imports to top of files in start_test_server.py and test_api.py

7. **Add CI/CD**
   - Create .github/workflows/ci.yml
   - Add automated testing and linting

## Commands to Run (in order)
```bash
# 1. Activate venv
source venv/bin/activate

# 2. Install dev dependencies
pip install ruff mypy pytest pytest-asyncio pytest-cov

# 3. Auto-fix what we can
ruff check --fix .

# 4. Run validation
./scripts/validate.sh

# 5. Create test structure
mkdir -p tests/agents tests/api
touch tests/__init__.py tests/conftest.py

# 6. Run tests (after creating them)
pytest -v
```

## Manual Fixes Needed
1. Replace bare except blocks with specific exceptions
2. Consolidate database session files
3. Write actual test cases
4. Fix any remaining mypy errors

## Validation Command
After all fixes, run:
```bash
source venv/bin/activate && ./scripts/validate.sh
```

This should show no ruff errors and minimal mypy errors.