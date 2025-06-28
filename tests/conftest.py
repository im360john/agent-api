"""
Pytest configuration for agent tests
Provides fixtures and async support
"""

import pytest
import asyncio
import os
from unittest.mock import patch


# Configure pytest-asyncio
pytest_plugins = ['pytest_asyncio']


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def mock_environment():
    """Mock environment variables for all tests"""
    env_vars = {
        "OPENAI_API_KEY": "test-key",
        "FIRECRAWL_API_KEY": "test-firecrawl-key",
        "BROWSERBASE_API_KEY": "test-browserbase-key",
        "BROWSERBASE_PROJECT_ID": "test-project-id",
        "EXA_API_KEY": "test-exa-key",
        "DATABASE_URL": "postgresql://test:test@localhost/test"
    }
    
    with patch.dict(os.environ, env_vars):
        yield


@pytest.fixture
def mock_db_url():
    """Provide test database URL"""
    return "postgresql://test:test@localhost/test"


# Mark all async tests
def pytest_collection_modifyitems(config, items):
    """Automatically mark all async tests"""
    for item in items:
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.asyncio)