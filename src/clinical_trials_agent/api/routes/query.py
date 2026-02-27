"""Query endpoint for the clinical trials agent."""

import json
import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from clinical_trials_agent.agent import create_agent
from clinical_trials_agent.api.dependencies import get_client_id, get_openai_api_key
from clinical_trials_agent.api.rate_limit import limiter
from clinical_trials_agent.database import get_app_db_session
from clinical_trials_agent.models import Conversation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["query"])


def _get_openai_error_code(error: Exception) -> str:
    """Extract the specific error code from an OpenAI error."""
    from openai import RateLimitError

    rate_error = (
        error
        if isinstance(error, RateLimitError)
        else getattr(error, "__cause__", None)
    )

    if not isinstance(rate_error, RateLimitError):
        return "rate_limit"

    body = getattr(rate_error, "body", None) or {}
    if not isinstance(body, dict):
        return "rate_limit"

    error_info = body.get("error", {})
    code = error_info.get("code") or error_info.get("type")
    if code == "insufficient_quota":
        return "insufficient_quota"

    return "rate_limit"


class QueryRequest(BaseModel):
    """Request model for query endpoint."""

    question: str = Field(
        ...,
        description="Natural language question about clinical trials",
        min_length=1,
        max_length=1000,
        examples=["How many lung cancer trials are recruiting?"],
    )
    conversation_id: str | None = Field(
        None,
        description="Optional conversation ID to continue an existing conversation",
    )


class QueryResponse(BaseModel):
    """Response model for query endpoint."""

    answer: str = Field(..., description="Natural language answer to the question")
    sql_query: str | None = Field(
        None, description="The SQL query that was executed (if any)"
    )
    conversation_id: str = Field(
        ..., description="The conversation ID for this session"
    )


def _extract_response(result: dict) -> tuple[str, str | None]:
    """Extract answer and SQL query from agent result."""
    answer = ""
    sql_query = None

    for message in reversed(result["messages"]):
        tool_calls = getattr(message, "tool_calls", None)
        if tool_calls:
            for tool_call in tool_calls:
                if tool_call.get("name") == "sql_db_query" and not sql_query:
                    sql_query = tool_call.get("args", {}).get("query")
        elif hasattr(message, "content") and message.content and not answer:
            answer = message.content

    return answer or "I was unable to generate an answer for your question.", sql_query


async def _save_conversation_metadata(
    conversation_id: str, title: str, client_id: str, is_new: bool = False
) -> None:
    """Save or update conversation metadata."""
    async with get_app_db_session() as session:
        conv_uuid = uuid.UUID(conversation_id)

        if is_new:
            # Truncate title to 100 chars for display
            display_title = title[:100] + "..." if len(title) > 100 else title
            conversation = Conversation(
                id=conv_uuid, title=display_title, client_id=client_id
            )
            session.add(conversation)
        else:
            # Update the updated_at timestamp
            result = await session.execute(
                select(Conversation).where(Conversation.id == conv_uuid)
            )
            conversation = result.scalar_one_or_none()
            if conversation:
                conversation.updated_at = datetime.now(UTC)


@router.post("/query", response_model=QueryResponse)
@limiter.limit("20/minute")
async def query_clinical_trials(
    request: Request,  # noqa: ARG001 — required by slowapi
    query: QueryRequest,
    client_id: str = Depends(get_client_id),
    openai_api_key: str | None = Depends(get_openai_api_key),
) -> QueryResponse:
    """Query the AACT clinical trials database using natural language.

    This endpoint accepts a natural language question about clinical trials
    and returns an answer along with the SQL query that was generated.

    If a conversation_id is provided, the agent will have access to the
    previous conversation context.

    Users can optionally provide their own OpenAI API key via the
    X-OpenAI-API-Key header to use instead of the server's default key.
    """
    try:
        # Get or create conversation ID
        is_new_conversation = query.conversation_id is None
        conversation_id = query.conversation_id or str(uuid.uuid4())

        logger.info(
            f"Processing query: {query.question[:100]}... "
            f"(conversation: {conversation_id}, new: {is_new_conversation}, user_key: {openai_api_key is not None})"
        )

        agent = create_agent()
        config: dict = {
            "configurable": {"thread_id": conversation_id, "client_id": client_id}
        }
        if openai_api_key:
            config["configurable"]["openai_api_key"] = openai_api_key

        # Run the agent (async invocation with checkpointer)
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": query.question}]},
            config,
        )

        # Save conversation metadata
        await _save_conversation_metadata(
            conversation_id, query.question, client_id, is_new=is_new_conversation
        )

        # Extract the response
        answer, sql_query = _extract_response(result)

        return QueryResponse(
            answer=answer, sql_query=sql_query, conversation_id=conversation_id
        )

    except Exception as e:
        logger.exception(f"Error processing query: {e}")
        from openai import AuthenticationError, RateLimitError

        cause = getattr(e, "__cause__", None)

        if isinstance(e, AuthenticationError) or isinstance(cause, AuthenticationError):
            raise HTTPException(status_code=401, detail="invalid_api_key") from e

        if isinstance(e, RateLimitError) or isinstance(cause, RateLimitError):
            raise HTTPException(
                status_code=429, detail=_get_openai_error_code(e)
            ) from e

        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing your question. Please try again.",
        ) from e


# Human-readable stage names for the LangGraph nodes
STAGE_LABELS = {
    "topic_guardrail": "Checking query relevance",
    "list_tables": "Discovering database tables",
    "call_get_schema": "Selecting relevant tables",
    "get_schema": "Loading table schemas",
    "generate_query": "Generating response",
    "check_query": "Validating SQL query",
    "run_query": "Executing SQL query",
}


@router.post("/query/stream")
@limiter.limit("20/minute")
async def query_clinical_trials_stream(
    request: Request,  # noqa: ARG001 — required by slowapi
    query: QueryRequest,
    client_id: str = Depends(get_client_id),
    openai_api_key: str | None = Depends(get_openai_api_key),
) -> StreamingResponse:
    """Stream the agent response token-by-token.

    This endpoint uses Server-Sent Events (SSE) to stream the response
    as the agent generates it. Events are JSON objects with the following types:

    - {"type": "stage", "stage": "...", "label": "..."} - Current agent stage
    - {"type": "token", "content": "..."} - A token of the response
    - {"type": "sql", "query": "..."} - The SQL query being executed
    - {"type": "done", "conversation_id": "...", "answer": "...", "sql_query": "..."} - Final response

    The conversation is persisted at each step via the checkpointer.
    Users can optionally provide their own OpenAI API key via the
    X-OpenAI-API-Key header to use instead of the server's default key.
    """
    # Get or create conversation ID
    is_new_conversation = query.conversation_id is None
    conversation_id = query.conversation_id or str(uuid.uuid4())

    logger.info(
        f"Streaming query: {query.question[:100]}... "
        f"(conversation: {conversation_id}, new: {is_new_conversation}, user_key: {openai_api_key is not None})"
    )

    async def generate():
        try:
            agent = create_agent()
            config: dict = {
                "configurable": {"thread_id": conversation_id, "client_id": client_id}
            }
            if openai_api_key:
                config["configurable"]["openai_api_key"] = openai_api_key

            answer_tokens: list[str] = []
            sql_query: str | None = None
            tool_call_args: dict[str, str] = {}  # Accumulate tool call args by ID
            current_stage: str | None = None  # Track current stage

            # Stream using 'messages' mode for token-by-token output
            async for msg_chunk, metadata in agent.astream(
                {"messages": [{"role": "user", "content": query.question}]},
                config,
                stream_mode="messages",
            ):
                # Extract current node from metadata
                node = metadata.get("langgraph_node")

                # Check for stage changes and emit stage events
                if node and node != current_stage:
                    current_stage = node
                    label = STAGE_LABELS.get(node, node.replace("_", " ").title())
                    yield f"data: {json.dumps({'type': 'stage', 'stage': node, 'label': label})}\n\n"

                # Check for tool call chunks (args come incrementally)
                # SQL query is generated in generate_query or check_query node
                # Track which indices are sql_db_query calls and accumulate their args
                if (
                    hasattr(msg_chunk, "tool_call_chunks")
                    and msg_chunk.tool_call_chunks
                    and node in ("generate_query", "check_query")
                ):
                    for chunk in msg_chunk.tool_call_chunks:
                        chunk_name = chunk.get("name")
                        chunk_index = chunk.get("index", 0)

                        # If this chunk has the sql_db_query name (usually in check_query), mark this index for tracking
                        if chunk_name == "sql_db_query":
                            tool_call_args[f"index_{chunk_index}"] = ""

                        # Accumulate args for tracked indices (or any index in generate_query/check_query)
                        # Since we're in the right nodes, accumulate all tool call args
                        index_key = f"index_{chunk_index}"
                        if index_key not in tool_call_args:
                            tool_call_args[index_key] = ""
                        if chunk.get("args"):
                            tool_call_args[index_key] += chunk["args"]

                        # Try to parse complete JSON and emit SQL event
                        if not sql_query:
                            try:
                                args = json.loads(tool_call_args[index_key])
                                if "query" in args:
                                    sql_query = args["query"]
                                    logger.info(
                                        f"Captured SQL from {node} chunks:\n{sql_query}"
                                    )
                                    yield f"data: {json.dumps({'type': 'sql', 'query': sql_query})}\n\n"
                            except json.JSONDecodeError:
                                pass  # Not complete yet, continue accumulating

                # Check for complete tool calls (handle both dict and object formats)
                if hasattr(msg_chunk, "tool_calls") and msg_chunk.tool_calls:
                    logger.debug(
                        f"Node: {node}, tool_calls found: {msg_chunk.tool_calls}"
                    )
                    for tool_call in msg_chunk.tool_calls:
                        # Handle both dict and object attribute access
                        name = (
                            tool_call.get("name")
                            if isinstance(tool_call, dict)
                            else getattr(tool_call, "name", None)
                        )
                        args = (
                            tool_call.get("args", {})
                            if isinstance(tool_call, dict)
                            else getattr(tool_call, "args", {})
                        )
                        if name == "sql_db_query":
                            captured_sql = (
                                args.get("query")
                                if isinstance(args, dict)
                                else getattr(args, "query", None)
                            )
                            if captured_sql and captured_sql != sql_query:
                                sql_query = captured_sql
                                logger.info(
                                    f"Captured SQL from tool_calls:\n{captured_sql}"
                                )
                                yield f"data: {json.dumps({'type': 'sql', 'query': sql_query})}\n\n"

                # Stream content tokens (only from final answer, not intermediate messages)
                if (
                    hasattr(msg_chunk, "content")
                    and msg_chunk.content
                    and node == "generate_query"
                    and not getattr(msg_chunk, "tool_calls", None)
                ):
                    answer_tokens.append(msg_chunk.content)
                    yield f"data: {json.dumps({'type': 'token', 'content': msg_chunk.content})}\n\n"

            # Try to extract SQL from accumulated tool call args if not found
            if not sql_query and tool_call_args:
                for args_str in tool_call_args.values():
                    try:
                        args = json.loads(args_str)
                        if "query" in args:
                            sql_query = args["query"]
                            logger.info(
                                f"Captured SQL from accumulated chunks:\n{sql_query}"
                            )
                            yield f"data: {json.dumps({'type': 'sql', 'query': sql_query})}\n\n"
                            break
                    except json.JSONDecodeError:
                        pass

            # Save conversation metadata
            await _save_conversation_metadata(
                conversation_id, query.question, client_id, is_new=is_new_conversation
            )

            # Send final event with complete response
            final_answer = (
                "".join(answer_tokens) or "I was unable to generate an answer."
            )
            yield f"data: {json.dumps({'type': 'done', 'conversation_id': conversation_id, 'answer': final_answer, 'sql_query': sql_query})}\n\n"

        except Exception as e:
            logger.exception(f"Error streaming query: {e}")
            from openai import AuthenticationError, RateLimitError

            cause = getattr(e, "__cause__", None)

            if isinstance(e, AuthenticationError) or isinstance(
                cause, AuthenticationError
            ):
                yield f"data: {json.dumps({'type': 'error', 'message': 'Invalid API key. Please provide a valid OpenAI API key.', 'code': 'invalid_api_key'})}\n\n"
            elif isinstance(e, RateLimitError) or isinstance(cause, RateLimitError):
                error_code = _get_openai_error_code(e)
                if error_code == "insufficient_quota":
                    yield f"data: {json.dumps({'type': 'error', 'message': 'API quota exceeded. Please provide your own API key.', 'code': 'insufficient_quota'})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'Rate limit reached. Please wait a moment or provide your own API key.', 'code': 'rate_limit'})}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'error', 'message': 'An error occurred while processing your question.'})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
