from typing import List
from fastapi import APIRouter, Depends, status
from auth.dependencies import get_current_user, require_roles, require_self_or_admin
from db.database import get_db
from models import UserResponse, UserUpdate, StandardResponse
from controller.user_controller import UserController

router = APIRouter(prefix="/users", tags=["Users"])

@router.get(
    "/me",
    response_model=StandardResponse[UserResponse],
    summary="Get your own profile",
)
async def get_me(current_user: dict = Depends(get_current_user)):
    result = await UserController.get_me(current_user)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Profile Retrieved Successfully",
        result_data=result
    )

@router.get(
    "/",
    response_model=StandardResponse[List[UserResponse]],
    summary="Get all users",
)
async def get_all_users(
    db=Depends(get_db),
    current_user: dict = Depends(require_roles("admin")),
):
    result = await UserController.get_all_users(db)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Users Retrieved Successfully",
        result_data=result
    )

@router.get(
    "/{user_id}",
    response_model=StandardResponse[UserResponse],
    summary="Get a user by ID",
)
async def get_user_by_id(
    user_id: str,
    db=Depends(get_db),
    current_user: dict = Depends(require_self_or_admin()),
):
    result = await UserController.get_user_by_id(user_id, db)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="User Retrieved Successfully",
        result_data=result
    )

@router.patch(
    "/{user_id}",
    response_model=StandardResponse[UserResponse],
    summary="Update a user",
)
async def update_user(
    user_id: str,
    data: UserUpdate,
    db=Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await UserController.update_user(user_id, data, db, current_user)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="User Updated Successfully",
        result_data=result
    )

@router.delete(
    "/{user_id}",
    response_model=StandardResponse[dict],
    summary="Delete a user (admin only)",
    status_code=status.HTTP_200_OK,
)
async def delete_user(
    user_id: str,
    db=Depends(get_db),
    current_user: dict = Depends(require_roles("admin")),
):
    result = await UserController.delete_user(user_id, db)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="User Deleted Successfully",
        result_data=result
    )
