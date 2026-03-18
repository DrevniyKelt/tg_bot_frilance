from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field


class OrderCardResponse(BaseModel):
    id: int
    slug: str
    title: str
    category: str
    summary: str
    description: str
    status: str
    budget_type: str
    currency: str
    stack_mode: str
    budget_amount: Decimal
    executor_amount: Decimal
    client_total_amount: Decimal
    fee_percent: Decimal
    auto_filters: dict[str, Any]
    stacks: list[str]
    client_name: str
    client_role: str
    created_at: str
    similarity: float | None = None


class OrderListResponse(BaseModel):
    items: list[OrderCardResponse]
    total: int
    normalized_stack_filters: list[str]


class CreateOrderRequest(BaseModel):
    title: str = Field(min_length=6, max_length=180)
    category: str = Field(min_length=2, max_length=120)
    summary: str = Field(min_length=12, max_length=240)
    description: str = Field(min_length=40, max_length=4000)
    budget_type: Literal["fixed", "auction"]
    currency: Literal["RUB", "ETH", "INTERNAL"] = "RUB"
    stack_mode: Literal["free", "specific"] = "specific"
    budget_amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    stack_slugs: list[str] = Field(default_factory=list, max_length=30)
    auto_filters: dict[str, Any] = Field(default_factory=dict)


class SwipeCardResponse(BaseModel):
    entity_type: Literal["order", "executor"]
    id: int
    title: str
    subtitle: str
    description: str
    stacks: list[str]
    similarity: float
    meta: dict[str, Any]
