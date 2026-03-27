from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_db_session
from app.schemas.application import (
    ApplicationCardResponse,
    CreateApplicationRequest,
    QuickApplicationRequest,
)
from app.services.applications import (
    cancel_application,
    create_application,
    get_application_by_id,
    quick_apply,
    serialize_application,
)
from app.services.orders import get_order_by_slug


router = APIRouter()


@router.post("/orders/{order_slug}/apply", response_model=ApplicationCardResponse, status_code=status.HTTP_201_CREATED)
async def apply_to_order(
    order_slug: str,
    payload: CreateApplicationRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ApplicationCardResponse:
    order = await get_order_by_slug(session, order_slug)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
    application = await create_application(session, order=order, executor=current_user, payload=payload)
    return serialize_application(application)


@router.post(
    "/orders/{order_slug}/quick_apply",
    response_model=ApplicationCardResponse,
    status_code=status.HTTP_201_CREATED,
)
async def quick_apply_to_order(
    order_slug: str,
    payload: QuickApplicationRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ApplicationCardResponse:
    order = await get_order_by_slug(session, order_slug)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
    application = await quick_apply(session, order=order, executor=current_user, payload=payload)
    return serialize_application(application)


@router.delete("/applications/{application_id}", response_model=ApplicationCardResponse)
async def delete_application(
    application_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ApplicationCardResponse:
    application = await get_application_by_id(session, application_id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")
    application = await cancel_application(session, application=application, actor=current_user)
    return serialize_application(application)
