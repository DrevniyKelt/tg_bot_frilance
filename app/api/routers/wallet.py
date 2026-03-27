from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_db_session
from app.schemas.wallet import WalletTopupRequest, WalletTransactionResponse, WalletWithdrawRequest
from app.services.orders import get_order_by_slug
from app.services.wallet import (
    fund_order_escrow,
    list_wallet_transactions,
    refund_order_escrow,
    release_order_escrow,
    serialize_wallet_transaction,
    topup_wallet,
    withdraw_wallet,
)


router = APIRouter()


@router.get("/wallet/transactions", response_model=list[WalletTransactionResponse])
async def api_list_wallet_transactions(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[WalletTransactionResponse]:
    txs = await list_wallet_transactions(session, user=current_user)
    return [serialize_wallet_transaction(tx) for tx in txs]


@router.post("/wallet/topup", response_model=WalletTransactionResponse, status_code=status.HTTP_201_CREATED)
async def api_wallet_topup(
    payload: WalletTopupRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> WalletTransactionResponse:
    tx = await topup_wallet(session, user=current_user, amount=payload.amount, currency=payload.currency, note=payload.note)
    return serialize_wallet_transaction(tx)


@router.post("/wallet/withdraw", response_model=WalletTransactionResponse, status_code=status.HTTP_201_CREATED)
async def api_wallet_withdraw(
    payload: WalletWithdrawRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> WalletTransactionResponse:
    tx = await withdraw_wallet(session, user=current_user, amount=payload.amount, currency=payload.currency, note=payload.note)
    return serialize_wallet_transaction(tx)


@router.post("/orders/{order_slug}/escrow/fund", response_model=WalletTransactionResponse, status_code=status.HTTP_201_CREATED)
async def api_fund_escrow(
    order_slug: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> WalletTransactionResponse:
    order = await get_order_by_slug(session, order_slug)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
    tx = await fund_order_escrow(session, order=order, client=current_user)
    return serialize_wallet_transaction(tx)


@router.post("/orders/{order_slug}/escrow/refund", response_model=WalletTransactionResponse, status_code=status.HTTP_201_CREATED)
async def api_refund_escrow(
    order_slug: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> WalletTransactionResponse:
    order = await get_order_by_slug(session, order_slug)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
    tx = await refund_order_escrow(session, order=order, client=current_user)
    return serialize_wallet_transaction(tx)


@router.post("/orders/{order_slug}/escrow/release", response_model=list[WalletTransactionResponse], status_code=status.HTTP_201_CREATED)
async def api_release_escrow(
    order_slug: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[WalletTransactionResponse]:
    order = await get_order_by_slug(session, order_slug)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
    txs = await release_order_escrow(session, order=order, client=current_user)
    return [serialize_wallet_transaction(tx) for tx in txs]
