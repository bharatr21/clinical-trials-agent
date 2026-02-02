"""E2E tests for API endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from clinical_trials_agent.api.main import app


@pytest.fixture
def client():
    """Provide test client for FastAPI app."""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_returns_200(self, client):
        """Health endpoint should return 200 OK."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_status(self, client):
        """Health endpoint should return status field."""
        response = client.get("/health")
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"

    def test_health_returns_version(self, client):
        """Health endpoint should return version field."""
        response = client.get("/health")
        data = response.json()
        assert "version" in data


class TestRootEndpoint:
    """Tests for the root endpoint."""

    def test_root_returns_200(self, client):
        """Root endpoint should return 200 OK."""
        response = client.get("/")
        assert response.status_code == 200

    def test_root_returns_api_info(self, client):
        """Root endpoint should return API information."""
        response = client.get("/")
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "docs" in data


class TestQueryEndpoint:
    """Tests for the query endpoint."""

    def test_query_requires_question(self, client):
        """Query endpoint should require a question."""
        response = client.post("/api/v1/query", json={})
        assert response.status_code == 422

    def test_query_rejects_empty_question(self, client):
        """Query endpoint should reject empty questions."""
        response = client.post("/api/v1/query", json={"question": ""})
        assert response.status_code == 422

    @patch(
        "clinical_trials_agent.api.routes.query._save_conversation_metadata",
        new_callable=AsyncMock,
    )
    @patch("clinical_trials_agent.api.routes.query.create_agent")
    def test_query_returns_answer(self, mock_create_agent, _mock_save_meta, client):
        """Query endpoint should return an answer."""
        mock_agent = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "There are 100 recruiting trials."
        mock_message.tool_calls = []
        mock_agent.ainvoke = AsyncMock(return_value={"messages": [mock_message]})
        mock_create_agent.return_value = mock_agent

        response = client.post(
            "/api/v1/query",
            json={"question": "How many trials are recruiting?"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert data["answer"] == "There are 100 recruiting trials."

    @patch(
        "clinical_trials_agent.api.routes.query._save_conversation_metadata",
        new_callable=AsyncMock,
    )
    @patch("clinical_trials_agent.api.routes.query.create_agent")
    def test_query_returns_sql_query(self, mock_create_agent, _mock_save_meta, client):
        """Query endpoint should return the SQL query if available."""
        mock_message1 = MagicMock()
        mock_message1.content = ""
        mock_message1.tool_calls = [
            {
                "name": "sql_db_query",
                "args": {"query": "SELECT COUNT(*) FROM ctgov.studies"},
            }
        ]

        mock_message2 = MagicMock()
        mock_message2.content = "There are 500,000 studies."
        mock_message2.tool_calls = []

        mock_agent = MagicMock()
        mock_agent.ainvoke = AsyncMock(
            return_value={"messages": [mock_message1, mock_message2]}
        )
        mock_create_agent.return_value = mock_agent

        response = client.post(
            "/api/v1/query",
            json={"question": "How many studies are there?"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "sql_query" in data
        assert data["sql_query"] == "SELECT COUNT(*) FROM ctgov.studies"
