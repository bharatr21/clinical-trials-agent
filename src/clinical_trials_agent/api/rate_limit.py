"""Rate limiting configuration for the API."""

import re

from slowapi import Limiter
from starlette.requests import Request

# Same pattern used by get_client_id in dependencies.py
_CLIENT_ID_PATTERN = re.compile(r"^[a-f0-9-]{32,64}$", re.IGNORECASE)


def _get_client_key(request: Request) -> str:
    """Extract rate limit key from client IP + validated X-Client-ID."""
    ip = request.client.host if request.client else "unknown"

    client_id = request.headers.get("X-Client-ID")
    if client_id and _CLIENT_ID_PATTERN.match(client_id):
        return f"{ip}:{client_id}"

    return ip


limiter = Limiter(key_func=_get_client_key)
