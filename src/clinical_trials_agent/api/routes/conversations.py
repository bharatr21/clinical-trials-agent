"""Conversations management endpoints."""

import logging
import uuid as uuid_module

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, desc, func, select

from clinical_trials_agent.agent import create_agent
from clinical_trials_agent.api.dependencies import get_client_id
from clinical_trials_agent.database import get_app_db_session
from clinical_trials_agent.models import Conversation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])


class MessageResponse(BaseModel):
    """A single message in a conversation."""

    id: str = Field(..., description="Message ID")
    role: str = Field(..., description="Message role (user or assistant)")
    content: str = Field(..., description="Message content")
    tool_calls: list[dict] | None = Field(None, description="Tool calls if any")


class ConversationSummary(BaseModel):
    """Summary of a conversation for listing."""

    id: str = Field(..., description="Conversation ID")
    title: str = Field(..., description="Conversation title")
    created_at: str = Field(..., description="ISO timestamp of creation")
    updated_at: str = Field(..., description="ISO timestamp of last update")


class ConversationDetail(BaseModel):
    """Detailed conversation with messages."""

    id: str = Field(..., description="Conversation ID")
    title: str = Field(..., description="Conversation title")
    messages: list[MessageResponse] = Field(..., description="Conversation messages")
    created_at: str = Field(..., description="ISO timestamp of creation")
    updated_at: str = Field(..., description="ISO timestamp of last update")


class ConversationListResponse(BaseModel):
    """Response for conversation list endpoint."""

    conversations: list[ConversationSummary] = Field(
        ..., description="List of conversations"
    )
    total: int = Field(..., description="Total number of conversations")


def _format_message(message) -> MessageResponse:
    """Format a LangChain message for the API response."""
    # Handle different message types
    role = "assistant"
    if hasattr(message, "type"):
        if message.type == "human":
            role = "user"
        elif message.type == "ai":
            role = "assistant"
        elif message.type == "tool":
            role = "tool"

    content = getattr(message, "content", str(message))
    tool_calls = None
    if hasattr(message, "tool_calls") and message.tool_calls:
        tool_calls = message.tool_calls

    return MessageResponse(
        id=getattr(message, "id", str(uuid_module.uuid4())),
        role=role,
        content=content,
        tool_calls=tool_calls,
    )


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    client_id: str = Depends(get_client_id),
    limit: int = 50,
    offset: int = 0,
) -> ConversationListResponse:
    """List all conversations for this client, ordered by most recently updated."""
    async with get_app_db_session() as session:
        # Get total count for this client
        count_result = await session.execute(
            select(func.count())
            .select_from(Conversation)
            .where(Conversation.client_id == client_id)
        )
        total = count_result.scalar() or 0

        # Get paginated results for this client
        result = await session.execute(
            select(Conversation)
            .where(Conversation.client_id == client_id)
            .order_by(desc(Conversation.updated_at))
            .limit(limit)
            .offset(offset)
        )
        conversations = result.scalars().all()

        return ConversationListResponse(
            conversations=[
                ConversationSummary(
                    id=str(conv.id),
                    title=conv.title,
                    created_at=conv.created_at.isoformat(),
                    updated_at=conv.updated_at.isoformat(),
                )
                for conv in conversations
            ],
            total=total,
        )


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: str,
    client_id: str = Depends(get_client_id),
) -> ConversationDetail:
    """Get a conversation with all its messages."""
    try:
        conv_uuid = uuid_module.UUID(conversation_id)
    except ValueError as e:
        raise HTTPException(
            status_code=400, detail="Invalid conversation ID format"
        ) from e

    # Get conversation metadata (must belong to this client)
    async with get_app_db_session() as session:
        result = await session.execute(
            select(Conversation).where(
                Conversation.id == conv_uuid,
                Conversation.client_id == client_id,
            )
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        conv_title = conversation.title
        conv_created_at = conversation.created_at.isoformat()
        conv_updated_at = conversation.updated_at.isoformat()

    # Get messages from LangGraph checkpointer
    agent = create_agent()
    config = {"configurable": {"thread_id": conversation_id}}

    try:
        state = await agent.aget_state(config)
    except Exception as e:
        logger.exception(f"Error getting conversation state: {e}")
        # Return empty messages if state retrieval fails
        return ConversationDetail(
            id=conversation_id,
            title=conv_title,
            messages=[],
            created_at=conv_created_at,
            updated_at=conv_updated_at,
        )

    messages: list[MessageResponse] = []
    if state and state.values:
        raw_messages = state.values.get("messages", [])
        for msg in raw_messages:
            formatted = _format_message(msg)
            # Skip tool messages and empty messages (tool calls without text)
            if formatted.role != "tool" and formatted.content.strip():
                messages.append(formatted)

    return ConversationDetail(
        id=conversation_id,
        title=conv_title,
        messages=messages,
        created_at=conv_created_at,
        updated_at=conv_updated_at,
    )


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    client_id: str = Depends(get_client_id),
) -> dict:
    """Delete a conversation and its metadata.

    Note: This deletes the metadata. LangGraph checkpoints may need
    separate cleanup depending on retention policy.
    """
    try:
        conv_uuid = uuid_module.UUID(conversation_id)
    except ValueError as e:
        raise HTTPException(
            status_code=400, detail="Invalid conversation ID format"
        ) from e

    async with get_app_db_session() as session:
        # Check if conversation exists and belongs to this client
        result = await session.execute(
            select(Conversation).where(
                Conversation.id == conv_uuid,
                Conversation.client_id == client_id,
            )
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Delete the conversation
        await session.execute(
            delete(Conversation).where(
                Conversation.id == conv_uuid,
                Conversation.client_id == client_id,
            )
        )

    logger.info(f"Deleted conversation: {conversation_id}")
    return {"status": "deleted", "id": conversation_id}
