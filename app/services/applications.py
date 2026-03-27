from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.db.models import (
    Application,
    ApplicationStatus,
    Order,
    OrderStatus,
    Subscription,
    User,
)
from app.schemas.application import (
    ApplicationCardResponse,
    CreateApplicationRequest,
    QuickApplicationRequest,
)
from app.bot.notifications import notify_executor_selected, notify_new_application
from app.services.chats import ensure_chat_for_order_pair
from app.services.orders import has_active_subscription


async def create_application(
    session: AsyncSession,
    *,
    order: Order,
    executor: User,
    payload: CreateApplicationRequest,
    is_quick: bool = False,
) -> Application:
    settings = get_settings()
    _validate_executor_can_apply(order, executor)

    existing_total = await session.scalar(
        select(func.count(Application.id)).where(Application.executor_id == executor.id)
    )
    if (
        executor.completed_deals == 0
        and existing_total >= settings.features.new_user_max_applications
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="New executor application boost limit reached.",
        )
    if (
        executor.unmatched_applications_last_week
        >= settings.features.new_user_max_unmatched_applications_per_week
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Weekly unmatched application limit reached.",
        )
    if (
        executor.total_matches >= settings.features.new_user_max_matches
        and executor.completed_deals == 0
        and not has_active_subscription(executor)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="New executor match limit reached.",
        )

    application = Application(
        order_id=order.id,
        executor_id=executor.id,
        cover_letter=payload.cover_letter.strip(),
        proposed_amount=payload.proposed_amount,
        delivery_days=payload.delivery_days,
        attachment_name=payload.attachment_name,
        is_quick=is_quick,
    )
    session.add(application)
    executor.unmatched_applications_last_week += 1
    await session.commit()
    await session.refresh(application)
    hydrated = await get_application_by_id(session, application.id)
    if hydrated is not None:
        await notify_new_application(order=hydrated.order, executor=hydrated.executor)
    return hydrated


async def quick_apply(
    session: AsyncSession,
    *,
    order: Order,
    executor: User,
    payload: QuickApplicationRequest,
) -> Application:
    summary_parts = [executor.profile.headline.strip(), executor.profile.bio.strip()]
    cover_letter = "\n\n".join(part for part in summary_parts if part)
    return await create_application(
        session,
        order=order,
        executor=executor,
        payload=CreateApplicationRequest(
            cover_letter=cover_letter[:2000],
            attachment_name=payload.attachment_name,
        ),
        is_quick=True,
    )


async def list_order_applications(
    session: AsyncSession,
    *,
    order_id: int,
) -> list[Application]:
    return (
        await session.scalars(
            select(Application)
            .options(
                selectinload(Application.executor).selectinload(User.profile),
                selectinload(Application.executor)
                .selectinload(User.subscriptions)
                .selectinload(Subscription.tariff),
            )
            .where(Application.order_id == order_id)
            .order_by(Application.created_at.desc())
        )
    ).all()


async def get_application_by_id(session: AsyncSession, application_id: int) -> Application | None:
    return await session.scalar(
        select(Application)
        .options(
            selectinload(Application.executor).selectinload(User.profile),
            selectinload(Application.executor)
            .selectinload(User.subscriptions)
            .selectinload(Subscription.tariff),
            selectinload(Application.order).selectinload(Order.client),
        )
        .where(Application.id == application_id)
    )


async def cancel_application(
    session: AsyncSession,
    *,
    application: Application,
    actor: User,
) -> Application:
    if application.executor_id != actor.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the executor can cancel this application.")
    if application.status != ApplicationStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only pending applications can be cancelled.")
    application.status = ApplicationStatus.CANCELLED
    application.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(application)
    return application


async def select_executors(
    session: AsyncSession,
    *,
    order: Order,
    client: User,
    application_ids: list[int],
) -> list[Application]:
    if order.client_id != client.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the order owner can select executors.")
    if order.status not in {OrderStatus.PUBLISHED, OrderStatus.IN_REVIEW}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Executors can only be selected for open orders.")

    applications = await list_order_applications(session, order_id=order.id)
    application_index = {application.id: application for application in applications}
    selected: list[Application] = []

    for application_id in application_ids:
        application = application_index.get(application_id)
        if application is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Application {application_id} not found.")
        if application.status != ApplicationStatus.PENDING:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only pending applications can be selected.")
        selected.append(application)

    order.status = OrderStatus.MATCHED
    client.total_matches += len(selected)

    for application in applications:
        if application.id in application_ids:
            application.status = ApplicationStatus.SELECTED
            application.executor.total_matches += 1
            if application.executor.unmatched_applications_last_week > 0:
                application.executor.unmatched_applications_last_week -= 1
            await ensure_chat_for_order_pair(
                session,
                order=order,
                client=client,
                executor=application.executor,
            )
        elif application.status == ApplicationStatus.PENDING:
            application.status = ApplicationStatus.ARCHIVED

    await session.commit()
    for application in selected:
        await notify_executor_selected(order=order, executor=application.executor)
    return [application_index[application_id] for application_id in application_ids]


def serialize_application(application: Application) -> ApplicationCardResponse:
    return ApplicationCardResponse(
        id=application.id,
        order_id=application.order_id,
        executor_id=application.executor_id,
        executor_name=application.executor.display_name,
        executor_headline=application.executor.profile.headline,
        executor_rating=application.executor.profile.avg_executor_rating,
        status=application.status.value,
        cover_letter=application.cover_letter,
        proposed_amount=application.proposed_amount,
        delivery_days=application.delivery_days,
        attachment_name=application.attachment_name,
        is_quick=application.is_quick,
        created_at=application.created_at.date().isoformat(),
    )


def _validate_executor_can_apply(order: Order, executor: User) -> None:
    settings = get_settings()
    if order.client_id == executor.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You cannot apply to your own order.")
    if order.status not in {OrderStatus.PUBLISHED, OrderStatus.IN_REVIEW}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Applications are closed for this order.")
    if executor.is_banned:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Banned users cannot apply.")
    if settings.features.require_tariff_after_first_completed and executor.completed_deals >= 1 and not has_active_subscription(executor):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tariff is required after the first completed deal.",
        )
