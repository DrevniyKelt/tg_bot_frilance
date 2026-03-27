from __future__ import annotations

from pydantic import BaseModel, Field


class ModerationTicketResponse(BaseModel):
    id: int
    reporter_id: int
    target_type: str
    target_user_id: int | None
    order_id: int | None
    reason: str
    status: str
    created_at: str


class CreateModerationTicketRequest(BaseModel):
    target_type: str = Field(pattern="^(order|user)$")
    target_user_id: int | None = None
    reason: str = Field(min_length=5, max_length=2000)
