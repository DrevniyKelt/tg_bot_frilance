from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.i18n import detect_locale
from app.db.models import User
from app.db.session import get_db_session
from app.schemas.profile import PublicUserProfile, UpdateProfileRequest, UpdateUserStacksRequest
from app.services.profiles import get_public_user, serialize_user, update_profile, update_user_stacks


router = APIRouter()


@router.get("/me", response_model=PublicUserProfile)
async def get_me(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> PublicUserProfile:
    locale = detect_locale(request, get_settings())
    return serialize_user(current_user, locale)


@router.patch("/me", response_model=PublicUserProfile)
async def patch_me(
    request: Request,
    payload: UpdateProfileRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> PublicUserProfile:
    locale = detect_locale(request, get_settings())
    user = await update_profile(session, current_user, payload)
    return serialize_user(user, locale)


@router.get("/me/stacks")
async def get_my_stacks(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    locale = detect_locale(request, get_settings())
    profile = serialize_user(current_user, locale)
    return [tag.model_dump() for tag in profile.stack]


@router.put("/me/stacks", response_model=PublicUserProfile)
async def put_my_stacks(
    request: Request,
    payload: UpdateUserStacksRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> PublicUserProfile:
    locale = detect_locale(request, get_settings())
    user = await update_user_stacks(session, current_user, payload.stack_slugs)
    return serialize_user(user, locale)


@router.get("/users/{user_id}/public", response_model=PublicUserProfile)
async def public_user_profile(
    user_id: int,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> PublicUserProfile:
    locale = detect_locale(request, get_settings())
    user = await get_public_user(session, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return serialize_user(user, locale)
