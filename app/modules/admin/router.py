from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends

from app.common.enums import UserRole
from app.db.models.user import User
from app.modules.admin.service import AdminService
from app.modules.auth.dependencies import SessionDependency, require_role
from app.modules.auth.schemas import UserResponse

router = APIRouter(prefix="/admin", tags=["admin"])


def get_admin_service(session: SessionDependency) -> AdminService:
    return AdminService(session)


@router.get(
    "/users",
    response_model=list[UserResponse],
    summary="List users",
    description="Returns all users. This endpoint is restricted to active admin users.",
)
async def list_users(
    _: Annotated[User, Depends(require_role(UserRole.ADMIN))],
    service: Annotated[AdminService, Depends(get_admin_service)],
) -> list[UserResponse]:
    users: Sequence[User] = await service.list_users()
    return [UserResponse.model_validate(user) for user in users]
