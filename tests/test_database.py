"""Tests for database connection module."""

from clinical_trials_agent.database.connection import AACT_TABLES


class TestAACTTables:
    """Tests for the AACT tables configuration."""

    def test_aact_tables_not_empty(self):
        """AACT_TABLES should not be empty."""
        assert len(AACT_TABLES) > 0

    def test_studies_table_included(self):
        """Studies table should be included."""
        assert "studies" in AACT_TABLES

    def test_conditions_table_included(self):
        """Conditions table should be included."""
        assert "conditions" in AACT_TABLES

    def test_browse_conditions_table_included(self):
        """Browse conditions table (for MeSH terms) should be included."""
        assert "browse_conditions" in AACT_TABLES

    def test_interventions_table_included(self):
        """Interventions table should be included."""
        assert "interventions" in AACT_TABLES

    def test_browse_interventions_table_included(self):
        """Browse interventions table (for MeSH terms) should be included."""
        assert "browse_interventions" in AACT_TABLES

    def test_eligibilities_table_included(self):
        """Eligibilities table should be included."""
        assert "eligibilities" in AACT_TABLES

    def test_sponsors_table_included(self):
        """Sponsors table should be included."""
        assert "sponsors" in AACT_TABLES

    def test_facilities_table_included(self):
        """Facilities table should be included."""
        assert "facilities" in AACT_TABLES

    def test_designs_table_included(self):
        """Designs table should be included."""
        assert "designs" in AACT_TABLES

    def test_countries_table_included(self):
        """Countries table should be included."""
        assert "countries" in AACT_TABLES
