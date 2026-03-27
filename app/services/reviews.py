from __future__ import annotations

from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Application, ApplicationStatus, Order, OrderStatus, Review, ReviewRole, User
from app.schemas.review import CreateReviewRequest, ReviewResponse


async def list_order_reviews(session: AsyncSession, *, order_id: int) -> list[Review]:
    return (
        await session.scalars(
            select(Review)
            .options(
                selectinload(Review.reviewer),
                selectinload(Review.reviewee),
            )
            .where(Review.order_id == order_id)
            .order_by(Review.created_at.desc())
        )
    ).all()


async def create_review(
    session: AsyncSession,
    *,
    order: Order,
    reviewer: User,
    payload: CreateReviewRequest,
) -> Review:
    if order.status != OrderStatus.COMPLETED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Reviews are available only for completed orders.")

    if payload.reviewee_id == reviewer.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You cannot review yourself.")

    participants = await _selected_participants(session, order_id=order.id)
    selected_executor_ids = {item.executor_id for item in participants}

    if reviewer.id == order.client_id:
        if payload.reviewee_id not in selected_executor_ids:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Client can review only selected executors.")
        role = ReviewRole.CLIENT_TO_EXECUTOR
    elif reviewer.id in selected_executor_ids:
        if payload.reviewee_id != order.client_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Executor can review only the order client.")
        role = ReviewRole.EXECUTOR_TO_CLIENT
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only order participants can leave reviews.")

    existing = await session.scalar(
        select(Review).where(
            Review.order_id == order.id,
            Review.reviewer_id == reviewer.id,
            Review.reviewee_id == payload.reviewee_id,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Review already exists for this participant.")

    reviewee = await session.scalar(
        select(User)
        .options(selectinload(User.profile))
        .where(User.id == payload.reviewee_id)
    )
    if reviewee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review target not found.")

    review = Review(
        order_id=order.id,
        reviewer_id=reviewer.id,
        reviewee_id=payload.reviewee_id,
        role=role,
        score=payload.score,
        text=payload.text.strip(),
    )
    session.add(review)
    await session.flush()
    await _recalculate_user_ratings(session, reviewee)
    await session.commit()
    await session.refresh(review)
    return await get_review_by_id(session, review.id)


async def get_review_by_id(session: AsyncSession, review_id: int) -> Review | None:
    return await session.scalar(
        select(Review)
        .options(selectinload(Review.reviewer), selectinload(Review.reviewee))
        .where(Review.id == review_id)
    )


def serialize_review(review: Review) -> ReviewResponse:
    return ReviewResponse(
        id=review.id,
        order_id=review.order_id,
        reviewer_id=review.reviewer_id,
        reviewer_name=review.reviewer.display_name,
        reviewee_id=review.reviewee_id,
        reviewee_name=review.reviewee.display_name,
        role=review.role.value,
        score=review.score,
        text=review.text,
        created_at=review.created_at.isoformat(),
    )


async def _selected_participants(session: AsyncSession, *, order_id: int) -> list[Application]:
    return (
        await session.scalars(
            select(Application).where(
                Application.order_id == order_id,
                Application.status == ApplicationStatus.SELECTED,
            )
        )
    ).all()


async def _recalculate_user_ratings(session: AsyncSession, user: User) -> None:
    received = (
        await session.scalars(
            select(Review).where(Review.reviewee_id == user.id)
        )
    ).all()
    client_scores = [Decimal(review.score) for review in received if review.role == ReviewRole.EXECUTOR_TO_CLIENT]
    executor_scores = [Decimal(review.score) for review in received if review.role == ReviewRole.CLIENT_TO_EXECUTOR]

    if executor_scores:
        user.profile.avg_executor_rating = (sum(executor_scores) / Decimal(len(executor_scores))).quantize(Decimal("0.01"))
    if client_scores:
        user.profile.avg_client_rating = (sum(client_scores) / Decimal(len(client_scores))).quantize(Decimal("0.01"))
