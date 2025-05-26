"""
Custom exceptions for API error handling in the Lumen application.
"""


class APIError(Exception):
    """Base exception for API-related errors."""
    pass


class APIKeyError(APIError):
    """Raised when API key is missing or invalid."""
    pass


class APIConnectionError(APIError):
    """Raised when connection to API fails."""
    pass


class APIRateLimitError(APIError):
    """Raised when API rate limit is exceeded."""
    pass


class APIResponseError(APIError):
    """Raised when API returns an unexpected response."""
    pass


class APITimeoutError(APIError):
    """Raised when API request times out."""
    pass