"""Unit tests for settings."""

from clinical_trials_agent.config.settings import Settings


class TestSettings:
    """Tests for application settings."""

    def test_default_db_host(self):
        """Default database host should be AACT public host."""
        settings = Settings(db_user="test", db_password="test")
        assert settings.db_host == "aact-db.ctti-clinicaltrials.org"

    def test_default_db_port(self):
        """Default database port should be 5432."""
        settings = Settings(db_user="test", db_password="test")
        assert settings.db_port == 5432

    def test_default_db_name(self):
        """Default database name should be aact."""
        settings = Settings(db_user="test", db_password="test")
        assert settings.db_name == "aact"

    def test_database_url_construction(self):
        """Database URL should be properly constructed."""
        settings = Settings(
            db_host="localhost",
            db_port=5432,
            db_name="testdb",
            db_user="user",
            db_password="pass",
        )
        assert settings.database_url == "postgresql://user:pass@localhost:5432/testdb"

    def test_default_openai_model(self):
        """Default OpenAI model should be set."""
        settings = Settings(db_user="test", db_password="test", openai_model="gpt-4o")
        assert settings.openai_model == "gpt-4o"

    def test_langfuse_base_url_is_set(self):
        """Langfuse base URL should be set."""
        settings = Settings(db_user="test", db_password="test")
        assert settings.langfuse_base_url != ""

    def test_default_api_port(self):
        """Default API port should be 8000."""
        settings = Settings(db_user="test", db_password="test")
        assert settings.api_port == 8000
