from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.i18n import detect_locale
from app.db.models import User
from app.db.session import get_db_session
from app.schemas.order import CreateOrderRequest, OrderCardResponse, OrderListResponse, SwipeCardResponse
from app.services.orders import create_order, get_order_by_slug, list_orders, serialize_order
from app.services.swipe import build_swipe_cards


router = APIRouter()


@router.get("/orders/swipe", response_model=list[SwipeCardResponse])
async def swipe_orders(
    request: Request,
    target: str = Query(default="orders", pattern="^(orders|executors)$"),
    stack: str | None = None,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[SwipeCardResponse]:
    locale = detect_locale(request, get_settings())
    return await build_swipe_cards(session, current_user, target=target, stack=stack, locale=locale)


@router.get("/orders", response_model=OrderListResponse)
async def api_list_orders(
    request: Request,
    q: str | None = None,
    stack: str | None = None,
    min_budget: Decimal | None = None,
    max_budget: Decimal | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    session: AsyncSession = Depends(get_db_session),
) -> OrderListResponse:
    locale = detect_locale(request, get_settings())
    return await list_orders(
        session,
        locale=locale,
        q=q,
        stack=stack,
        min_budget=min_budget,
        max_budget=max_budget,
        status_filter=status_filter,
    )


@router.post("/orders", response_model=OrderCardResponse, status_code=status.HTTP_201_CREATED)
async def api_create_order(
    request: Request,
    payload: CreateOrderRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> OrderCardResponse:
    locale = detect_locale(request, get_settings())
    order = await create_order(session, current_user, payload)
    return serialize_order(order, locale=locale)


@router.get("/orders/{order_slug}", response_model=OrderCardResponse)
async def api_get_order(
    order_slug: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> OrderCardResponse:
    locale = detect_locale(request, get_settings())
    order = await get_order_by_slug(session, order_slug)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
    return serialize_order(order, locale=locale)
