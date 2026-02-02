"""Pytest configuration and fixtures."""

from unittest.mock import MagicMock

import pytest

from clinical_trials_agent.config import Settings


@pytest.fixture
def mock_settings():
    """Provide mock settings for testing."""
    return Settings(
        db_host="test-host",
        db_port=5432,
        db_name="test_db",
        db_user="test_user",
        db_password="test_pass",
        openai_api_key="test-key",
        openai_model="gpt-4o",
        langsmith_tracing=False,
        langsmith_api_key="test-key",
    )


@pytest.fixture
def mock_database():
    """Provide a mock SQLDatabase."""
    mock_db = MagicMock()
    mock_db.dialect = "postgresql"
    mock_db.get_usable_table_names.return_value = [
        "studies",
        "conditions",
        "browse_conditions",
    ]
    mock_db.run.return_value = "[(1, 'Test Study')]"
    return mock_db


@pytest.fixture
def mock_llm():
    """Provide a mock ChatOpenAI."""
    mock = MagicMock()
    mock.invoke.return_value = MagicMock(content="Test response", tool_calls=[])
    return mock
