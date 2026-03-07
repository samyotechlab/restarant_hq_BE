from pydantic import BaseModel
from .user_model import UserResponse


class TokenResponse(BaseModel):
    """Returned on successful login or token refresh."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class AccessTokenResponse(BaseModel):
    """Returned on /auth/refresh — only a new access token."""
    access_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """Body for the /auth/refresh endpoint."""
    refresh_token: str
