from typing import List

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from bson import ObjectId

from auth.jwt import decode_token
from db.database import get_db

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db=Depends(get_db),
) -> dict:
    token = credentials.credentials
    payload = decode_token(token)
    user_id = payload.get('sub')

    user = await db["users"].find_one({"_id": ObjectId(user_id)})
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists.",
        )
    return user


def require_roles(*roles: str):
    """
    Role-based access control factory.
    """
    async def role_checker(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {list(roles)}",
            )
        return user

    return role_checker


def require_self_or_admin(user_id_param: str = "user_id"):
    """
    Allow access if user is admin OR accessing their own resource.
    Expects a path parameter with the user_id to check against.
    """
    async def self_or_admin_checker(
        user_id: str,
        user: dict = Depends(get_current_user)
    ) -> dict:
        if user.get("role") == "admin" or str(user["_id"]) == user_id:
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only access your own resources or must be an admin.",
        )

    return self_or_admin_checker
