from __future__ import annotations

from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.utils import money_to_decimal
from app.db.models import (
    Application,
    ApplicationStatus,
    Currency,
    EscrowStatus,
    Order,
    OrderStatus,
    User,
    WalletTransaction,
    WalletTransactionKind,
    WalletTransactionStatus,
)
from app.schemas.wallet import WalletTransactionResponse


async def topup_wallet(
    session: AsyncSession,
    *,
    user: User,
    amount: Decimal,
    currency: str,
    note: str,
) -> WalletTransaction:
    normalized_amount = money_to_decimal(amount)
    user.profile.wallet_balance += normalized_amount
    tx = WalletTransaction(
        user_id=user.id,
        kind=WalletTransactionKind.TOPUP,
        status=WalletTransactionStatus.SUCCEEDED,
        currency=Currency(currency),
        amount=normalized_amount,
        balance_after=user.profile.wallet_balance,
        note=note,
    )
    session.add(tx)
    await session.commit()
    await session.refresh(tx)
    return tx


async def withdraw_wallet(
    session: AsyncSession,
    *,
    user: User,
    amount: Decimal,
    currency: str,
    note: str,
) -> WalletTransaction:
    normalized_amount = money_to_decimal(amount)
    _ensure_sufficient_balance(user, normalized_amount)
    user.profile.wallet_balance -= normalized_amount
    tx = WalletTransaction(
        user_id=user.id,
        kind=WalletTransactionKind.WITHDRAW,
        status=WalletTransactionStatus.SUCCEEDED,
        currency=Currency(currency),
        amount=-normalized_amount,
        balance_after=user.profile.wallet_balance,
        note=note,
    )
    session.add(tx)
    await session.commit()
    await session.refresh(tx)
    return tx


async def fund_order_escrow(
    session: AsyncSession,
    *,
    order: Order,
    client: User,
) -> WalletTransaction:
    if order.client_id != client.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the order owner can fund escrow.")
    if order.status != OrderStatus.MATCHED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Escrow can only be funded for matched orders.")
    if order.escrow_status != EscrowStatus.NONE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Escrow is already funded or settled.")

    amount = money_to_decimal(order.client_total_amount)
    _ensure_sufficient_balance(client, amount)
    client.profile.wallet_balance -= amount
    order.escrow_status = EscrowStatus.HELD
    order.escrow_amount = amount
    tx = WalletTransaction(
        user_id=client.id,
        order_id=order.id,
        kind=WalletTransactionKind.ESCROW_HOLD,
        status=WalletTransactionStatus.SUCCEEDED,
        currency=order.currency,
        amount=-amount,
        balance_after=client.profile.wallet_balance,
        note=f"Escrow hold for order {order.slug}",
    )
    session.add(tx)
    await session.commit()
    await session.refresh(tx)
    return tx


async def refund_order_escrow(
    session: AsyncSession,
    *,
    order: Order,
    client: User,
) -> WalletTransaction:
    if order.client_id != client.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the order owner can refund escrow.")
    if order.escrow_status != EscrowStatus.HELD:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only held escrow can be refunded.")

    amount = money_to_decimal(order.escrow_amount)
    client.profile.wallet_balance += amount
    order.escrow_status = EscrowStatus.REFUNDED
    tx = WalletTransaction(
        user_id=client.id,
        order_id=order.id,
        kind=WalletTransactionKind.ESCROW_REFUND,
        status=WalletTransactionStatus.SUCCEEDED,
        currency=order.currency,
        amount=amount,
        balance_after=client.profile.wallet_balance,
        note=f"Escrow refund for order {order.slug}",
    )
    session.add(tx)
    await session.commit()
    await session.refresh(tx)
    return tx


async def release_order_escrow(
    session: AsyncSession,
    *,
    order: Order,
    client: User,
) -> list[WalletTransaction]:
    if order.client_id != client.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the order owner can release escrow.")
    return await finalize_order_release(session, order=order)


async def list_wallet_transactions(session: AsyncSession, *, user: User) -> list[WalletTransaction]:
    return (
        await session.scalars(
            select(WalletTransaction)
            .where(WalletTransaction.user_id == user.id)
            .order_by(WalletTransaction.created_at.desc())
        )
    ).all()


def serialize_wallet_transaction(tx: WalletTransaction) -> WalletTransactionResponse:
    return WalletTransactionResponse(
        id=tx.id,
        user_id=tx.user_id,
        order_id=tx.order_id,
        kind=tx.kind.value,
        status=tx.status.value,
        currency=tx.currency.value,
        amount=tx.amount,
        balance_after=tx.balance_after,
        note=tx.note,
        created_at=tx.created_at.isoformat(),
    )


def _ensure_sufficient_balance(user: User, amount: Decimal) -> None:
    if user.profile.wallet_balance < amount:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Insufficient wallet balance.")


async def finalize_order_release(
    session: AsyncSession,
    *,
    order: Order,
) -> list[WalletTransaction]:
    if order.escrow_status != EscrowStatus.HELD:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only held escrow can be released.")

    client = order.client
    selected_applications = (
        await session.scalars(
            select(Application)
            .options(selectinload(Application.executor).selectinload(User.profile))
            .where(
                Application.order_id == order.id,
                Application.status == ApplicationStatus.SELECTED,
            )
            .order_by(Application.id)
        )
    ).all()
    if not selected_applications:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No selected executors for payout.")

    payout_amount = money_to_decimal(order.executor_amount / Decimal(len(selected_applications)))
    order.escrow_status = EscrowStatus.RELEASED
    order.status = OrderStatus.COMPLETED
    order.completed_at = order.completed_at or order.client_completion_confirmed_at or order.executor_completion_confirmed_at
    client.completed_deals += 1
    transactions: list[WalletTransaction] = []

    for application in selected_applications:
        application.executor.profile.wallet_balance += payout_amount
        application.executor.completed_deals += 1
        tx = WalletTransaction(
            user_id=application.executor_id,
            order_id=order.id,
            kind=WalletTransactionKind.ESCROW_RELEASE,
            status=WalletTransactionStatus.SUCCEEDED,
            currency=order.currency,
            amount=payout_amount,
            balance_after=application.executor.profile.wallet_balance,
            note=f"Escrow release for order {order.slug}",
        )
        session.add(tx)
        transactions.append(tx)

    await session.commit()
    for tx in transactions:
        await session.refresh(tx)
    return transactions
