from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.db.models.user import User
from app.modules.auth.dependencies import (
    get_auth_service,
    get_current_active_user,
)
from app.modules.auth.rate_limit import AuthRateLimitDependency
from app.modules.auth.schemas import (
    RefreshTokenRequest,
    RegisterUserRequest,
    TokenResponse,
    UserResponse,
)
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Creates a new user account using email, password, and full name.",
)
async def register_user(
    payload: RegisterUserRequest,
    _: AuthRateLimitDependency,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponse:
    user = await service.register_user(payload)
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate a user",
    description=(
        "Authenticates a user with email and password and returns access and "
        "refresh tokens."
    ),
)
async def login_user(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    _: AuthRateLimitDependency,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    return await service.login_user(email=form_data.username, password=form_data.password)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh auth tokens",
    description="Rotates a refresh token and returns a fresh access and refresh token pair.",
)
async def refresh_tokens(
    payload: RefreshTokenRequest,
    _: AuthRateLimitDependency,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    return await service.refresh_user_tokens(refresh_token=payload.refresh_token)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Returns the currently authenticated active user.",
)
async def get_current_authenticated_user(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> UserResponse:
    return UserResponse.model_validate(current_user)
