"""SQL tools setup for the agent."""

from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI

from clinical_trials_agent.config import get_settings
from clinical_trials_agent.database import get_database


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
