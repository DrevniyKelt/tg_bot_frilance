from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class StackTagPublic(BaseModel):
    id: int
    slug: str
    name: str
    categories: list[str]


class StackCategoryPublic(BaseModel):
    id: int
    slug: str
    name: str
    tags: list[StackTagPublic]


class PublicUserProfile(BaseModel):
    id: int
    display_name: str
    role: str
    headline: str
    bio: str
    locale: str
    wallet_balance: Decimal
    avg_executor_rating: Decimal
    avg_client_rating: Decimal
    completed_deals: int
    total_matches: int
    active_tariff: str | None
    stack: list[StackTagPublic]


class UpdateProfileRequest(BaseModel):
    display_name: str = Field(min_length=2, max_length=120)
    headline: str = Field(default="", max_length=160)
    bio: str = Field(default="", max_length=2000)
    primary_role: Literal["client", "executor", "both"]


class UpdateUserStacksRequest(BaseModel):
    stack_slugs: list[str] = Field(default_factory=list, max_length=30)
