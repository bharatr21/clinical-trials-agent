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
from clinical_trials_agent.agent.tools import (
    get_ctgov_search_tool,
    get_sql_tools,
    get_tool_by_name,
)
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

        # Create connection pool for runtime use.
        # The managed Postgres (or its proxy) drops idle connections, so
        # validate connections on checkout, recycle idle/old ones, and enable
        # TCP keepalives. Otherwise the pool hands out dead connections and the
        # first checkpointer read fails with "server closed the connection".
        _pool = AsyncConnectionPool(
            conninfo=settings.app_database_url,
            open=False,
            check=AsyncConnectionPool.check_connection,
            max_idle=60,
            max_lifetime=30 * 60,
            reconnect_timeout=60,
            kwargs={
                "autocommit": True,
                "prepare_threshold": 0,
                "keepalives": 1,
                "keepalives_idle": 30,
                "keepalives_interval": 10,
                "keepalives_count": 3,
            },
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


def should_continue_after_guardrail(
    state: MessagesState,
) -> Literal["list_tables", "__end__"]:
    """Route after topic guardrail: proceed or short-circuit.

    The topic_guardrail node is the first node after START. If it blocked the
    query (off-topic or injection), it appended an AIMessage. If it passed,
    the last message is still the user's HumanMessage. We check message type
    instead of a state flag to avoid stickiness across checkpointed turns.
    """
    messages = state.get("messages", [])
    if not messages:
        return "list_tables"
    last_message = messages[-1]
    # If the guardrail appended a response, the last message is an AIMessage
    if hasattr(last_message, "type") and last_message.type == "ai":
        return END
    return "list_tables"


def should_continue_after_check(
    state: MessagesState,
) -> Literal["run_query", "generate_query"]:
    """Route after check_query: run the query or retry generation.

    If SQL validation passed, the response has tool_calls (the validated query).
    If it failed, the response is a plain AIMessage with no tool_calls.
    """
    messages = state.get("messages", [])
    if not messages:
        return "generate_query"
    last_message = messages[-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "run_query"
    return "generate_query"


_TOOL_ROUTES: dict[str, str] = {
    "sql_db_query": "check_query",
    "search_clinicaltrials_api": "api_search",
}


def should_continue(
    state: MessagesState,
) -> Literal["check_query", "api_search", "__end__"]:
    """Determine whether to check the query, search the API, or end.

    Routes based on which tool the LLM called:
    - sql_db_query → check_query (validate SQL before running)
    - search_clinicaltrials_api → api_search (external API fallback)
    - no tool call → END (LLM provided final answer)
    """
    messages = state.get("messages", [])
    if not messages:
        return END
    last_message = messages[-1]
    if not last_message.tool_calls:
        return END
    tool_name = last_message.tool_calls[0].get("name", "")
    route = _TOOL_ROUTES.get(tool_name)
    if route is None:
        logger.warning("Unexpected tool call '%s', ending conversation", tool_name)
        return END
    return route  # type: ignore[return-value]


def _build_agent_graph() -> StateGraph:
    """Build the SQL agent graph (uncompiled).

    Graph flow:
    START → topic_guardrail → [on-topic?]
                                ↓ no → END (off-topic response already in messages)
                                ↓ yes
                              list_tables → call_get_schema → get_schema → generate_query
                                                                                ↓
                                                                          [which tool?]
                                                                     ↓         ↓           ↓
                                                                check_query  api_search   END
                                                                     ↓         ↓
                                                               [valid SQL?]  generate_query
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
    api_search_tool = get_ctgov_search_tool()

    # Create tool nodes
    get_schema_node = ToolNode([get_schema_tool], name="get_schema")
    run_query_node = ToolNode([run_query_tool], name="run_query")
    api_search_node = ToolNode([api_search_tool], name="api_search")

    # Create function nodes
    topic_guardrail = create_topic_guardrail_node()
    list_tables = create_list_tables_node(list_tables_tool)
    call_get_schema = create_call_get_schema_node(get_schema_tool)
    generate_query = create_generate_query_node(run_query_tool, api_search_tool)
    check_query = create_check_query_node(run_query_tool)

    # Build the graph
    builder = StateGraph(MessagesState)

    # Add nodes
    builder.add_node("topic_guardrail", topic_guardrail)
    builder.add_node("list_tables", list_tables)
    builder.add_node("call_get_schema", call_get_schema)
    builder.add_node(get_schema_node, "get_schema")
    builder.add_node("generate_query", generate_query)
    builder.add_node("check_query", check_query)
    builder.add_node(run_query_node, "run_query")
    builder.add_node(api_search_node, "api_search")

    # Add edges
    builder.add_edge(START, "topic_guardrail")
    builder.add_conditional_edges("topic_guardrail", should_continue_after_guardrail)
    builder.add_edge("list_tables", "call_get_schema")
    builder.add_edge("call_get_schema", "get_schema")
    builder.add_edge("get_schema", "generate_query")
    builder.add_conditional_edges("generate_query", should_continue)
    builder.add_conditional_edges("check_query", should_continue_after_check)
    builder.add_edge("run_query", "generate_query")
    builder.add_edge("api_search", "generate_query")

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
