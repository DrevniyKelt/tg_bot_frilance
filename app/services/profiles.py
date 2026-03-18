from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.db.models import RoleMode, StackTag, Subscription, SubscriptionStatus, User
from app.schemas.profile import PublicUserProfile, UpdateProfileRequest
from app.services.catalog import resolve_stack_tags


async def resolve_current_user(session: AsyncSession, request: Request) -> User | None:
    settings = get_settings()
    user_id = request.session.get("user_id")
    if user_id is None and settings.telegram.allow_dev_login:
        user_id = settings.demo.default_user_id
        request.session["user_id"] = user_id
    if user_id is None:
        return None
    user = await session.scalar(
        select(User)
        .options(
            selectinload(User.profile),
            selectinload(User.stacks).selectinload(StackTag.categories),
            selectinload(User.subscriptions).selectinload(Subscription.tariff),
        )
        .where(User.id == int(user_id))
    )
    if user is None:
        return None
    user.last_active_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(user)
    return user


def serialize_user(user: User, locale: str) -> PublicUserProfile:
    active_tariff = None
    for subscription in user.subscriptions:
        if subscription.status == SubscriptionStatus.ACTIVE and subscription.ends_at:
            active_tariff = subscription.tariff.name_ru if locale == "ru" else subscription.tariff.name_en
            break
    return PublicUserProfile(
        id=user.id,
        display_name=user.display_name,
        role=user.primary_role.value,
        headline=user.profile.headline,
        bio=user.profile.bio,
        locale=user.locale,
        wallet_balance=user.profile.wallet_balance,
        avg_executor_rating=user.profile.avg_executor_rating,
        avg_client_rating=user.profile.avg_client_rating,
        completed_deals=user.completed_deals,
        total_matches=user.total_matches,
        active_tariff=active_tariff,
        stack=[
            {
                "id": tag.id,
                "slug": tag.slug,
                "name": tag.name_ru if locale == "ru" else tag.name_en,
                "categories": [
                    category.name_ru if locale == "ru" else category.name_en
                    for category in tag.categories
                ],
            }
            for tag in user.stacks
        ],
    )


async def update_profile(session: AsyncSession, user: User, payload: UpdateProfileRequest) -> User:
    user.display_name = payload.display_name
    user.primary_role = RoleMode(payload.primary_role)
    user.profile.headline = payload.headline
    user.profile.bio = payload.bio
    await session.commit()
    await session.refresh(user)
    return user


async def update_user_stacks(session: AsyncSession, user: User, stack_slugs: list[str]) -> User:
    if len(stack_slugs) > 30:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Maximum 30 stack tags.")
    user.stacks = await resolve_stack_tags(session, stack_slugs)
    await session.commit()
    await session.refresh(user)
    return user


async def get_public_user(session: AsyncSession, user_id: int) -> User | None:
    return await session.scalar(
        select(User)
        .options(
            selectinload(User.profile),
            selectinload(User.stacks).selectinload(StackTag.categories),
            selectinload(User.subscriptions).selectinload(Subscription.tariff),
        )
        .where(User.id == user_id)
    )
