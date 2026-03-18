from __future__ import annotations

from random import Random

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.db.models import Order, RoleMode, User
from app.schemas.order import SwipeCardResponse
from app.services.catalog import normalize_stack_slugs


async def build_swipe_cards(
    session: AsyncSession,
    current_user: User,
    *,
    target: str,
    stack: list[str] | str | None = None,
    locale: str,
) -> list[SwipeCardResponse]:
    settings = get_settings()
    normalized_filters = await normalize_stack_slugs(session, stack)
    reference_stack = set(normalized_filters or [tag.slug for tag in current_user.stacks])

    if target == "executors":
        candidates = (
            await session.scalars(
                select(User)
                .options(selectinload(User.profile), selectinload(User.stacks))
                .order_by(User.display_name)
            )
        ).all()
        cards = [
            SwipeCardResponse(
                entity_type="executor",
                id=user.id,
                title=user.display_name,
                subtitle=user.profile.headline,
                description=user.profile.bio,
                stacks=[tag.name_ru if locale == "ru" else tag.name_en for tag in user.stacks],
                similarity=_similarity(reference_stack, {tag.slug for tag in user.stacks}),
                meta={
                    "role": user.primary_role.value,
                    "executor_rating": float(user.profile.avg_executor_rating),
                    "completed_deals": user.completed_deals,
                },
            )
            for user in candidates
            if user.id != current_user.id and user.primary_role in {RoleMode.EXECUTOR, RoleMode.BOTH}
        ]
    else:
        orders = (
            await session.scalars(
                select(Order).options(selectinload(Order.stacks)).order_by(Order.created_at.desc())
            )
        ).all()
        cards = [
            SwipeCardResponse(
                entity_type="order",
                id=order.id,
                title=order.title,
                subtitle=order.category,
                description=order.summary,
                stacks=[tag.name_ru if locale == "ru" else tag.name_en for tag in order.stacks],
                similarity=_similarity(reference_stack, {tag.slug for tag in order.stacks}),
                meta={
                    "slug": order.slug,
                    "budget_amount": float(order.budget_amount),
                    "client_total_amount": float(order.client_total_amount),
                    "budget_type": order.budget_type.value,
                },
            )
            for order in orders
        ]

    min_similarity = settings.features.swipe_min_similarity
    filtered = [card for card in cards if card.similarity >= min_similarity or not reference_stack]
    return _mix_cards(filtered, settings.features.swipe_mix_strategy)


def _similarity(reference: set[str], candidate: set[str]) -> float:
    if not reference and not candidate:
        return 0.5
    if not reference or not candidate:
        return 0.0
    union = reference | candidate
    if not union:
        return 0.0
    return round(len(reference & candidate) / len(union), 2)


def _mix_cards(cards: list[SwipeCardResponse], strategy: str) -> list[SwipeCardResponse]:
    ordered = sorted(cards, key=lambda item: item.similarity, reverse=True)
    if strategy != "mixed" or len(ordered) < 3:
        return ordered

    top_bucket = ordered[::2]
    mid_bucket = ordered[1::2]
    Random(7).shuffle(mid_bucket)

    mixed: list[SwipeCardResponse] = []
    for index in range(max(len(top_bucket), len(mid_bucket))):
        if index < len(top_bucket):
            mixed.append(top_bucket[index])
        if index < len(mid_bucket):
            mixed.append(mid_bucket[index])
    return mixed
