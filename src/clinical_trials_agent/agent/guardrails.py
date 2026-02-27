"""Guardrails for the clinical trials agent.

Provides:
- Topic classification: rejects off-topic queries
- Prompt injection detection: flags manipulation attempts
- SQL validation: deterministic checks before query execution
"""

import logging
import re

import sqlparse

from clinical_trials_agent.database.connection import AACT_TABLES

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 1. Topic classification prompt (used by the LLM-based guardrail node)
# ---------------------------------------------------------------------------

TOPIC_CLASSIFIER_PROMPT = """\
You are a topic classifier. Determine whether the user's message is related to \
clinical trials, medical research, drugs, treatments, diseases, health conditions, \
the ClinicalTrials.gov database, or the AACT database.

Respond with EXACTLY one word:
- "yes" if the message is related to clinical trials or medical/health research
- "no" if the message is clearly off-topic (e.g. cooking, sports, politics, coding help, jokes)

Be lenient: if the message is even tangentially related to health, medicine, \
pharmaceuticals, or biomedical research, respond "yes".\
"""

OFF_TOPIC_RESPONSE = (
    "I'm a clinical trials research assistant and can only help with questions "
    "about clinical trials, medical research, treatments, and health conditions. "
    "Could you ask me something about clinical trials instead? For example:\n\n"
    '- "How many breast cancer trials are currently recruiting?"\n'
    '- "What phase 3 diabetes trials are sponsored by Pfizer?"\n'
    '- "Show me COVID-19 vaccine trials completed in 2023"'
)

# ---------------------------------------------------------------------------
# 2. Prompt injection detection
# ---------------------------------------------------------------------------

# Patterns that suggest prompt injection attempts
_INJECTION_PATTERNS = [
    re.compile(
        r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|rules)", re.I
    ),
    re.compile(
        r"disregard\s+(all\s+)?(previous|prior|your)\s+(instructions|prompts|rules)",
        re.I,
    ),
    re.compile(
        r"forget\s+(all\s+)?(previous|prior|your)\s+(instructions|prompts|rules)", re.I
    ),
    re.compile(r"you\s+are\s+now\s+(a|an)\b", re.I),
    re.compile(r"new\s+(instructions|role|persona)\s*:", re.I),
    re.compile(r"system\s*prompt\s*:", re.I),
    re.compile(r"\bdo\s+not\s+follow\s+(your|the)\s+(rules|instructions)\b", re.I),
    re.compile(
        r"\boverride\s+(your|the|all)\s+(rules|instructions|restrictions)\b", re.I
    ),
    re.compile(r"\bact\s+as\s+(if\s+)?(you\s+)?(are|were)\b", re.I),
    re.compile(
        r"reveal\s+(your|the)\s+(system|original)\s+(prompt|instructions)", re.I
    ),
    re.compile(r"print\s+(your|the)\s+(system|original)\s+(prompt|instructions)", re.I),
    re.compile(r"what\s+(is|are)\s+your\s+(system\s+)?(prompt|instructions)", re.I),
]

INJECTION_DETECTED_RESPONSE = (
    "I'm unable to process that request. I'm a clinical trials research assistant "
    "— please ask me a question about clinical trials, medical research, or "
    "health conditions."
)


def detect_prompt_injection(text: str) -> bool:
    """Return True if the text contains likely prompt injection patterns."""
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            logger.warning(f"Prompt injection pattern detected: {pattern.pattern}")
            return True
    return False


# ---------------------------------------------------------------------------
# 3. Deterministic SQL validation
# ---------------------------------------------------------------------------

_DML_PATTERN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|EXEC|EXECUTE)\b",
    re.I,
)

_ALLOWED_TABLES = {t.lower() for t in AACT_TABLES}
# Also allow schema-qualified names
_ALLOWED_QUALIFIED = {f"ctgov.{t}" for t in _ALLOWED_TABLES}


class SQLValidationError(Exception):
    """Raised when a SQL query fails guardrail validation."""


def validate_sql_query(query: str) -> str:
    """Validate a SQL query before execution.

    Checks:
    1. No DML/DDL statements (INSERT, UPDATE, DELETE, DROP, etc.)
    2. Must be a single SELECT statement
    3. All referenced tables must be in the AACT allowlist

    Returns the query unchanged if valid; raises SQLValidationError otherwise.
    """
    if not query or not query.strip():
        raise SQLValidationError("Empty query")

    # Check 1: Block DML/DDL
    if _DML_PATTERN.search(query):
        logger.warning(f"DML/DDL statement blocked: {query[:200]}")
        raise SQLValidationError(
            "Only SELECT queries are allowed. "
            "DML/DDL statements (INSERT, UPDATE, DELETE, DROP, etc.) are blocked."
        )

    # Check 2: Parse and verify it's a single SELECT
    parsed = sqlparse.parse(query)
    # Filter out empty/whitespace-only statements
    statements = [s for s in parsed if s.get_type() is not None]
    if len(statements) != 1:
        raise SQLValidationError(
            f"Expected exactly one SQL statement, got {len(statements)}."
        )

    stmt = statements[0]
    stmt_type = stmt.get_type()
    if stmt_type != "SELECT":
        raise SQLValidationError(
            f"Only SELECT statements are allowed, got: {stmt_type}"
        )

    # Check 3: Verify all referenced tables are in the allowlist
    # CTE aliases (WITH x AS ...) are valid table references, not real tables
    tables = _extract_table_names(query)
    cte_names = _extract_cte_names(query)
    disallowed = tables - _ALLOWED_TABLES - _ALLOWED_QUALIFIED - cte_names
    if disallowed:
        logger.warning(f"Query references disallowed tables: {disallowed}")
        raise SQLValidationError(
            f"Query references tables not in the allowlist: {', '.join(sorted(disallowed))}"
        )

    return query


def _extract_cte_names(query: str) -> set[str]:
    """Extract CTE alias names from WITH clauses."""
    cte_pattern = re.compile(r"\bWITH\b\s+(\w+)\s+AS\s*\(", re.I)
    # Also match comma-separated CTEs: WITH a AS (...), b AS (...)
    cte_continuation = re.compile(r"\)\s*,\s*(\w+)\s+AS\s*\(", re.I)
    names = {m.group(1).lower() for m in cte_pattern.finditer(query)}
    names |= {m.group(1).lower() for m in cte_continuation.finditer(query)}
    return names


def _extract_table_names(query: str) -> set[str]:
    """Extract table names from a SQL query.

    Looks for identifiers following FROM and JOIN keywords, handling:
    - Unquoted: FROM ctgov.studies s
    - Double-quoted: FROM "ctgov"."studies"
    - Mixed: FROM ctgov."studies"
    - Backtick-quoted: FROM `ctgov`.`studies`
    - Bracket-quoted: FROM [ctgov].[studies]
    """
    tables = set()

    # Pattern for a single identifier: quoted or unquoted
    _ident = r'(?:"[^"]+"|`[^`]+`|\[[^\]]+\]|[a-zA-Z_][a-zA-Z0-9_]*)'
    # Schema-qualified or plain identifier after FROM/JOIN
    table_ref_pattern = re.compile(
        rf"(?:FROM|JOIN)\s+({_ident}(?:\.{_ident})?)",
        re.I,
    )

    for match in table_ref_pattern.finditer(query):
        raw = match.group(1)
        # Strip quotes/brackets from each part and rejoin
        parts = raw.split(".")
        normalized = ".".join(_strip_quotes(p) for p in parts).lower()
        tables.add(normalized)

    return tables


def _strip_quotes(identifier: str) -> str:
    """Strip surrounding double quotes, backticks, or square brackets."""
    if len(identifier) >= 2:
        if (identifier[0] == '"' and identifier[-1] == '"') or (
            identifier[0] == "`" and identifier[-1] == "`"
        ):
            return identifier[1:-1]
        if identifier[0] == "[" and identifier[-1] == "]":
            return identifier[1:-1]
    return identifier
