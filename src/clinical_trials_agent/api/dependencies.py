"""FastAPI dependencies for the API."""

import re
import uuid

from fastapi import Header, Response

# Pattern for valid client IDs: UUID-like format or alphanumeric with hyphens
# Allows device fingerprint IDs and standard UUIDs
CLIENT_ID_PATTERN = re.compile(r"^[a-f0-9-]{32,64}$", re.IGNORECASE)

# Pattern for valid OpenAI API keys (sk-... format)
OPENAI_KEY_PATTERN = re.compile(r"^sk-[a-zA-Z0-9_-]{20,}$")


def get_client_id(
    response: Response,
    x_client_id: str | None = Header(None, alias="X-Client-ID"),
) -> str:
    """Get client ID from header or generate a new one.

    Accepts either:
    - Standard UUIDs
    - Device fingerprint IDs (UUID-like hex strings)

    If client ID is missing or invalid, generates a new UUID and
    returns it in X-Client-ID response header for frontend to store.
    """
    # Validate existing client ID
    if x_client_id and CLIENT_ID_PATTERN.match(x_client_id):
        return x_client_id

    # Generate new client ID as fallback
    new_client_id = str(uuid.uuid4())
    response.headers["X-Client-ID"] = new_client_id
    return new_client_id


def get_openai_api_key(
    x_openai_api_key: str | None = Header(None, alias="X-OpenAI-API-Key"),
) -> str | None:
    """Get user-provided OpenAI API key from header.

    Returns None if no key provided or key format is invalid.
    The key is validated for format only (sk-... pattern).
    """
    if x_openai_api_key and OPENAI_KEY_PATTERN.match(x_openai_api_key):
        return x_openai_api_key
    return None
