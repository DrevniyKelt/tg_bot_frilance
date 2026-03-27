from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import HTTPException, status

from app.db.models import Application, ApplicationStatus, EscrowStatus, Order, OrderStatus, User, utcnow
from app.services.wallet import finalize_order_release


async def start_order_work(
    session: AsyncSession,
    *,
    order: Order,
    actor: User,
) -> Order:
    if actor.id != order.client_id and not await _is_selected_executor(session, order_id=order.id, user_id=actor.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only selected participants can start the order.")
    if order.status != OrderStatus.MATCHED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only matched orders can be moved into progress.")
    if order.escrow_status != EscrowStatus.HELD:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Escrow must be funded before work starts.")

    order.status = OrderStatus.IN_PROGRESS
    if order.started_at is None:
        order.started_at = utcnow()
    await session.commit()
    await session.refresh(order)
    return order


async def confirm_order_completion(
    session: AsyncSession,
    *,
    order: Order,
    actor: User,
) -> Order:
    if order.status != OrderStatus.IN_PROGRESS:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only orders in progress can be confirmed.")

    is_selected_executor = await _is_selected_executor(session, order_id=order.id, user_id=actor.id)
    if actor.id == order.client_id:
        order.client_completion_confirmed_at = order.client_completion_confirmed_at or utcnow()
    elif is_selected_executor:
        order.executor_completion_confirmed_at = order.executor_completion_confirmed_at or utcnow()
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only client or selected executors can confirm completion.")

    if order.client_completion_confirmed_at and order.executor_completion_confirmed_at:
        await finalize_order_release(session, order=order)
    else:
        await session.commit()
        await session.refresh(order)
    return order


async def _is_selected_executor(session: AsyncSession, *, order_id: int, user_id: int) -> bool:
    application = await session.scalar(
        select(Application.id).where(
            Application.order_id == order_id,
            Application.executor_id == user_id,
            Application.status == ApplicationStatus.SELECTED,
        )
    )
    return application is not None
