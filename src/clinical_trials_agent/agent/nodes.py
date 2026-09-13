"""Node functions for the LangGraph agent."""

import hashlib
import logging

from langchain_core.messages import AIMessage, AnyMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState

from clinical_trials_agent.agent.guardrails import (
    INJECTION_DETECTED_RESPONSE,
    OFF_TOPIC_RESPONSE,
    TOPIC_CLASSIFIER_PROMPT,
    SQLValidationError,
    detect_prompt_injection,
    validate_sql_query,
)
from clinical_trials_agent.agent.prompts import (
    CHECK_QUERY_SYSTEM_PROMPT,
    GENERATE_QUERY_SYSTEM_PROMPT,
)
from clinical_trials_agent.config import get_settings

logger = logging.getLogger(__name__)


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
    Tracing callbacks are inherited from the graph run config.
    """
    from openai import RateLimitError

    user_key = config.get("configurable", {}).get("openai_api_key") if config else None

    # If user provided a key, use it directly (they likely hit rate limit before)
    if user_key:
        logger.info("Using user-provided OpenAI API key")
        llm = _get_llm(config, use_fallback=True)
        return llm_func(llm)

    # Otherwise try server key, with no fallback available
    try:
        llm = _get_llm(config, use_fallback=False)
        return llm_func(llm)
    except RateLimitError:
        logger.error("Server API key rate limited and no user key available")
        raise


INTERRUPTED_TOOL_CALL_CONTENT = "Tool call was interrupted and did not complete."


def repair_dangling_tool_calls(messages: list[AnyMessage]) -> list[AnyMessage]:
    """Give every unanswered tool call a placeholder ToolMessage.

    A run that aborts between an LLM tool call and its tool execution (client
    disconnect, recursion limit, exception) checkpoints an AIMessage whose
    tool calls have no responses. OpenAI rejects any later request containing
    that history, which would break the conversation permanently. This returns
    a copy for the LLM request; checkpointed state is left untouched.
    """
    answered = {m.tool_call_id for m in messages if isinstance(m, ToolMessage)}
    repaired: list[AnyMessage] = []
    pending: list[str] = []

    def flush_pending() -> None:
        repaired.extend(
            ToolMessage(content=INTERRUPTED_TOOL_CALL_CONTENT, tool_call_id=call_id)
            for call_id in pending
        )
        pending.clear()

    for msg in messages:
        # Tool responses must directly follow their AIMessage, so insert
        # placeholders once the run of tool messages ends.
        if pending and not isinstance(msg, ToolMessage):
            flush_pending()
        repaired.append(msg)
        if isinstance(msg, AIMessage) and msg.tool_calls:
            pending = [tc["id"] for tc in msg.tool_calls if tc["id"] not in answered]
    flush_pending()
    return repaired


def create_topic_guardrail_node():
    """Create a node that checks if the user's question is on-topic.

    This runs before the main pipeline. It:
    1. Checks for prompt injection patterns (deterministic, fast)
    2. Classifies whether the question is about clinical trials (LLM call)

    If off-topic or injection detected, appends an AIMessage so the
    downstream router (which checks last message type) short-circuits to END.
    If on-topic, returns nothing — the last message stays as the user's
    HumanMessage and the router proceeds to list_tables.
    """

    def topic_guardrail(state: MessagesState, config: RunnableConfig) -> dict:
        # Find the latest user message
        user_message = ""
        for msg in reversed(state["messages"]):
            if hasattr(msg, "type") and msg.type == "human":
                user_message = msg.content
                break
            elif isinstance(msg, dict) and msg.get("role") == "user":
                user_message = msg["content"]
                break

        if not user_message:
            return {}

        msg_fingerprint = hashlib.sha256(user_message.encode()).hexdigest()[:12]

        # Fast check: prompt injection detection (no LLM needed)
        if detect_prompt_injection(user_message):
            logger.warning(
                "Prompt injection blocked (msg_hash=%s, len=%d)",
                msg_fingerprint,
                len(user_message),
            )
            return {
                "messages": [AIMessage(content=INJECTION_DETECTED_RESPONSE)],
            }

        # LLM-based topic classification
        logger.info("Node: topic_guardrail - Classifying user intent")

        def invoke_llm(llm: ChatOpenAI):
            return llm.invoke(
                [
                    {"role": "system", "content": TOPIC_CLASSIFIER_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                config,
            )

        response = _invoke_with_fallback(invoke_llm, config)
        raw_classification = response.content.strip().strip(".").lower()
        # Extract first token for exact match — reject ambiguous outputs
        first_token = raw_classification.split()[0] if raw_classification else ""
        logger.info(
            "Topic classification: '%s' (msg_hash=%s, len=%d)",
            first_token,
            msg_fingerprint,
            len(user_message),
        )

        if first_token != "yes":
            logger.info("Off-topic query blocked by guardrail")
            return {
                "messages": [AIMessage(content=OFF_TOPIC_RESPONSE)],
            }

        # On-topic: return nothing, last message stays as the user's HumanMessage
        return {}

    return topic_guardrail


# Prefix of the pipeline's table-list AIMessage. It is LLM context, not an
# answer, so the conversation history endpoint hides messages starting with it.
TABLE_LIST_PREFIX = "Available tables in the AACT database: "


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
        response = AIMessage(content=f"{TABLE_LIST_PREFIX}{tool_message.content}")
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

        def invoke_llm(llm: ChatOpenAI):
            llm_with_tools = llm.bind_tools([get_schema_tool], tool_choice="any")
            return llm_with_tools.invoke(
                repair_dangling_tool_calls(state["messages"]), config
            )

        response = _invoke_with_fallback(invoke_llm, config)
        logger.debug(f"LLM response tool calls: {response.tool_calls}")
        return {"messages": [response]}

    return call_get_schema


def create_generate_query_node(
    run_query_tool: BaseTool,
    api_search_tool: BaseTool | None = None,
    top_k: int = 10,
):
    """Create a node that generates SQL queries."""
    bound_tools = [run_query_tool]
    if api_search_tool:
        bound_tools.append(api_search_tool)

    def generate_query(state: MessagesState, config: RunnableConfig) -> dict:
        """Generate a SQL query based on the user's question and schema."""
        logger.info("Node: generate_query - Generating SQL query")

        system_prompt = GENERATE_QUERY_SYSTEM_PROMPT.format(top_k=top_k)
        system_message = {
            "role": "system",
            "content": system_prompt,
        }
        logger.debug(f"System prompt: {system_prompt[:500]}...")

        def invoke_llm(llm: ChatOpenAI):
            llm_with_tools = llm.bind_tools(bound_tools)
            return llm_with_tools.invoke(
                [system_message, *repair_dangling_tool_calls(state["messages"])],
                config,
            )

        response = _invoke_with_fallback(invoke_llm, config)
        if response.tool_calls:
            tool_name = response.tool_calls[0].get("name", "N/A")
            arg_keys = list(response.tool_calls[0].get("args", {}).keys())
            logger.info("Tool call: %s, arg_keys: %s", tool_name, arg_keys)
        else:
            logger.info("LLM response (no tool call), length=%d", len(response.content))
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

        def invoke_llm(llm: ChatOpenAI):
            llm_with_tools = llm.bind_tools([run_query_tool], tool_choice="any")
            return llm_with_tools.invoke([system_message, user_message], config)

        response = _invoke_with_fallback(invoke_llm, config)
        # Preserve the message ID for proper graph flow
        response.id = state["messages"][-1].id

        if response.tool_calls:
            validated_query = response.tool_calls[0].get("args", {}).get("query", "")
            if validated_query != original_query:
                logger.info(f"Query modified by checker: {validated_query}")
            else:
                logger.debug("Query validated without changes")

            # Deterministic SQL guardrail: validate before execution
            try:
                validate_sql_query(validated_query)
            except SQLValidationError as e:
                logger.warning(f"SQL guardrail blocked query: {e}")
                # Replace the tool call with a plain AIMessage (no tool_calls)
                # so the router sends back to generate_query instead of run_query
                return {
                    "messages": [
                        AIMessage(
                            content=f"I'm unable to execute that query because it "
                            f"failed a safety check: {e}. Let me try a different "
                            f"approach.",
                            id=state["messages"][-1].id,
                        )
                    ],
                }

        return {"messages": [response]}

    return check_query
