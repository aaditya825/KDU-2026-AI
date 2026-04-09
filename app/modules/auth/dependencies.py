from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import UserRole
from app.core.exceptions import AppError
from app.core.security import oauth2_scheme
from app.db.models.user import User
from app.db.session import get_db_session
from app.modules.auth.service import AuthService, user_has_role

SessionDependency = Annotated[AsyncSession, Depends(get_db_session)]
TokenDependency = Annotated[str, Depends(oauth2_scheme)]


def get_auth_service(session: SessionDependency) -> AuthService:
    return AuthService(session)


async def get_current_user(
    token: TokenDependency,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    return await service.get_user_from_access_token(token)


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not current_user.is_active:
        raise AppError(
            code="inactive_user",
            message="User account is inactive.",
            status_code=status.HTTP_403_FORBIDDEN,
        )
    return current_user


def require_role(role: UserRole) -> Callable[..., Awaitable[User]]:
    async def dependency(
        current_user: Annotated[User, Depends(get_current_active_user)],
    ) -> User:
        if not user_has_role(current_user, role):
            raise AppError(
                code="insufficient_permissions",
                message="You do not have permission to perform this action.",
                status_code=status.HTTP_403_FORBIDDEN,
            )
        return current_user

    return dependency
