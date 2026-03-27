from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class WalletTransactionResponse(BaseModel):
    id: int
    user_id: int
    order_id: int | None
    kind: str
    status: str
    currency: str
    amount: Decimal
    balance_after: Decimal
    note: str
    created_at: str


class WalletTopupRequest(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    currency: Literal["RUB", "ETH", "INTERNAL"] = "RUB"
    note: str = Field(default="Mock top-up", max_length=240)


class WalletWithdrawRequest(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    currency: Literal["RUB", "ETH", "INTERNAL"] = "RUB"
    note: str = Field(default="Mock withdraw", max_length=240)
