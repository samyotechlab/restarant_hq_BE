from datetime import datetime, timezone
from typing import List
from fastapi import HTTPException, status
from bson import ObjectId
from auth.password import hash_password
from models import UserResponse, UserUpdate

class UserController:
    @staticmethod
    async def get_me(current_user: dict):
        user_data = current_user.copy()
        user_data["id"] = str(user_data["_id"])
        return UserResponse(**user_data)

    @staticmethod
    async def get_all_users(db):
        users = await db["users"].find().to_list(length=None)
        res = []
        for u in users:
            u["id"] = str(u["_id"])
            res.append(UserResponse(**u))
        return res

    @staticmethod
    async def get_user_by_id(user_id: str, db):
        user = await db["users"].find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id '{user_id}' not found.",
            )
        user["id"] = str(user["_id"])
        return UserResponse(**user)

    @staticmethod
    async def update_user(user_id: str, data: UserUpdate, db, current_user: dict):
        if current_user["role"] != "admin" and str(current_user["_id"]) != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own profile.",
            )

        user = await db["users"].find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id '{user_id}' not found.",
            )

        update_fields = data.model_dump(exclude_unset=True)
        if "password" in update_fields:
            update_fields["password"] = hash_password(update_fields["password"])

        update_fields["updated_at"] = datetime.now(timezone.utc)

        await db["users"].update_one({"_id": ObjectId(user_id)}, {"$set": update_fields})
        updated_user = await db["users"].find_one({"_id": ObjectId(user_id)})
        updated_user["id"] = str(updated_user["_id"])
        return UserResponse(**updated_user)

    @staticmethod
    async def delete_user(user_id: str, db):
        result = await db["users"].delete_one({"_id": ObjectId(user_id)})
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id '{user_id}' not found.",
            )
        return {"message": f"User '{user_id}' deleted successfully."}
