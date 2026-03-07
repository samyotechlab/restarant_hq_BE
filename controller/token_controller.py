from datetime import datetime, timezone
from bson import ObjectId
from fastapi import HTTPException, status
from auth.jwt import create_access_token, decode_token
from models import AccessTokenResponse, TokenResponse, UserResponse


class TokenController:
    @staticmethod
    async def store_refresh_token(db, user_id: str, refresh_token: str):
        """Stores a refresh token in the database."""
        await db["refresh_tokens"].delete_one({"user_id": user_id})
        await db["refresh_tokens"].insert_one({
            "user_id": user_id,
            "token": refresh_token,
            "created_at": datetime.now(timezone.utc)
        })

    @staticmethod
    async def refresh_access_token(refresh_token: str, db):
        """Verifies a refresh token and returns a new access token."""
        payload = decode_token(refresh_token)
        user_id_str = payload.get("sub")

        # Verify token exists in database
        stored_token = await db["refresh_tokens"].find_one({
            "user_id": user_id_str,
            "token": refresh_token
        })
        if not stored_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token.",
            )

        # Convert user_id_str to ObjectId for querying users collection
        user = await db["users"].find_one({"_id": ObjectId(user_id_str)})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User no longer exists.",
            )

        token_payload = {
            "sub": str(user["_id"]),
            "email": user["email"],
            "role": user["role"],
            "name": user["name"],
        }
        new_access_token = create_access_token(token_payload)
        return AccessTokenResponse(access_token=new_access_token)

    @staticmethod
    async def revoke_refresh_token(refresh_token: str, db):
        """Removes a refresh token from the database (logout)."""
        await db["refresh_tokens"].delete_one({"token": refresh_token})
        return {"message": "Logged out successfully."}
