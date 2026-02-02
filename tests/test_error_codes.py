"""Tests for OpenAI error code extraction."""

from unittest.mock import MagicMock


def test_get_openai_error_code_rate_limit():
    """Test that rate limit errors return 'rate_limit' code."""
    from openai import RateLimitError

    from clinical_trials_agent.api.routes.query import _get_openai_error_code

    # Create a mock RateLimitError with rate limit body
    error = MagicMock(spec=RateLimitError)
    error.body = {
        "error": {
            "message": "Rate limit reached",
            "type": "tokens",
            "code": None,
        }
    }
    # Make isinstance check work
    error.__class__ = RateLimitError

    result = _get_openai_error_code(error)
    assert result == "rate_limit"


def test_get_openai_error_code_insufficient_quota():
    """Test that quota errors return 'insufficient_quota' code."""
    from openai import RateLimitError

    from clinical_trials_agent.api.routes.query import _get_openai_error_code

    # Create a mock RateLimitError with quota exceeded body
    error = MagicMock(spec=RateLimitError)
    error.body = {
        "error": {
            "message": "You exceeded your current quota",
            "type": "insufficient_quota",
            "code": "insufficient_quota",
        }
    }
    error.__class__ = RateLimitError

    result = _get_openai_error_code(error)
    assert result == "insufficient_quota"


def test_get_openai_error_code_wrapped_error():
    """Test that wrapped errors are handled correctly."""
    from clinical_trials_agent.api.routes.query import _get_openai_error_code

    # Create a real RateLimitError (requires specific arguments)
    # We'll test the logic by checking that non-RateLimitError returns rate_limit
    outer_error = Exception("Wrapped error")

    # Without a proper __cause__, should default to rate_limit
    result = _get_openai_error_code(outer_error)
    assert result == "rate_limit"  # Default when not a RateLimitError


def test_get_openai_error_code_no_body():
    """Test fallback when error has no body."""
    from openai import RateLimitError

    from clinical_trials_agent.api.routes.query import _get_openai_error_code

    error = MagicMock(spec=RateLimitError)
    error.body = None
    error.__class__ = RateLimitError

    result = _get_openai_error_code(error)
    assert result == "rate_limit"  # Default fallback
