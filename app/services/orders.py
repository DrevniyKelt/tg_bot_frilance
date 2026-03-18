from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.utils import format_money, make_slug, money_to_decimal
from app.db.models import (
    BudgetType,
    Currency,
    Order,
    OrderStatus,
    StackMode,
    Subscription,
    SubscriptionStatus,
    StackTag,
    User,
)
from app.schemas.order import CreateOrderRequest, OrderCardResponse, OrderListResponse
from app.services.catalog import normalize_stack_slugs, resolve_stack_tags


def active_subscription_name(user: User) -> str | None:
    now = datetime.now(timezone.utc)
    for subscription in user.subscriptions:
        if (
            subscription.status == SubscriptionStatus.ACTIVE
            and subscription.ends_at
            and subscription.ends_at >= now
        ):
            return subscription.tariff.name_ru
    return None


def has_active_subscription(user: User) -> bool:
    now = datetime.now(timezone.utc)
    for subscription in user.subscriptions:
        if (
            subscription.status == SubscriptionStatus.ACTIVE
            and subscription.ends_at
            and subscription.ends_at >= now
        ):
            return True
    return False


def calculate_fee(user: User, amount: Decimal) -> tuple[Decimal, Decimal, Decimal]:
    settings = get_settings()
    clean_amount = money_to_decimal(amount)
    if has_active_subscription(user):
        return Decimal("0.00"), clean_amount, clean_amount

    fee_percent = Decimal(str(settings.features.fee_percent))
    fee_amount = (clean_amount * fee_percent).quantize(Decimal("0.01"))

    if settings.features.fee_mode == "deduct":
        return fee_percent, clean_amount, clean_amount + fee_amount

    return fee_percent, clean_amount - fee_amount, clean_amount


async def list_orders(
    session: AsyncSession,
    *,
    locale: str,
    q: str | None = None,
    stack: list[str] | str | None = None,
    min_budget: Decimal | None = None,
    max_budget: Decimal | None = None,
    status_filter: str | None = None,
) -> OrderListResponse:
    normalized_stack_filters = await normalize_stack_slugs(session, stack)
    orders = (
        await session.scalars(
            select(Order)
            .options(
                selectinload(Order.stacks),
                selectinload(Order.client).selectinload(User.profile),
                selectinload(Order.client)
                .selectinload(User.subscriptions)
                .selectinload(Subscription.tariff),
            )
            .order_by(Order.created_at.desc())
        )
    ).all()
    filtered: list[Order] = []

    for order in orders:
        if q:
            haystack = f"{order.title} {order.summary} {order.description}".lower()
            if q.lower() not in haystack:
                continue
        if status_filter and order.status.value != status_filter:
            continue
        if min_budget is not None and order.budget_amount < min_budget:
            continue
        if max_budget is not None and order.budget_amount > max_budget:
            continue
        if normalized_stack_filters:
            order_slugs = {tag.slug for tag in order.stacks}
            if not order_slugs.intersection(normalized_stack_filters):
                continue
        filtered.append(order)

    items = [serialize_order(order, locale=locale) for order in filtered]
    return OrderListResponse(
        items=items,
        total=len(items),
        normalized_stack_filters=normalized_stack_filters,
    )


async def get_order_by_slug(session: AsyncSession, slug: str) -> Order | None:
    return await session.scalar(
        select(Order)
        .options(
            selectinload(Order.stacks),
            selectinload(Order.client).selectinload(User.profile),
            selectinload(Order.client)
            .selectinload(User.subscriptions)
            .selectinload(Subscription.tariff),
        )
        .where(Order.slug == slug)
    )


async def create_order(session: AsyncSession, user: User, payload: CreateOrderRequest) -> Order:
    settings = get_settings()
    if settings.features.require_tariff_after_first_completed and user.completed_deals >= 1 and not has_active_subscription(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tariff is required after the first completed deal.",
        )

    existing_user_orders = await session.scalar(
        select(func.count(Order.id)).where(Order.client_id == user.id)
    )
    if user.completed_deals == 0 and existing_user_orders >= settings.features.new_user_max_orders:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="New user order boost limit reached.",
        )

    stack_tags = await resolve_stack_tags(session, payload.stack_slugs)
    if payload.stack_mode == StackMode.SPECIFIC.value and not stack_tags:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Specific stack mode requires at least one valid stack tag.",
        )

    slug = await _make_unique_order_slug(session, payload.title)
    fee_percent, executor_amount, client_total_amount = calculate_fee(user, payload.budget_amount)
    order = Order(
        slug=slug,
        client_id=user.id,
        title=payload.title,
        category=payload.category,
        summary=payload.summary,
        description=payload.description,
        budget_type=BudgetType(payload.budget_type),
        currency=Currency(payload.currency),
        stack_mode=StackMode(payload.stack_mode),
        status=OrderStatus.PUBLISHED,
        budget_amount=money_to_decimal(payload.budget_amount),
        executor_amount=executor_amount,
        client_total_amount=client_total_amount,
        fee_percent=fee_percent,
        auto_filters=payload.auto_filters,
        stacks=stack_tags,
    )
    session.add(order)
    await session.commit()
    await session.refresh(order)
    return order


def serialize_order(order: Order, *, locale: str, similarity: float | None = None) -> OrderCardResponse:
    return OrderCardResponse(
        id=order.id,
        slug=order.slug,
        title=order.title,
        category=order.category,
        summary=order.summary,
        description=order.description,
        status=order.status.value,
        budget_type=order.budget_type.value,
        currency=order.currency.value,
        stack_mode=order.stack_mode.value,
        budget_amount=order.budget_amount,
        executor_amount=order.executor_amount,
        client_total_amount=order.client_total_amount,
        fee_percent=order.fee_percent,
        auto_filters=order.auto_filters or {},
        stacks=[tag.name_ru if locale == "ru" else tag.name_en for tag in order.stacks],
        client_name=order.client.display_name,
        client_role=order.client.primary_role.value,
        created_at=order.created_at.date().isoformat(),
        similarity=similarity,
    )


def order_budget_preview(user: User, amount: Decimal) -> dict[str, str]:
    fee_percent, executor_amount, client_total_amount = calculate_fee(user, amount)
    return {
        "fee_percent": str((fee_percent * 100).quantize(Decimal("0.01"))),
        "executor_amount": format_money(executor_amount),
        "client_total_amount": format_money(client_total_amount),
    }


async def _make_unique_order_slug(session: AsyncSession, title: str) -> str:
    base_slug = make_slug(title)[:120] or "order"
    existing = (
        await session.scalars(select(Order.slug).where(Order.slug.like(f"{base_slug}%")).order_by(Order.slug))
    ).all()
    if base_slug not in existing:
        return base_slug
    return f"{base_slug}-{len(existing) + 1}"
