from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from jose import JWTError, jwt

from config.settings import settings

# ---------------------------------------------------------------------------
# JWT Token Utilities
# ---------------------------------------------------------------------------

CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials.",
    headers={"WWW-Authenticate": "Bearer"},
)


def _create_token(data: dict, expires_delta: timedelta) -> str:
    """Internal helper — create a signed JWT with an expiry claim."""
    payload = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    payload.update({"exp": expire})
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(data: dict) -> str:
    """Create a short-lived access token (default: ACCESS_TOKEN_MINUTES)."""
    return _create_token(
        data, timedelta(minutes=settings.ACCESS_TOKEN_MINUTES)
    )


def create_refresh_token(data: dict) -> str:
    """Create a long-lived refresh token (default: REFRESH_TOKEN_DAYS days)."""
    return _create_token(
        data, timedelta(days=settings.REFRESH_TOKEN_DAYS)
    )


def decode_token(token: str) -> dict:
    """
    Decode and verify a JWT.

    Raises HTTP 401 if the token is invalid, expired, or missing required claims.
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id: Optional[str] = payload.get("sub")
        if user_id is None:
            raise CREDENTIALS_EXCEPTION
        return payload
    except JWTError:
        raise CREDENTIALS_EXCEPTION
