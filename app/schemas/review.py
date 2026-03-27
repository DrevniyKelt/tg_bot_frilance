from __future__ import annotations

from pydantic import BaseModel, Field


class ReviewResponse(BaseModel):
    id: int
    order_id: int
    reviewer_id: int
    reviewer_name: str
    reviewee_id: int
    reviewee_name: str
    role: str
    score: int
    text: str
    created_at: str


class CreateReviewRequest(BaseModel):
    reviewee_id: int
    score: int = Field(ge=1, le=5)
    text: str = Field(min_length=3, max_length=2000)
