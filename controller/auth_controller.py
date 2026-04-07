from datetime import datetime, timezone
from fastapi import HTTPException, status
from auth.jwt import create_access_token, create_refresh_token
from auth.password import hash_password, verify_password
from bson import ObjectId
from models import (
    AccessTokenResponse,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
    ChangePasswordRequest,
)
from controller.token_controller import TokenController

class AuthController:
    @staticmethod
    async def register(data: UserCreate, db):
        existing = await db["users"].find_one({"email": data.email})
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this email already exists. Try different email.",
            )

        now = datetime.now(timezone.utc)
        user_doc = {
            "name": data.name,
            "email": data.email,
            "password": hash_password(data.password),
            "role": data.role.value,
            "created_at": now,
            "updated_at": now,
        }

        result = await db["users"].insert_one(user_doc)
        return UserResponse(
            id=str(result.inserted_id),
            name= user_doc["name"],
            email= user_doc["email"],
            role= user_doc["role"],
            created_at= user_doc["created_at"],
            updated_at= user_doc["updated_at"],
        )

    @staticmethod
    async def login(data: UserLogin, db):
        user = await db["users"].find_one({"email": data.email})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No account found with this email.",
            )

        if not verify_password(data.password, user["password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect password.",
            )

        user_id_str = str(user["_id"])
        token_payload = {
            "sub": user_id_str,
            "email": user["email"],
            "role": user["role"],
            "name": user["name"],
        }
        access_token = create_access_token(token_payload)
        refresh_token = create_refresh_token({"sub": user_id_str})

        await TokenController.store_refresh_token(db, user_id_str, refresh_token)

        user_response = UserResponse(
            id=user_id_str,
            name=user["name"],
            email=user["email"],
            role=user["role"],
            created_at=user["created_at"],
            updated_at=user["updated_at"],
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=user_response
        )

    @staticmethod
    async def refresh_token(refresh_token: str, db):
        """Exchange refresh token for access token via TokenController."""
        return await TokenController.refresh_access_token(refresh_token, db)

    @staticmethod
    async def logout(refresh_token: str, db):
        """Invalidate specific browse session via TokenController."""
        return await TokenController.revoke_refresh_token(refresh_token, db)

    @staticmethod
    async def change_password(new_password: str, user_id: str, db):
        hashed_password = hash_password(new_password)
        now = datetime.now(timezone.utc)
        await db["users"].update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"password": hashed_password, "updated_at": now}}
        )
        return {"message": "Password changed successfully"}
