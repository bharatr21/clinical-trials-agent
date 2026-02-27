"""Node functions for the LangGraph agent."""

import logging

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler as LangfuseCallbackHandler
from langgraph.graph import MessagesState

from clinical_trials_agent.agent.prompts import (
    CHECK_QUERY_SYSTEM_PROMPT,
    GENERATE_QUERY_SYSTEM_PROMPT,
)
from clinical_trials_agent.config import get_settings

logger = logging.getLogger(__name__)

_langfuse_initialized = False


def _ensure_langfuse_client() -> bool:
    """Initialize the global Langfuse client once. Returns True if configured."""
    global _langfuse_initialized
    if _langfuse_initialized:
        return True

    settings = get_settings()
    if not settings.langfuse_secret_key or not settings.langfuse_public_key:
        return False

    Langfuse(
        secret_key=settings.langfuse_secret_key,
        public_key=settings.langfuse_public_key,
        host=settings.langfuse_base_url,
    )
    _langfuse_initialized = True
    return True


def _get_langfuse_handler(
    config: RunnableConfig | None = None,
) -> tuple[LangfuseCallbackHandler | None, dict]:
    """Create a Langfuse callback handler and metadata if configured."""
    if not _ensure_langfuse_client():
        return None, {}

    configurable = config.get("configurable", {}) if config else {}
    metadata = {
        "langfuse_user_id": configurable.get("client_id"),
        "langfuse_session_id": configurable.get("thread_id"),
    }

    return LangfuseCallbackHandler(), metadata


def _get_llm(
    config: RunnableConfig | None = None, use_fallback: bool = False
) -> ChatOpenAI:
    """Create an LLM instance with fallback to user-provided API key."""
    settings = get_settings()
    user_key = config.get("configurable", {}).get("openai_api_key") if config else None

    # Use server key by default, switch to user key on fallback (after rate limit)
    if use_fallback and user_key:
        logger.info("Using user-provided OpenAI API key (fallback)")
        api_key = user_key
    else:
        api_key = settings.openai_api_key

    return ChatOpenAI(
        model=settings.openai_model,
        api_key=api_key,
        temperature=0,
    )


def _invoke_with_fallback(llm_func, config: RunnableConfig | None = None):
    """Invoke an LLM function with automatic fallback on rate limit errors.

    If user provided an API key, use it directly (skip server key).
    Otherwise, use server key and fall back to user key on rate limit.
    Langfuse callback is injected automatically for tracing.
    """
    from openai import RateLimitError

    user_key = config.get("configurable", {}).get("openai_api_key") if config else None

    langfuse_handler, langfuse_metadata = _get_langfuse_handler(config)
    callbacks = [langfuse_handler] if langfuse_handler else []

    # If user provided a key, use it directly (they likely hit rate limit before)
    if user_key:
        logger.info("Using user-provided OpenAI API key")
        llm = _get_llm(config, use_fallback=True)
        return llm_func(llm, callbacks, langfuse_metadata)

    # Otherwise try server key, with no fallback available
    try:
        llm = _get_llm(config, use_fallback=False)
        return llm_func(llm, callbacks, langfuse_metadata)
    except RateLimitError:
        logger.error("Server API key rate limited and no user key available")
        raise


def create_list_tables_node(list_tables_tool: BaseTool):
    """Create a node that lists available database tables."""

    def list_tables(state: MessagesState) -> dict:  # noqa: ARG001
        """List available tables in the AACT database."""
        logger.info("Node: list_tables - Fetching available tables")
        tool_call = {
            "name": "sql_db_list_tables",
            "args": {},
            "id": "list_tables_call",
            "type": "tool_call",
        }
        tool_call_message = AIMessage(content="", tool_calls=[tool_call])
        tool_message = list_tables_tool.invoke(tool_call)
        logger.debug(f"Available tables: {tool_message.content}")
        response = AIMessage(
            content=f"Available tables in the AACT database: {tool_message.content}"
        )
        return {"messages": [tool_call_message, tool_message, response]}

    return list_tables


def create_call_get_schema_node(get_schema_tool: BaseTool):
    """Create a node that asks the LLM to select relevant tables for schema retrieval."""

    def call_get_schema(state: MessagesState, config: RunnableConfig) -> dict:
        """Have LLM select which tables to get schema for."""
        logger.info("Node: call_get_schema - LLM selecting relevant tables")
        logger.debug(
            f"Messages to LLM: {[m.content if hasattr(m, 'content') else str(m) for m in state['messages']]}"
        )

        def invoke_llm(llm: ChatOpenAI, callbacks: list, metadata: dict):
            llm_with_tools = llm.bind_tools([get_schema_tool], tool_choice="any")
            return llm_with_tools.invoke(
                state["messages"],
                config={"callbacks": callbacks, "metadata": metadata},
            )

        response = _invoke_with_fallback(invoke_llm, config)
        logger.debug(f"LLM response tool calls: {response.tool_calls}")
        return {"messages": [response]}

    return call_get_schema


def create_generate_query_node(run_query_tool: BaseTool, top_k: int = 10):
    """Create a node that generates SQL queries."""

    def generate_query(state: MessagesState, config: RunnableConfig) -> dict:
        """Generate a SQL query based on the user's question and schema."""
        logger.info("Node: generate_query - Generating SQL query")

        system_prompt = GENERATE_QUERY_SYSTEM_PROMPT.format(top_k=top_k)
        system_message = {
            "role": "system",
            "content": system_prompt,
        }
        logger.debug(f"System prompt: {system_prompt[:500]}...")

        def invoke_llm(llm: ChatOpenAI, callbacks: list, metadata: dict):
            llm_with_tools = llm.bind_tools([run_query_tool])
            return llm_with_tools.invoke(
                [system_message, *state["messages"]],
                config={"callbacks": callbacks, "metadata": metadata},
            )

        response = _invoke_with_fallback(invoke_llm, config)
        if response.tool_calls:
            logger.info(
                f"Generated SQL: {response.tool_calls[0].get('args', {}).get('query', 'N/A')}"
            )
        else:
            logger.info(f"LLM response (no tool call): {response.content[:200]}...")
        return {"messages": [response]}

    return generate_query


def create_check_query_node(run_query_tool: BaseTool):
    """Create a node that validates SQL queries before execution."""

    def check_query(state: MessagesState, config: RunnableConfig) -> dict:
        """Validate and potentially fix the SQL query."""
        logger.info("Node: check_query - Validating SQL query")

        system_message = {
            "role": "system",
            "content": CHECK_QUERY_SYSTEM_PROMPT,
        }

        # Extract the query from the last tool call
        tool_call = state["messages"][-1].tool_calls[0]
        original_query = tool_call["args"]["query"]
        user_message = {"role": "user", "content": original_query}
        logger.debug(f"Query to validate: {original_query}")

        def invoke_llm(llm: ChatOpenAI, callbacks: list, metadata: dict):
            llm_with_tools = llm.bind_tools([run_query_tool], tool_choice="any")
            return llm_with_tools.invoke(
                [system_message, user_message],
                config={"callbacks": callbacks, "metadata": metadata},
            )

        response = _invoke_with_fallback(invoke_llm, config)
        # Preserve the message ID for proper graph flow
        response.id = state["messages"][-1].id

        if response.tool_calls:
            validated_query = response.tool_calls[0].get("args", {}).get("query", "")
            if validated_query != original_query:
                logger.info(f"Query modified by checker: {validated_query}")
            else:
                logger.debug("Query validated without changes")

        return {"messages": [response]}

    return check_query
