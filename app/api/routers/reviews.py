from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_db_session
from app.schemas.review import CreateReviewRequest, ReviewResponse
from app.services.orders import get_order_by_slug
from app.services.reviews import create_review, list_order_reviews, serialize_review


router = APIRouter()


@router.get("/orders/{order_slug}/reviews", response_model=list[ReviewResponse])
async def api_list_reviews(
    order_slug: str,
    session: AsyncSession = Depends(get_db_session),
) -> list[ReviewResponse]:
    order = await get_order_by_slug(session, order_slug)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
    reviews = await list_order_reviews(session, order_id=order.id)
    return [serialize_review(review) for review in reviews]


@router.post("/orders/{order_slug}/reviews", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def api_create_review(
    order_slug: str,
    payload: CreateReviewRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ReviewResponse:
    order = await get_order_by_slug(session, order_slug)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
    review = await create_review(session, order=order, reviewer=current_user, payload=payload)
    return serialize_review(review)
