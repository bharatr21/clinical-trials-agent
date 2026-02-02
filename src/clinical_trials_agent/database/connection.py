"""Database connection for AACT PostgreSQL database."""

from functools import lru_cache

from langchain_community.utilities import SQLDatabase
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

from clinical_trials_agent.config import get_settings

# Key AACT tables for clinical trials queries
# See: https://aact.ctti-clinicaltrials.org/schema
AACT_TABLES = [
    "studies",  # Core study information (nct_id, brief_title, overall_status, etc.)
    "conditions",  # Study conditions/diseases
    "browse_conditions",  # MeSH-standardized conditions (CRITICAL for search)
    "interventions",  # Drugs, devices, procedures being studied
    "browse_interventions",  # MeSH-standardized interventions
    "eligibilities",  # Inclusion/exclusion criteria, age, gender
    "outcomes",  # Primary/secondary outcome measures and results
    "sponsors",  # Study sponsors (lead, collaborator)
    "facilities",  # Study sites/locations
    "countries",  # Countries where study is conducted
    "designs",  # Study design (phase, allocation, masking)
    "participant_flows",  # Enrollment and participant flow
    "reported_events",  # Adverse events
    "result_groups",  # Result group definitions
]


@lru_cache
def get_engine():
    """Get a cached SQLAlchemy engine with connection pooling.

    Uses conservative pool settings since AACT is a shared public database
    with connection limits.
    """
    settings = get_settings()

    engine = create_engine(
        settings.database_url,
        poolclass=QueuePool,
        pool_size=2,  # Keep minimal connections open
        max_overflow=3,  # Allow up to 5 total (2 + 3)
        pool_timeout=30,  # Wait up to 30s for a connection
        pool_recycle=300,  # Recycle connections after 5 minutes
        pool_pre_ping=True,  # Verify connections before use
    )

    return engine


@lru_cache
def get_database() -> SQLDatabase:
    """Get a cached SQLDatabase instance for AACT.

    The database is configured to:
    - Use the ctgov schema (AACT's main schema)
    - Include only key tables relevant for clinical trials queries
    - Return sample rows for schema inspection
    - Use connection pooling to avoid "too many connections" errors
    """
    engine = get_engine()

    db = SQLDatabase(
        engine=engine,
        schema="ctgov",
        include_tables=AACT_TABLES,
        sample_rows_in_table_info=3,
    )

    return db
