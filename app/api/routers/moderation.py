from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_db_session
from app.schemas.moderation import CreateModerationTicketRequest, ModerationTicketResponse
from app.services.moderation import (
    ban_user,
    create_moderation_ticket,
    ensure_admin,
    get_ticket_by_id,
    hide_order,
    list_moderation_tickets,
    resolve_ticket,
    serialize_ticket,
)
from app.services.orders import get_order_by_slug
from app.services.profiles import get_public_user


router = APIRouter()


@router.post("/orders/{order_slug}/report", response_model=ModerationTicketResponse, status_code=status.HTTP_201_CREATED)
async def api_report_order(
    order_slug: str,
    payload: CreateModerationTicketRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ModerationTicketResponse:
    order = await get_order_by_slug(session, order_slug)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
    ticket = await create_moderation_ticket(session, reporter=current_user, order=order, payload=payload)
    return serialize_ticket(ticket)


@router.get("/admin/moderation", response_model=list[ModerationTicketResponse])
async def api_list_tickets(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[ModerationTicketResponse]:
    ensure_admin(current_user)
    tickets = await list_moderation_tickets(session)
    return [serialize_ticket(ticket) for ticket in tickets]


@router.post("/admin/moderation/{ticket_id}/resolve", response_model=ModerationTicketResponse)
async def api_resolve_ticket(
    ticket_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ModerationTicketResponse:
    ensure_admin(current_user)
    ticket = await resolve_ticket(session, ticket_id=ticket_id)
    return serialize_ticket(ticket)


@router.post("/admin/orders/{order_slug}/hide")
async def api_hide_order(
    order_slug: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, bool]:
    ensure_admin(current_user)
    order = await get_order_by_slug(session, order_slug)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
    await hide_order(session, order=order)
    return {"ok": True}


@router.post("/admin/users/{user_id}/ban")
async def api_ban_user(
    user_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, bool]:
    ensure_admin(current_user)
    user = await get_public_user(session, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    await ban_user(session, user=user)
    return {"ok": True}
