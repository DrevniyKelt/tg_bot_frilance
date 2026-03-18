from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.auth import AuthResponse, TelegramVerifyRequest
from app.services.auth import login_from_telegram


router = APIRouter()


@router.post("/auth/telegram/verify", response_model=AuthResponse)
async def verify_telegram_auth(
    payload: TelegramVerifyRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> AuthResponse:
    user = await login_from_telegram(session, payload.init_data)
    request.session["user_id"] = user.id
    return AuthResponse(user_id=user.id, display_name=user.display_name, locale=user.locale)


@router.post("/logout")
async def logout(request: Request) -> dict[str, bool]:
    request.session.clear()
    return {"ok": True}
