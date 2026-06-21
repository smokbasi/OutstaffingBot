from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import User, UserRole


async def get_or_create_by_telegram_id(
    session: AsyncSession,
    telegram_id: int,
    *,
    username: str | None = None,
    language_code: str | None = None,
) -> User:
    stmt = (
        select(User)
        .options(selectinload(User.worker))
        .where(User.telegram_id == telegram_id)
    )
    user = await session.scalar(stmt)
    if user is not None:
        if username and user.username != username:
            user.username = username
        if language_code and user.language_code != language_code:
            user.language_code = language_code
        return user

    user = User(
        telegram_id=telegram_id,
        username=username,
        language_code=language_code,
        role=UserRole.worker,
    )
    session.add(user)
    await session.flush()
    return user


async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> User | None:
    stmt = (
        select(User)
        .options(selectinload(User.worker))
        .where(User.telegram_id == telegram_id)
    )
    return await session.scalar(stmt)
