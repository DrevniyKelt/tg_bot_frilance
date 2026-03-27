from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.db.models import (
    ModerationTargetType,
    ModerationTicket,
    ModerationTicketStatus,
    Order,
    OrderStatus,
    User,
)
from app.schemas.moderation import CreateModerationTicketRequest, ModerationTicketResponse


def ensure_admin(user: User) -> None:
    settings = get_settings()
    if user.id != settings.demo.default_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")


async def create_moderation_ticket(
    session: AsyncSession,
    *,
    reporter: User,
    order: Order | None,
    payload: CreateModerationTicketRequest,
) -> ModerationTicket:
    target_user = None
    if payload.target_user_id is not None:
        target_user = await session.scalar(select(User).where(User.id == payload.target_user_id))
        if target_user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found.")

    ticket = ModerationTicket(
        reporter_id=reporter.id,
        target_type=ModerationTargetType(payload.target_type),
        target_user_id=target_user.id if target_user else None,
        order_id=order.id if order else None,
        reason=payload.reason.strip(),
    )
    session.add(ticket)
    await session.commit()
    await session.refresh(ticket)
    return await get_ticket_by_id(session, ticket.id)


async def list_moderation_tickets(session: AsyncSession) -> list[ModerationTicket]:
    return (
        await session.scalars(
            select(ModerationTicket)
            .options(
                selectinload(ModerationTicket.reporter),
                selectinload(ModerationTicket.target_user),
                selectinload(ModerationTicket.order),
            )
            .order_by(ModerationTicket.created_at.desc())
        )
    ).all()


async def get_ticket_by_id(session: AsyncSession, ticket_id: int) -> ModerationTicket | None:
    return await session.scalar(
        select(ModerationTicket)
        .options(
            selectinload(ModerationTicket.reporter),
            selectinload(ModerationTicket.target_user),
            selectinload(ModerationTicket.order),
        )
        .where(ModerationTicket.id == ticket_id)
    )


async def resolve_ticket(session: AsyncSession, *, ticket_id: int) -> ModerationTicket:
    ticket = await get_ticket_by_id(session, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found.")
    ticket.status = ModerationTicketStatus.RESOLVED
    await session.commit()
    return await get_ticket_by_id(session, ticket_id)


async def hide_order(session: AsyncSession, *, order: Order) -> Order:
    order.status = OrderStatus.BANNED
    await session.commit()
    await session.refresh(order)
    return order


async def ban_user(session: AsyncSession, *, user: User) -> User:
    user.is_banned = True
    await session.commit()
    await session.refresh(user)
    return user


def serialize_ticket(ticket: ModerationTicket) -> ModerationTicketResponse:
    return ModerationTicketResponse(
        id=ticket.id,
        reporter_id=ticket.reporter_id,
        target_type=ticket.target_type.value,
        target_user_id=ticket.target_user_id,
        order_id=ticket.order_id,
        reason=ticket.reason,
        status=ticket.status.value,
        created_at=ticket.created_at.isoformat(),
    )
