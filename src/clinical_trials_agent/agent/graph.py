"""LangGraph StateGraph for the SQL agent."""

import logging
from typing import Literal

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode
from psycopg_pool import AsyncConnectionPool

from clinical_trials_agent.agent.nodes import (
    create_call_get_schema_node,
    create_check_query_node,
    create_generate_query_node,
    create_list_tables_node,
    create_topic_guardrail_node,
)
from clinical_trials_agent.agent.tools import get_sql_tools, get_tool_by_name
from clinical_trials_agent.config import get_settings

logger = logging.getLogger(__name__)

_pool: AsyncConnectionPool | None = None
_checkpointer: AsyncPostgresSaver | None = None


async def init_checkpointer() -> AsyncPostgresSaver:
    """Initialize the PostgreSQL checkpointer for conversation persistence.

    This should be called once at application startup.
    """
    global _pool, _checkpointer

    if _checkpointer is None:
        settings = get_settings()

        # Run setup with a separate autocommit connection
        # (required for CREATE INDEX CONCURRENTLY)
        import psycopg

        async with await psycopg.AsyncConnection.connect(
            settings.app_database_url, autocommit=True
        ) as conn:
            temp_checkpointer = AsyncPostgresSaver(conn=conn)
            await temp_checkpointer.setup()
            logger.info("LangGraph checkpoint tables created")

        # Create connection pool for runtime use
        _pool = AsyncConnectionPool(
            conninfo=settings.app_database_url,
            open=False,
        )
        await _pool.open()

        # Create checkpointer from pool
        _checkpointer = AsyncPostgresSaver(conn=_pool)
        logger.info("LangGraph checkpointer initialized")

    return _checkpointer


async def close_checkpointer() -> None:
    """Close the checkpointer connection pool."""
    global _pool, _checkpointer

    if _pool is not None:
        await _pool.close()
        _pool = None
        _checkpointer = None
        logger.info("LangGraph checkpointer closed")


def get_checkpointer() -> AsyncPostgresSaver | None:
    """Get the initialized checkpointer instance."""
    return _checkpointer


class AgentState(MessagesState):
    """Extended state that includes guardrail flags."""

    guardrail_block: bool = False
    sql_validation_failed: bool = False


def should_continue_after_guardrail(
    state: AgentState,
) -> Literal["list_tables", "__end__"]:
    """Route after topic guardrail: proceed or short-circuit."""
    if state.get("guardrail_block"):
        return END
    return "list_tables"


def should_continue_after_check(
    state: AgentState,
) -> Literal["run_query", "generate_query"]:
    """Route after check_query: run the query or retry generation on validation failure."""
    if state.get("sql_validation_failed"):
        return "generate_query"
    return "run_query"


def should_continue(state: AgentState) -> Literal["check_query", "__end__"]:
    """Determine whether to check the query or end the conversation.

    If the LLM generated a tool call (SQL query), route to check_query.
    If no tool call (LLM provided final answer), end the conversation.
    """
    messages = state["messages"]
    last_message = messages[-1]
    if not last_message.tool_calls:
        return END
    return "check_query"


def _build_agent_graph() -> StateGraph:
    """Build the SQL agent graph (uncompiled).

    Graph flow:
    START → topic_guardrail → [on-topic?]
                                ↓ no → END (off-topic response already in messages)
                                ↓ yes
                              list_tables → call_get_schema → get_schema → generate_query
                                                                                ↓
                                                                          [has tool call?]
                                                                           ↓         ↓
                                                                      check_query    END
                                                                           ↓
                                                                     [valid SQL?]
                                                                      ↓         ↓
                                                                 run_query   generate_query (retry)
                                                                           ↓
                                                                     generate_query
    """
    # Get tools
    tools = get_sql_tools()
    list_tables_tool = get_tool_by_name(tools, "sql_db_list_tables")
    get_schema_tool = get_tool_by_name(tools, "sql_db_schema")
    run_query_tool = get_tool_by_name(tools, "sql_db_query")

    # Create tool nodes
    get_schema_node = ToolNode([get_schema_tool], name="get_schema")
    run_query_node = ToolNode([run_query_tool], name="run_query")

    # Create function nodes
    topic_guardrail = create_topic_guardrail_node()
    list_tables = create_list_tables_node(list_tables_tool)
    call_get_schema = create_call_get_schema_node(get_schema_tool)
    generate_query = create_generate_query_node(run_query_tool)
    check_query = create_check_query_node(run_query_tool)

    # Build the graph
    builder = StateGraph(AgentState)

    # Add nodes
    builder.add_node("topic_guardrail", topic_guardrail)
    builder.add_node("list_tables", list_tables)
    builder.add_node("call_get_schema", call_get_schema)
    builder.add_node(get_schema_node, "get_schema")
    builder.add_node("generate_query", generate_query)
    builder.add_node("check_query", check_query)
    builder.add_node(run_query_node, "run_query")

    # Add edges
    builder.add_edge(START, "topic_guardrail")
    builder.add_conditional_edges("topic_guardrail", should_continue_after_guardrail)
    builder.add_edge("list_tables", "call_get_schema")
    builder.add_edge("call_get_schema", "get_schema")
    builder.add_edge("get_schema", "generate_query")
    builder.add_conditional_edges("generate_query", should_continue)
    builder.add_conditional_edges("check_query", should_continue_after_check)
    builder.add_edge("run_query", "generate_query")

    return builder


def create_agent(checkpointer: AsyncPostgresSaver | None = None) -> CompiledStateGraph:
    """Create and compile the SQL agent graph with optional checkpointer.

    Args:
        checkpointer: Optional checkpointer for conversation persistence.
                     If None, uses the global checkpointer if initialized.

    Returns:
        Compiled StateGraph ready for invocation.
    """
    builder = _build_agent_graph()
    cp = checkpointer or _checkpointer
    return builder.compile(checkpointer=cp)
