from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import StackTag, Subscription, User, UserProfile


async def upsert_bot_user(
    session: AsyncSession,
    *,
    tg_id: int,
    chat_id: int,
    username: str | None,
    first_name: str,
    last_name: str | None = None,
    locale: str = "ru",
) -> User:
    user = await session.scalar(
        select(User)
        .options(
            selectinload(User.profile),
            selectinload(User.stacks).selectinload(StackTag.categories),
            selectinload(User.subscriptions).selectinload(Subscription.tariff),
        )
        .where(User.tg_id == tg_id)
    )

    display_name = " ".join(part for part in [first_name.strip(), (last_name or "").strip()] if part).strip() or username or f"Telegram user {tg_id}"
    if user is None:
        user = User(
            tg_id=tg_id,
            chat_id=chat_id,
            username=username,
            display_name=display_name,
            locale=locale,
            profile=UserProfile(headline="New IT user", bio="Telegram onboarded account."),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

    user.chat_id = chat_id
    user.username = username
    user.display_name = display_name
    user.locale = locale
    await session.commit()
    await session.refresh(user)
    return user
