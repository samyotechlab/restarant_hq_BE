from fastapi import APIRouter, Depends, status
from auth.dependencies import get_current_user
from db.database import get_db
from models import (
    AccessTokenResponse,
    RefreshRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
    StandardResponse,
)
from controller.auth_controller import AuthController

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post(
    "/register",
    response_model=StandardResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(data: UserCreate, db=Depends(get_db)):
    """
    Register a new user account.
    """
    result = await AuthController.register(data, db)
    return StandardResponse(
        status_code=status.HTTP_201_CREATED,
        message="Profile Created Successfully",
        result_data=result
    )

@router.post(
    "/login",
    response_model=StandardResponse[TokenResponse],
    summary="Login and receive access + refresh tokens",
)
async def login(data: UserLogin, db=Depends(get_db)):
    """
    Authenticate a user and return a JWT access token and refresh token.
    """
    result = await AuthController.login(data, db)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Login Successful",
        result_data=result
    )

@router.post(
    "/refresh",
    response_model=StandardResponse[AccessTokenResponse],
    summary="Get a new access token using a refresh token",
)
async def refresh_token(body: RefreshRequest, db=Depends(get_db)):
    """
    Exchange a valid refresh token for a new access token.
    """
    result = await AuthController.refresh_token(body.refresh_token, db)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Token Refreshed Successfully",
        result_data=result
    )

@router.post(
    "/logout",
    response_model=StandardResponse[dict],
    summary="Logout and invalidate refresh token",
    status_code=status.HTTP_200_OK,
)
async def logout(body: RefreshRequest, db=Depends(get_db), _: dict = Depends(get_current_user)):
    """
    Logout the current user and remove their refresh token from the database.
    """
    result = await AuthController.logout(body.refresh_token, db)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Logout Successful",
        result_data=result
    )
