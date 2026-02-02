"""Unit tests for prompts."""

from clinical_trials_agent.agent.prompts import (
    CHECK_QUERY_SYSTEM_PROMPT,
    GENERATE_QUERY_SYSTEM_PROMPT,
)


class TestGenerateQueryPrompt:
    """Tests for the generate query system prompt."""

    def test_prompt_contains_aact_reference(self):
        """Prompt should reference AACT database."""
        assert "AACT" in GENERATE_QUERY_SYSTEM_PROMPT

    def test_prompt_contains_postgresql_reference(self):
        """Prompt should reference PostgreSQL."""
        assert "PostgreSQL" in GENERATE_QUERY_SYSTEM_PROMPT

    def test_prompt_contains_ctgov_schema(self):
        """Prompt should reference ctgov schema."""
        assert "ctgov" in GENERATE_QUERY_SYSTEM_PROMPT

    def test_prompt_contains_mesh_term_guidance(self):
        """Prompt should contain MeSH term mapping guidance."""
        assert "MeSH" in GENERATE_QUERY_SYSTEM_PROMPT
        assert "browse_conditions" in GENERATE_QUERY_SYSTEM_PROMPT

    def test_prompt_contains_breast_cancer_mapping(self):
        """Prompt should contain breast cancer to Breast Neoplasms mapping."""
        assert "breast cancer" in GENERATE_QUERY_SYSTEM_PROMPT.lower()
        assert "Breast Neoplasms" in GENERATE_QUERY_SYSTEM_PROMPT

    def test_prompt_contains_status_values(self):
        """Prompt should document study status values."""
        assert "Recruiting" in GENERATE_QUERY_SYSTEM_PROMPT
        assert "Completed" in GENERATE_QUERY_SYSTEM_PROMPT

    def test_prompt_contains_key_tables(self):
        """Prompt should reference key AACT tables."""
        assert "studies" in GENERATE_QUERY_SYSTEM_PROMPT
        assert "conditions" in GENERATE_QUERY_SYSTEM_PROMPT
        assert "interventions" in GENERATE_QUERY_SYSTEM_PROMPT

    def test_prompt_warns_against_dml(self):
        """Prompt should warn against DML statements."""
        assert "INSERT" in GENERATE_QUERY_SYSTEM_PROMPT
        assert "DELETE" in GENERATE_QUERY_SYSTEM_PROMPT
        assert "DROP" in GENERATE_QUERY_SYSTEM_PROMPT

    def test_prompt_has_top_k_placeholder(self):
        """Prompt should have {top_k} placeholder for result limits."""
        assert "{top_k}" in GENERATE_QUERY_SYSTEM_PROMPT


class TestCheckQueryPrompt:
    """Tests for the check query system prompt."""

    def test_prompt_contains_postgresql_reference(self):
        """Prompt should reference PostgreSQL."""
        assert "PostgreSQL" in CHECK_QUERY_SYSTEM_PROMPT

    def test_prompt_contains_common_mistakes(self):
        """Prompt should list common SQL mistakes to check."""
        assert "NOT IN" in CHECK_QUERY_SYSTEM_PROMPT
        assert "UNION" in CHECK_QUERY_SYSTEM_PROMPT

    def test_prompt_contains_schema_check(self):
        """Prompt should mention schema qualification."""
        assert "ctgov" in CHECK_QUERY_SYSTEM_PROMPT

    def test_prompt_contains_mesh_check(self):
        """Prompt should mention MeSH term usage."""
        assert "MeSH" in CHECK_QUERY_SYSTEM_PROMPT

    def test_prompt_mentions_nct_id(self):
        """Prompt should mention nct_id as join key."""
        assert "nct_id" in CHECK_QUERY_SYSTEM_PROMPT
