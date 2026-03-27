from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field


class ApplicationCardResponse(BaseModel):
    id: int
    order_id: int
    executor_id: int
    executor_name: str
    executor_headline: str
    executor_rating: Decimal
    status: str
    cover_letter: str
    proposed_amount: Decimal | None
    delivery_days: int | None
    attachment_name: str | None
    is_quick: bool
    created_at: str


class CreateApplicationRequest(BaseModel):
    cover_letter: str = Field(default="", max_length=2000)
    proposed_amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    delivery_days: int | None = Field(default=None, ge=1, le=365)
    attachment_name: str | None = Field(default=None, max_length=200)


class QuickApplicationRequest(BaseModel):
    attachment_name: str | None = Field(default=None, max_length=200)


class SelectExecutorsRequest(BaseModel):
    application_ids: list[int] = Field(min_length=1, max_length=10)
