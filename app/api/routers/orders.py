from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.i18n import detect_locale
from app.db.models import User
from app.db.session import get_db_session
from app.schemas.application import ApplicationCardResponse, SelectExecutorsRequest
from app.schemas.order import CreateOrderRequest, OrderCardResponse, OrderListResponse, SwipeCardResponse
from app.services.applications import list_order_applications, select_executors, serialize_application
from app.services.deals import confirm_order_completion, start_order_work
from app.services.orders import create_order, get_order_by_slug, list_orders, serialize_order
from app.services.swipe import build_swipe_cards


router = APIRouter()


@router.get("/orders/swipe", response_model=list[SwipeCardResponse])
async def swipe_orders(
    request: Request,
    target: str = Query(default="orders", pattern="^(orders|executors)$"),
    stack: str | None = None,
    source_order_id: int | None = None,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[SwipeCardResponse]:
    locale = detect_locale(request, get_settings())
    return await build_swipe_cards(
        session,
        current_user,
        target=target,
        stack=stack,
        locale=locale,
        source_order_id=source_order_id,
    )


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


@router.get("/orders/{order_slug}/applications", response_model=list[ApplicationCardResponse])
async def api_list_order_applications(
    order_slug: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[ApplicationCardResponse]:
    order = await get_order_by_slug(session, order_slug)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
    if current_user.id != order.client_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the order owner can view applications.")
    applications = await list_order_applications(session, order_id=order.id)
    return [serialize_application(application) for application in applications]


@router.post("/orders/{order_slug}/select_executor", response_model=list[ApplicationCardResponse])
async def api_select_executor(
    order_slug: str,
    payload: SelectExecutorsRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[ApplicationCardResponse]:
    order = await get_order_by_slug(session, order_slug)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
    selected = await select_executors(
        session,
        order=order,
        client=current_user,
        application_ids=payload.application_ids,
    )
    return [serialize_application(application) for application in selected]


@router.post("/orders/{order_slug}/start", response_model=OrderCardResponse)
async def api_start_order(
    order_slug: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> OrderCardResponse:
    locale = detect_locale(request, get_settings())
    order = await get_order_by_slug(session, order_slug)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
    order = await start_order_work(session, order=order, actor=current_user)
    return serialize_order(order, locale=locale)


@router.post("/orders/{order_slug}/confirm", response_model=OrderCardResponse)
async def api_confirm_order_completion(
    order_slug: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> OrderCardResponse:
    locale = detect_locale(request, get_settings())
    order = await get_order_by_slug(session, order_slug)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
    order = await confirm_order_completion(session, order=order, actor=current_user)
    return serialize_order(order, locale=locale)
