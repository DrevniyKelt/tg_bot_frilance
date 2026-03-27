from __future__ import annotations

from random import Random

from fastapi import HTTPException, status
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.db.models import (
    Order,
    OrderStatus,
    RoleMode,
    SwipeActorSide,
    SwipeDecision,
    SwipeDecisionDirection,
    User,
)
from app.schemas.order import SwipeCardResponse
from app.services.chats import ensure_chat_for_order_pair, serialize_chat
from app.services.catalog import normalize_stack_slugs
from app.services.profiles import get_public_user


async def build_swipe_cards(
    session: AsyncSession,
    current_user: User,
    *,
    target: str,
    stack: list[str] | str | None = None,
    locale: str,
    source_order_id: int | None = None,
) -> list[SwipeCardResponse]:
    settings = get_settings()
    normalized_filters = await normalize_stack_slugs(session, stack)
    reference_stack = set(normalized_filters or [tag.slug for tag in current_user.stacks])
    source_order = await _resolve_source_order(session, current_user=current_user, source_order_id=source_order_id)
    decisions = await _get_swipe_decisions(
        session,
        current_user=current_user,
        target=target,
        source_order=source_order,
    )

    if target == "executors":
        candidates = (
            await session.scalars(
                select(User)
                .options(selectinload(User.profile), selectinload(User.stacks))
                .order_by(User.display_name)
            )
        ).all()
        cards = []
        for user in candidates:
            if user.id == current_user.id or user.primary_role not in {RoleMode.EXECUTOR, RoleMode.BOTH}:
                continue
            card = SwipeCardResponse(
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
                    "source_order_title": source_order.title if source_order else None,
                },
                action_url=f"/profile?user_id={user.id}",
            )
            _apply_executor_card_state(card, decisions, executor_id=user.id, locale=locale)
            cards.append(card)
    else:
        orders = (
            await session.scalars(
                select(Order)
                .options(selectinload(Order.client), selectinload(Order.stacks))
                .where(Order.status.in_([OrderStatus.PUBLISHED, OrderStatus.IN_REVIEW, OrderStatus.MATCHED]))
                .order_by(Order.created_at.desc())
            )
        ).all()
        cards = []
        for order in orders:
            card = SwipeCardResponse(
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
                    "client_name": order.client.display_name,
                },
                action_url=f"/orders/{order.slug}",
            )
            _apply_order_card_state(card, decisions, order_id=order.id, locale=locale)
            cards.append(card)

    min_similarity = settings.features.swipe_min_similarity
    filtered = [card for card in cards if card.similarity >= min_similarity or not reference_stack]
    if len(filtered) < min(4, len(cards)):
        filtered = sorted(cards, key=lambda item: item.similarity, reverse=True)[:8]
    mixed = _mix_cards(filtered, settings.features.swipe_mix_strategy)
    return mixed


async def record_swipe_decision(
    session: AsyncSession,
    *,
    actor: User,
    target: str,
    direction: str,
    target_id: int,
    source_order_id: int | None = None,
    locale: str,
) -> dict:
    swipe_direction = SwipeDecisionDirection(direction)
    if target == "executors":
        source_order = await _resolve_source_order(session, current_user=actor, source_order_id=source_order_id)
        if source_order is None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No open source order for matching.")
        executor = await get_public_user(session, target_id)
        if executor is None or executor.id == actor.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Executor not found.")
        decision = await _upsert_decision(
            session,
            actor=actor,
            order=source_order,
            executor_id=executor.id,
            actor_side=SwipeActorSide.CLIENT,
            direction=swipe_direction,
        )
        match_payload = await _finalize_match_if_ready(
            session,
            order=source_order,
            executor_id=executor.id,
            locale=locale,
        )
        return {
            "matched": match_payload is not None,
            "direction": direction,
            "status_label": _card_status_label_from_decision(
                by_you=decision.direction == SwipeDecisionDirection.ACCEPT,
                selected_you=match_payload is not None,
                rejected_by_you=decision.direction == SwipeDecisionDirection.REJECT,
                rejected_you=False,
                locale=locale,
            ),
            "chat_url": match_payload["chat_url"] if match_payload else None,
            "chat_id": match_payload["chat_id"] if match_payload else None,
            "executor_name": executor.display_name,
        }

    order = await session.scalar(
        select(Order).options(selectinload(Order.client)).where(Order.id == target_id)
    )
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
    decision = await _upsert_decision(
        session,
        actor=actor,
        order=order,
        executor_id=actor.id,
        actor_side=SwipeActorSide.EXECUTOR,
        direction=swipe_direction,
    )
    match_payload = await _finalize_match_if_ready(
        session,
        order=order,
        executor_id=actor.id,
        locale=locale,
    )
    return {
        "matched": match_payload is not None,
        "direction": direction,
        "status_label": _card_status_label_from_decision(
            by_you=decision.direction == SwipeDecisionDirection.ACCEPT,
            selected_you=match_payload is not None,
            rejected_by_you=decision.direction == SwipeDecisionDirection.REJECT,
            rejected_you=False,
            locale=locale,
        ),
        "chat_url": match_payload["chat_url"] if match_payload else None,
        "chat_id": match_payload["chat_id"] if match_payload else None,
        "order_title": order.title,
    }


async def _resolve_source_order(
    session: AsyncSession,
    *,
    current_user: User,
    source_order_id: int | None,
) -> Order | None:
    query = (
        select(Order)
        .options(selectinload(Order.client), selectinload(Order.stacks))
        .where(
            Order.client_id == current_user.id,
            Order.status.in_([OrderStatus.PUBLISHED, OrderStatus.IN_REVIEW, OrderStatus.MATCHED]),
        )
        .order_by(Order.created_at.desc())
    )
    orders = (await session.scalars(query)).all()
    if not orders:
        return None
    if source_order_id is not None:
        for order in orders:
            if order.id == source_order_id:
                return order
    return orders[0]


async def list_swipe_source_orders(session: AsyncSession, *, user: User) -> list[Order]:
    return (
        await session.scalars(
            select(Order)
            .where(
                Order.client_id == user.id,
                Order.status.in_([OrderStatus.PUBLISHED, OrderStatus.IN_REVIEW, OrderStatus.MATCHED]),
            )
            .order_by(Order.created_at.desc())
        )
    ).all()


async def _get_swipe_decisions(
    session: AsyncSession,
    *,
    current_user: User,
    target: str,
    source_order: Order | None,
) -> list[SwipeDecision]:
    if target == "executors" and source_order is not None:
        query = select(SwipeDecision).where(SwipeDecision.order_id == source_order.id)
    else:
        query = select(SwipeDecision).where(
            or_(SwipeDecision.actor_user_id == current_user.id, SwipeDecision.executor_id == current_user.id)
        )
    return (
        await session.scalars(
            query.order_by(SwipeDecision.updated_at.desc())
        )
    ).all()


async def _upsert_decision(
    session: AsyncSession,
    *,
    actor: User,
    order: Order,
    executor_id: int,
    actor_side: SwipeActorSide,
    direction: SwipeDecisionDirection,
) -> SwipeDecision:
    existing = await session.scalar(
        select(SwipeDecision).where(
            SwipeDecision.actor_user_id == actor.id,
            SwipeDecision.order_id == order.id,
            SwipeDecision.executor_id == executor_id,
            SwipeDecision.actor_side == actor_side,
        )
    )
    if existing is None:
        existing = SwipeDecision(
            actor_user_id=actor.id,
            order_id=order.id,
            executor_id=executor_id,
            actor_side=actor_side,
            direction=direction,
        )
        session.add(existing)
    else:
        existing.direction = direction
    await session.commit()
    await session.refresh(existing)
    return existing


async def _finalize_match_if_ready(
    session: AsyncSession,
    *,
    order: Order,
    executor_id: int,
    locale: str,
) -> dict | None:
    client_decision = await session.scalar(
        select(SwipeDecision).where(
            SwipeDecision.order_id == order.id,
            SwipeDecision.executor_id == executor_id,
            SwipeDecision.actor_side == SwipeActorSide.CLIENT,
            SwipeDecision.direction == SwipeDecisionDirection.ACCEPT,
        )
    )
    executor_decision = await session.scalar(
        select(SwipeDecision).where(
            SwipeDecision.order_id == order.id,
            SwipeDecision.executor_id == executor_id,
            SwipeDecision.actor_side == SwipeActorSide.EXECUTOR,
            SwipeDecision.direction == SwipeDecisionDirection.ACCEPT,
        )
    )
    if client_decision is None or executor_decision is None:
        return None

    executor = await get_public_user(session, executor_id)
    if executor is None:
        return None
    chat = await ensure_chat_for_order_pair(session, order=order, client=order.client, executor=executor)
    if client_decision.matched_at is None:
        client_decision.matched_at = chat.updated_at
    if executor_decision.matched_at is None:
        executor_decision.matched_at = chat.updated_at
    await session.commit()
    serialized_chat = serialize_chat(chat).model_dump()
    return {
        "title": "Это мэтч" if locale == "ru" else "It is a match",
        "chat_id": serialized_chat["id"],
        "chat_url": f"/chats/{serialized_chat['id']}",
    }


def _apply_executor_card_state(
    card: SwipeCardResponse,
    decisions: list[SwipeDecision],
    *,
    executor_id: int,
    locale: str,
) -> None:
    client_decision = next(
        (
            item
            for item in decisions
            if item.executor_id == executor_id and item.actor_side == SwipeActorSide.CLIENT
        ),
        None,
    )
    executor_decision = next(
        (
            item
            for item in decisions
            if item.executor_id == executor_id and item.actor_side == SwipeActorSide.EXECUTOR
        ),
        None,
    )
    _attach_decision_state(
        card,
        by_you=client_decision,
        opposite=executor_decision,
        locale=locale,
    )


def _apply_order_card_state(
    card: SwipeCardResponse,
    decisions: list[SwipeDecision],
    *,
    order_id: int,
    locale: str,
) -> None:
    client_decision = next(
        (
            item
            for item in decisions
            if item.order_id == order_id and item.actor_side == SwipeActorSide.CLIENT
        ),
        None,
    )
    executor_decision = next(
        (
            item
            for item in decisions
            if item.order_id == order_id and item.actor_side == SwipeActorSide.EXECUTOR
        ),
        None,
    )
    _attach_decision_state(
        card,
        by_you=executor_decision,
        opposite=client_decision,
        locale=locale,
    )


def _attach_decision_state(
    card: SwipeCardResponse,
    *,
    by_you: SwipeDecision | None,
    opposite: SwipeDecision | None,
    locale: str,
) -> None:
    card.selected_by_you = bool(by_you and by_you.direction == SwipeDecisionDirection.ACCEPT)
    card.rejected_by_you = bool(by_you and by_you.direction == SwipeDecisionDirection.REJECT)
    card.selected_you = bool(opposite and opposite.direction == SwipeDecisionDirection.ACCEPT)
    card.rejected_you = bool(opposite and opposite.direction == SwipeDecisionDirection.REJECT)
    card.match_ready = bool(
        by_you
        and opposite
        and by_you.direction == SwipeDecisionDirection.ACCEPT
        and opposite.direction == SwipeDecisionDirection.ACCEPT
    )
    card.match_label = "Мэтч" if locale == "ru" else "Match" if card.match_ready else None
    if card.match_ready:
        card.status_label = "У вас мэтч" if locale == "ru" else "You matched"
        card.status_tone = "match"
        return
    if card.selected_by_you:
        card.status_label = "Ты выбрал" if locale == "ru" else "You liked"
        card.status_tone = "accept"
        return
    if card.selected_you:
        card.status_label = "Выбрали тебя" if locale == "ru" else "Liked you"
        card.status_tone = "accept"
        return
    if card.rejected_by_you:
        card.status_label = "Ты отказался" if locale == "ru" else "You passed"
        card.status_tone = "reject"
        return
    if card.rejected_you:
        card.status_label = "Тебя пропустили" if locale == "ru" else "They passed"
        card.status_tone = "reject"
        return
    card.status_label = None
    card.status_tone = "neutral"


def _card_status_label_from_decision(
    *,
    by_you: bool,
    selected_you: bool,
    rejected_by_you: bool,
    rejected_you: bool,
    locale: str,
) -> str:
    if by_you and selected_you:
        return "У вас мэтч" if locale == "ru" else "You matched"
    if by_you:
        return "Ты выбрал" if locale == "ru" else "You liked"
    if rejected_by_you:
        return "Ты отказался" if locale == "ru" else "You passed"
    if rejected_you:
        return "Тебя пропустили" if locale == "ru" else "They passed"
    return "Обновлено" if locale == "ru" else "Updated"


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
    ordered = sorted(cards, key=lambda item: (item.match_ready, item.similarity), reverse=True)
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
