"""Rate limiting configuration for the API."""

from slowapi import Limiter
from starlette.requests import Request


def _get_client_key(request: Request) -> str:
    """Extract rate limit key from X-Client-ID header, falling back to IP."""
    client_id = request.headers.get("X-Client-ID")
    if client_id:
        return client_id
    return request.client.host if request.client else "unknown"


limiter = Limiter(key_func=_get_client_key)
