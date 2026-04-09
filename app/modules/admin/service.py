from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.modules.admin.repository import AdminRepository


class AdminService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = AdminRepository(session)

    async def list_users(self) -> Sequence[User]:
        return await self.repository.list_users()
