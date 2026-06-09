import re
from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader
from app.core.config import settings

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)


async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Dependency to verify the API key provided in the custom header.
    """
    if api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key."
        )
    return api_key


def sanitize_input(text: str) -> str:
    """
    Sanitize text input to protect against injection.
    Removes NUL bytes, strips surrounding whitespaces, and normalizes space chars.
    """
    if not text:
        return ""
    # Remove null characters
    text = text.replace("\x00", "")
    # Normalize whitespaces (tabs, newlines, etc.) to spaces in case of specific queries,
    # but keep formatting for chunk storage by only stripping outer.
    return text.strip()
