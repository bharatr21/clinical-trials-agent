"""Langfuse tracing (the v3 SDK exports spans to Langfuse's OTLP endpoint)."""

import logging
from typing import Any

from langfuse import Langfuse, get_client
from langfuse.langchain import CallbackHandler

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


def get_langfuse_config(configurable: dict[str, Any]) -> dict[str, Any]:
    """Build RunnableConfig entries that trace a whole agent run in Langfuse.

    Pass these at the graph entry point (ainvoke/astream) so every node, tool
    and LLM call is nested under a single trace. Returns {} if not configured.
    """
    if not _ensure_langfuse_client():
        return {}

    return {
        "callbacks": [CallbackHandler()],
        "metadata": {
            "langfuse_user_id": configurable.get("client_id"),
            "langfuse_session_id": configurable.get("thread_id"),
        },
    }


def shutdown_langfuse() -> None:
    """Flush pending spans and stop the exporter. Blocking; call on shutdown."""
    if _langfuse_initialized:
        get_client().shutdown()
        logger.info("Langfuse client shut down")
