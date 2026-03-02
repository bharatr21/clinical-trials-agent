"""SQL tools setup for the agent."""

import logging
import re

from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_core.tools import BaseTool, StructuredTool
from langchain_openai import ChatOpenAI

from clinical_trials_agent.agent.ctgov_api import search_ctgov
from clinical_trials_agent.config import get_settings
from clinical_trials_agent.database import get_database

logger = logging.getLogger(__name__)

_NCT_ID_PATTERN = re.compile(r"^NCT\d{8}$")


def get_sql_tools() -> list[BaseTool]:
    """Get SQL database tools for the agent.

    Returns a list of tools:
    - sql_db_list_tables: List available tables
    - sql_db_schema: Get schema for specified tables
    - sql_db_query: Execute SQL queries
    - sql_db_query_checker: Validate queries before execution
    """
    settings = get_settings()
    db = get_database()

    # The toolkit needs an LLM for the query checker tool
    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0,
    )

    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    return toolkit.get_tools()


def get_tool_by_name(tools: list[BaseTool], name: str) -> BaseTool:
    """Get a specific tool by name from the tools list."""
    for tool in tools:
        if tool.name == name:
            return tool
    raise ValueError(f"Tool '{name}' not found in tools list")


async def _search_clinicaltrials_api(
    condition: str = "", term: str = "", intervention: str = ""
) -> str:
    """Search the ClinicalTrials.gov API as a last-resort fallback.

    Use this tool ONLY after database searches (MeSH terms, conditions,
    keywords, and brief_title) all returned 0 results. Returns NCT IDs
    that can be used in a SQL WHERE s.nct_id IN (...) clause.
    """
    result = await search_ctgov(
        condition=condition, term=term, intervention=intervention
    )

    if not result["nct_ids"]:
        return "No results found on ClinicalTrials.gov API either."

    # Validate NCT IDs to prevent SQL injection via crafted API responses
    valid_ids = [nct for nct in result["nct_ids"] if _NCT_ID_PATTERN.match(nct)]
    invalid_count = len(result["nct_ids"]) - len(valid_ids)
    if invalid_count:
        logger.warning("Filtered %d invalid NCT IDs from API response", invalid_count)
    if not valid_ids:
        return "No valid NCT IDs returned from ClinicalTrials.gov API."

    nct_list = ", ".join(f"'{nct}'" for nct in valid_ids)
    truncation_note = ""
    if result["was_truncated"]:
        truncation_note = (
            f" (showing {len(valid_ids)} of {result['total_count']} total)"
        )

    return (
        f"ClinicalTrials.gov API found {result['total_count']} studies{truncation_note} "
        f"({len(valid_ids)} valid IDs).\n"
        f"Use these NCT IDs in your SQL query: WHERE s.nct_id IN ({nct_list})"
    )


def get_ctgov_search_tool() -> StructuredTool:
    """Create the ClinicalTrials.gov API search tool."""
    return StructuredTool.from_function(
        coroutine=_search_clinicaltrials_api,
        name="search_clinicaltrials_api",
        description=(
            "Search ClinicalTrials.gov API for studies by condition, term, or "
            "intervention. Use as a LAST RESORT after all database text searches "
            "(MeSH terms, conditions, keywords, brief_title) return 0 results. "
            "Returns NCT IDs to use in SQL WHERE s.nct_id IN (...) clause."
        ),
    )
