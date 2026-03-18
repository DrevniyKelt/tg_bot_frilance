from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import verify_telegram_init_data
from app.db.models import RoleMode, User, UserProfile


async def login_from_telegram(session: AsyncSession, init_data: str) -> User:
    settings = get_settings()
    payload = _load_payload(init_data, settings.telegram.bot_token, settings.telegram.allow_dev_login)
    tg_id = int(payload["id"])

    result = await session.scalars(select(User).where(User.tg_id == tg_id))
    user = result.first()
    display_name = _display_name(payload)
    locale = payload.get("language_code", settings.app.default_locale)
    username = payload.get("username")

    if user is None:
        user = User(
            tg_id=tg_id,
            username=username,
            display_name=display_name,
            primary_role=RoleMode.BOTH,
            locale=locale,
            profile=UserProfile(
                headline="New IT user",
                bio="Telegram onboarded account.",
            ),
        )
        session.add(user)
        await session.flush()
    else:
        user.display_name = display_name
        user.username = username
        user.locale = locale

    user.last_active_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(user)
    return user


def _load_payload(init_data: str, bot_token: str, allow_dev_login: bool) -> dict:
    if allow_dev_login and init_data.startswith("demo:"):
        _, raw_id = init_data.split(":", maxsplit=1)
        demo_id = int(raw_id)
        return {
            "id": demo_id,
            "username": f"demo_{demo_id}",
            "first_name": f"Demo {demo_id}",
            "last_name": "",
            "language_code": "ru",
        }

    if allow_dev_login and init_data.startswith("{"):
        return json.loads(init_data)

    return verify_telegram_init_data(init_data, bot_token)


def _display_name(payload: dict) -> str:
    pieces = [payload.get("first_name", "").strip(), payload.get("last_name", "").strip()]
    joined = " ".join(part for part in pieces if part).strip()
    return joined or payload.get("username") or f"Telegram user {payload['id']}"
