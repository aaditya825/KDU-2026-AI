from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User


class AdminRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_users(self) -> Sequence[User]:
        statement = select(User).order_by(User.id.asc())
        result = await self.session.scalars(statement)
        return result.all()
