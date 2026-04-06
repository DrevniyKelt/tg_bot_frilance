from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.i18n import detect_locale, translator
from app.core.utils import csv_to_list, format_money
from app.db.models import AdCampaign, ModerationTicket, Order, User
from app.db.models import RoleMode
from app.db.session import get_db_session
from app.schemas.ads import AdEventRequest
from app.schemas.application import CreateApplicationRequest
from app.schemas.chat import CreateChatMessageRequest
from app.schemas.moderation import CreateModerationTicketRequest
from app.schemas.order import CreateOrderRequest
from app.schemas.profile import UpdateProfileRequest
from app.schemas.review import CreateReviewRequest
from app.services.ads import get_active_ad_for_placement, list_ad_campaigns, record_ad_click, record_ad_impression, serialize_ad_campaign
from app.services.applications import create_application, list_order_applications, select_executors, serialize_application
from app.services.chats import assert_chat_member, create_message, get_chat_by_id, list_user_chats, serialize_chat, serialize_message
from app.services.catalog import get_stack_catalog, list_addon_packs, list_tariffs
from app.services.deals import confirm_order_completion, start_order_work
from app.services.forums import create_forum_post, create_forum_topic, get_forum_topic_by_id, list_forum_topics, serialize_forum_post, serialize_forum_topic
from app.services.moderation import ban_user, create_moderation_ticket, ensure_admin, hide_order, list_moderation_tickets, resolve_ticket, serialize_ticket
from app.services.orders import (
    create_order,
    get_order_by_slug,
    list_client_orders,
    list_executor_orders,
    list_orders,
    order_budget_preview,
    serialize_order,
)
from app.services.profiles import get_public_user, resolve_current_user, serialize_user, update_profile, update_user_stacks
from app.services.reviews import create_review, list_order_reviews, serialize_review
from app.services.swipe import build_swipe_cards, list_swipe_source_orders, record_swipe_decision
from app.services.wallet import (
    fund_order_escrow,
    list_wallet_transactions,
    refund_order_escrow,
    release_order_escrow,
    serialize_wallet_transaction,
    topup_wallet,
    withdraw_wallet,
)


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _build_context(
    request: Request,
    *,
    title: str,
    active_route: str,
    user: User | None,
    **extra,
) -> dict:
    settings = get_settings()
    locale = detect_locale(request, settings)
    is_admin = bool(user and user.id == settings.demo.default_user_id)
    test_mode_enabled = request.session.get("test_mode_enabled", settings.telegram.allow_dev_login)
    return {
        "request": request,
        "title": title,
        "lang": locale,
        "t": translator(locale),
        "settings": settings,
        "user": serialize_user(user, locale) if user else None,
        "active_route": active_route,
        "demo_mode": test_mode_enabled,
        "is_admin": is_admin,
        "format_money": format_money,
        **extra,
    }


def _template_response(request: Request, template: str, context: dict) -> Response:
    response = templates.TemplateResponse(request, template, context)
    requested_locale = request.query_params.get("lang")
    if requested_locale:
        response.set_cookie("locale", requested_locale, max_age=60 * 60 * 24 * 365)
    return response


def _exception_message(exc: Exception) -> str:
    detail = getattr(exc, "detail", None)
    if detail:
        return str(detail)
    return str(exc)


def _auth_redirect() -> RedirectResponse:
    return RedirectResponse(url="/swipe", status_code=303)


@router.get("/")
async def home() -> RedirectResponse:
    return RedirectResponse(url="/swipe", status_code=303)


@router.get("/catalog")
async def catalog(
    request: Request,
    q: str | None = None,
    stack: str | None = None,
    min_budget: Decimal | None = None,
    max_budget: Decimal | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    user = await resolve_current_user(session, request)
    locale = detect_locale(request, get_settings())
    orders = await list_orders(
        session,
        locale=locale,
        q=q,
        stack=stack,
        min_budget=min_budget,
        max_budget=max_budget,
        status_filter=status_filter,
    )
    stack_catalog = await get_stack_catalog(session, locale)
    catalog_ad = await get_active_ad_for_placement(session, "catalog_inline")
    if catalog_ad:
        catalog_ad = await record_ad_impression(session, catalog_ad.code)
    context = _build_context(
        request,
        title="Catalog",
        active_route="orders",
        user=user,
        orders=orders,
        stack_catalog=stack_catalog,
        catalog_ad=serialize_ad_campaign(catalog_ad) if catalog_ad else None,
        filters={
            "q": q or "",
            "stack": stack or "",
            "min_budget": min_budget or "",
            "max_budget": max_budget or "",
            "status": status_filter or "",
        },
    )
    return _template_response(request, "pages/catalog.html", context)


@router.get("/orders/new")
async def new_order(request: Request, session: AsyncSession = Depends(get_db_session)) -> Response:
    user = await resolve_current_user(session, request)
    if user is None:
        return _auth_redirect()
    locale = detect_locale(request, get_settings())
    stack_catalog = await get_stack_catalog(session, locale)
    preview = order_budget_preview(user, Decimal("20000")) if user else None
    context = _build_context(
        request,
        title="Create order",
        active_route="new_order",
        user=user,
        stack_catalog=stack_catalog,
        preview=preview,
        form_data={},
        error=None,
    )
    return _template_response(request, "pages/order_form.html", context)


@router.post("/orders/new")
async def create_order_from_form(
    request: Request,
    title: str = Form(...),
    category: str = Form(...),
    summary: str = Form(...),
    description: str = Form(...),
    budget_type: str = Form(...),
    currency: str = Form(...),
    budget_amount: Decimal = Form(...),
    stack_mode: str = Form(...),
    stack_slugs: str = Form(default=""),
    min_rating: str = Form(default=""),
    delivery_days: str = Form(default=""),
    priority: str = Form(default="balanced"),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    user = await resolve_current_user(session, request)
    if user is None:
        return _auth_redirect()
    locale = detect_locale(request, get_settings())
    stack_catalog = await get_stack_catalog(session, locale)

    payload = CreateOrderRequest(
        title=title,
        category=category,
        summary=summary,
        description=description,
        budget_type=budget_type,
        currency=currency,
        stack_mode=stack_mode,
        budget_amount=budget_amount,
        stack_slugs=csv_to_list(stack_slugs),
        auto_filters={
            "min_rating": float(min_rating) if min_rating else None,
            "delivery_days": int(delivery_days) if delivery_days else None,
            "priority": priority,
        },
    )
    try:
        order = await create_order(session, user, payload)
    except Exception as exc:  # noqa: BLE001
        context = _build_context(
            request,
            title="Create order",
            active_route="new_order",
            user=user,
            stack_catalog=stack_catalog,
            preview=order_budget_preview(user, budget_amount),
            form_data={
                "title": title,
                "category": category,
                "summary": summary,
                "description": description,
                "budget_type": budget_type,
                "currency": currency,
                "budget_amount": budget_amount,
                "stack_mode": stack_mode,
                "stack_slugs": stack_slugs,
                "min_rating": min_rating,
                "delivery_days": delivery_days,
                "priority": priority,
            },
            error=_exception_message(exc),
        )
        return _template_response(request, "pages/order_form.html", context)

    return RedirectResponse(url=f"/orders/{order.slug}", status_code=303)


@router.get("/orders/{order_slug}")
async def order_detail(
    order_slug: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    user = await resolve_current_user(session, request)
    locale = detect_locale(request, get_settings())
    order = await get_order_by_slug(session, order_slug)
    if order is None:
        return RedirectResponse(url="/catalog", status_code=303)
    applications = await list_order_applications(session, order_id=order.id)
    reviews = await list_order_reviews(session, order_id=order.id)
    serialized_user = serialize_user(user, locale) if user else None
    related_chats = []
    if user:
        user_chats = await list_user_chats(session, user=user)
        related_chats = [serialize_chat(chat) for chat in user_chats if chat.order_id == order.id]
    context = _build_context(
        request,
        title=order.title,
        active_route="orders",
        user=user,
        order=serialize_order(order, locale=locale),
        applications=[serialize_application(application) for application in applications],
        reviews=[serialize_review(review) for review in reviews],
        can_apply=bool(user and user.id != order.client_id),
        is_order_owner=bool(user and user.id == order.client_id),
        application_error=None,
        review_error=None,
        report_error=None,
        selected_application_ids=[
            application.id for application in applications if application.status.value == "selected"
        ],
        serialized_user=serialized_user,
        related_chats=related_chats,
    )
    return _template_response(request, "pages/order_detail.html", context)


@router.post("/orders/{order_slug}/apply")
async def apply_to_order_from_form(
    order_slug: str,
    request: Request,
    cover_letter: str = Form(default=""),
    proposed_amount: str = Form(default=""),
    delivery_days: str = Form(default=""),
    attachment_name: str = Form(default=""),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    user = await resolve_current_user(session, request)
    if user is None:
        return _auth_redirect()
    order = await get_order_by_slug(session, order_slug)
    if order is None:
        return RedirectResponse(url="/catalog", status_code=303)

    try:
        await create_application(
            session,
            order=order,
            executor=user,
            payload=CreateApplicationRequest(
                cover_letter=cover_letter,
                proposed_amount=Decimal(proposed_amount) if proposed_amount else None,
                delivery_days=int(delivery_days) if delivery_days else None,
                attachment_name=attachment_name or None,
            ),
        )
        return RedirectResponse(url=f"/orders/{order_slug}", status_code=303)
    except Exception as exc:  # noqa: BLE001
        locale = detect_locale(request, get_settings())
        applications = await list_order_applications(session, order_id=order.id)
        reviews = await list_order_reviews(session, order_id=order.id)
        context = _build_context(
            request,
            title=order.title,
            active_route="orders",
            user=user,
            order=serialize_order(order, locale=locale),
            applications=[serialize_application(application) for application in applications],
            reviews=[serialize_review(review) for review in reviews],
            can_apply=user.id != order.client_id,
            is_order_owner=user.id == order.client_id,
            application_error=_exception_message(exc),
            review_error=None,
            report_error=None,
            selected_application_ids=[
                application.id for application in applications if application.status.value == "selected"
            ],
            serialized_user=serialize_user(user, locale),
            related_chats=[serialize_chat(chat) for chat in await list_user_chats(session, user=user) if chat.order_id == order.id],
        )
        return _template_response(request, "pages/order_detail.html", context)


@router.post("/orders/{order_slug}/reviews")
async def create_review_from_form(
    order_slug: str,
    request: Request,
    reviewee_id: int = Form(...),
    score: int = Form(...),
    text: str = Form(...),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    user = await resolve_current_user(session, request)
    if user is None:
        return _auth_redirect()
    order = await get_order_by_slug(session, order_slug)
    if order is None:
        return RedirectResponse(url="/catalog", status_code=303)
    try:
        await create_review(
            session,
            order=order,
            reviewer=user,
            payload=CreateReviewRequest(reviewee_id=reviewee_id, score=score, text=text),
        )
        return RedirectResponse(url=f"/orders/{order_slug}", status_code=303)
    except Exception as exc:  # noqa: BLE001
        locale = detect_locale(request, get_settings())
        applications = await list_order_applications(session, order_id=order.id)
        reviews = await list_order_reviews(session, order_id=order.id)
        context = _build_context(
            request,
            title=order.title,
            active_route="orders",
            user=user,
            order=serialize_order(order, locale=locale),
            applications=[serialize_application(application) for application in applications],
            reviews=[serialize_review(review) for review in reviews],
            can_apply=user.id != order.client_id,
            is_order_owner=user.id == order.client_id,
            application_error=None,
            review_error=_exception_message(exc),
            report_error=None,
            selected_application_ids=[
                application.id for application in applications if application.status.value == "selected"
            ],
            serialized_user=serialize_user(user, locale),
            related_chats=[serialize_chat(chat) for chat in await list_user_chats(session, user=user) if chat.order_id == order.id],
        )
        return _template_response(request, "pages/order_detail.html", context)


@router.post("/orders/{order_slug}/report")
async def create_order_report_from_form(
    order_slug: str,
    request: Request,
    reason: str = Form(...),
    target_user_id: str = Form(default=""),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    user = await resolve_current_user(session, request)
    if user is None:
        return _auth_redirect()
    order = await get_order_by_slug(session, order_slug)
    if order is None:
        return RedirectResponse(url="/catalog", status_code=303)
    try:
        await create_moderation_ticket(
            session,
            reporter=user,
            order=order,
            payload=CreateModerationTicketRequest(
                target_type="order" if not target_user_id else "user",
                target_user_id=int(target_user_id) if target_user_id else None,
                reason=reason,
            ),
        )
        return RedirectResponse(url=f"/orders/{order_slug}", status_code=303)
    except Exception as exc:  # noqa: BLE001
        locale = detect_locale(request, get_settings())
        applications = await list_order_applications(session, order_id=order.id)
        reviews = await list_order_reviews(session, order_id=order.id)
        context = _build_context(
            request,
            title=order.title,
            active_route="orders",
            user=user,
            order=serialize_order(order, locale=locale),
            applications=[serialize_application(application) for application in applications],
            reviews=[serialize_review(review) for review in reviews],
            can_apply=user.id != order.client_id,
            is_order_owner=user.id == order.client_id,
            application_error=None,
            review_error=None,
            report_error=_exception_message(exc),
            selected_application_ids=[
                application.id for application in applications if application.status.value == "selected"
            ],
            serialized_user=serialize_user(user, locale),
            related_chats=[serialize_chat(chat) for chat in await list_user_chats(session, user=user) if chat.order_id == order.id],
        )
        return _template_response(request, "pages/order_detail.html", context)


@router.post("/orders/{order_slug}/select")
async def select_order_executors_from_form(
    order_slug: str,
    request: Request,
    application_ids: list[int] = Form(...),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    user = await resolve_current_user(session, request)
    if user is None:
        return _auth_redirect()
    order = await get_order_by_slug(session, order_slug)
    if order is None:
        return RedirectResponse(url="/catalog", status_code=303)
    await select_executors(session, order=order, client=user, application_ids=application_ids)
    return RedirectResponse(url=f"/orders/{order_slug}", status_code=303)


@router.post("/orders/{order_slug}/escrow/fund")
async def fund_escrow_from_form(
    order_slug: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    user = await resolve_current_user(session, request)
    if user is None:
        return _auth_redirect()
    order = await get_order_by_slug(session, order_slug)
    if order is None:
        return RedirectResponse(url="/catalog", status_code=303)
    await fund_order_escrow(session, order=order, client=user)
    return RedirectResponse(url=f"/orders/{order_slug}", status_code=303)


@router.post("/orders/{order_slug}/escrow/refund")
async def refund_escrow_from_form(
    order_slug: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    user = await resolve_current_user(session, request)
    if user is None:
        return _auth_redirect()
    order = await get_order_by_slug(session, order_slug)
    if order is None:
        return RedirectResponse(url="/catalog", status_code=303)
    await refund_order_escrow(session, order=order, client=user)
    return RedirectResponse(url=f"/orders/{order_slug}", status_code=303)


@router.post("/orders/{order_slug}/escrow/release")
async def release_escrow_from_form(
    order_slug: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    user = await resolve_current_user(session, request)
    if user is None:
        return _auth_redirect()
    order = await get_order_by_slug(session, order_slug)
    if order is None:
        return RedirectResponse(url="/catalog", status_code=303)
    await release_order_escrow(session, order=order, client=user)
    return RedirectResponse(url=f"/orders/{order_slug}", status_code=303)


@router.post("/orders/{order_slug}/start")
async def start_order_from_form(
    order_slug: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    user = await resolve_current_user(session, request)
    if user is None:
        return _auth_redirect()
    order = await get_order_by_slug(session, order_slug)
    if order is None:
        return RedirectResponse(url="/catalog", status_code=303)
    await start_order_work(session, order=order, actor=user)
    return RedirectResponse(url=f"/orders/{order_slug}", status_code=303)


@router.post("/orders/{order_slug}/confirm")
async def confirm_order_from_form(
    order_slug: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    user = await resolve_current_user(session, request)
    if user is None:
        return _auth_redirect()
    order = await get_order_by_slug(session, order_slug)
    if order is None:
        return RedirectResponse(url="/catalog", status_code=303)
    await confirm_order_completion(session, order=order, actor=user)
    return RedirectResponse(url=f"/orders/{order_slug}", status_code=303)


@router.get("/profile")
async def profile_page(request: Request, session: AsyncSession = Depends(get_db_session)) -> Response:
    user = await resolve_current_user(session, request)
    if user is None:
        return _auth_redirect()
    locale = detect_locale(request, get_settings())
    stack_catalog = await get_stack_catalog(session, locale)
    tariffs = await list_tariffs(session)
    wallet_transactions = await list_wallet_transactions(session, user=user)
    context = _build_context(
        request,
        title="Profile",
        active_route="profile",
        user=user,
        stack_catalog=stack_catalog,
        tariffs=tariffs,
        wallet_transactions=[serialize_wallet_transaction(tx) for tx in wallet_transactions[:10]],
        error=None,
        success=False,
        wallet_error=None,
    )
    return _template_response(request, "pages/profile.html", context)


@router.get("/me/orders")
async def my_orders_page(
    request: Request,
    mode: str = Query(default="client", pattern="^(client|executor)$"),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    user = await resolve_current_user(session, request)
    if user is None:
        return _auth_redirect()
    locale = detect_locale(request, get_settings())
    client_orders = await list_client_orders(session, user=user, locale=locale)
    executor_orders = await list_executor_orders(session, user=user, locale=locale)
    context = _build_context(
        request,
        title="My orders",
        active_route="profile",
        user=user,
        mode=mode,
        client_orders=client_orders,
        executor_orders=executor_orders,
    )
    return _template_response(request, "pages/my_orders.html", context)


@router.post("/profile")
async def profile_update(
    request: Request,
    display_name: str = Form(...),
    headline: str = Form(default=""),
    bio: str = Form(default=""),
    primary_role: str = Form(...),
    stack_slugs: str = Form(default=""),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    user = await resolve_current_user(session, request)
    if user is None:
        return _auth_redirect()
    locale = detect_locale(request, get_settings())
    stack_catalog = await get_stack_catalog(session, locale)
    try:
        user = await update_profile(
            session,
            user,
            UpdateProfileRequest(
                display_name=display_name,
                headline=headline,
                bio=bio,
                primary_role=primary_role,
            ),
        )
        user = await update_user_stacks(session, user, csv_to_list(stack_slugs))
    except Exception as exc:  # noqa: BLE001
        context = _build_context(
            request,
            title="Profile",
            active_route="profile",
            user=user,
            stack_catalog=stack_catalog,
            tariffs=await list_tariffs(session),
            wallet_transactions=[
                serialize_wallet_transaction(tx)
                for tx in (await list_wallet_transactions(session, user=user))[:10]
            ],
            error=_exception_message(exc),
            success=False,
            wallet_error=None,
        )
        return _template_response(request, "pages/profile.html", context)

    context = _build_context(
        request,
        title="Profile",
        active_route="profile",
        user=user,
        stack_catalog=stack_catalog,
        tariffs=await list_tariffs(session),
        wallet_transactions=[
            serialize_wallet_transaction(tx)
            for tx in (await list_wallet_transactions(session, user=user))[:10]
        ],
        error=None,
        success=True,
        wallet_error=None,
    )
    return _template_response(request, "pages/profile.html", context)


@router.post("/wallet/topup")
async def wallet_topup_from_form(
    request: Request,
    amount: Decimal = Form(...),
    currency: str = Form(default="RUB"),
    note: str = Form(default="Mock top-up"),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    user = await resolve_current_user(session, request)
    if user is None:
        return _auth_redirect()
    await topup_wallet(session, user=user, amount=amount, currency=currency, note=note)
    return RedirectResponse(url="/profile", status_code=303)


@router.post("/wallet/withdraw")
async def wallet_withdraw_from_form(
    request: Request,
    amount: Decimal = Form(...),
    currency: str = Form(default="RUB"),
    note: str = Form(default="Mock withdraw"),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    user = await resolve_current_user(session, request)
    if user is None:
        return _auth_redirect()
    try:
        await withdraw_wallet(session, user=user, amount=amount, currency=currency, note=note)
        return RedirectResponse(url="/profile", status_code=303)
    except Exception as exc:  # noqa: BLE001
        locale = detect_locale(request, get_settings())
        stack_catalog = await get_stack_catalog(session, locale)
        wallet_transactions = await list_wallet_transactions(session, user=user)
        context = _build_context(
            request,
            title="Profile",
            active_route="profile",
            user=user,
            stack_catalog=stack_catalog,
            tariffs=await list_tariffs(session),
            wallet_transactions=[serialize_wallet_transaction(tx) for tx in wallet_transactions[:10]],
            error=None,
            success=False,
            wallet_error=_exception_message(exc),
        )
        return _template_response(request, "pages/profile.html", context)


@router.get("/swipe")
async def swipe_page(
    request: Request,
    target: str | None = Query(default=None, pattern="^(orders|executors)$"),
    stack: str | None = None,
    source_order_id: int | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    user = await resolve_current_user(session, request)
    locale = detect_locale(request, get_settings())
    guest_required = user is None
    if target is None:
        target = "executors" if user and user.primary_role in {RoleMode.CLIENT, RoleMode.BOTH} else "orders"
    cards = []
    stack_catalog = await get_stack_catalog(session, locale)
    source_orders = []
    selected_source_order = None
    if user is not None:
        cards = await build_swipe_cards(
            session,
            user,
            target=target,
            stack=stack,
            locale=locale,
            source_order_id=source_order_id,
        )
        source_orders = await list_swipe_source_orders(session, user=user)
        selected_source_order = next((item for item in source_orders if item.id == source_order_id), None)
        if selected_source_order is None and source_orders:
            selected_source_order = source_orders[0]
    context = _build_context(
        request,
        title="Swipe",
        active_route="swipe",
        user=user,
        cards=cards,
        stack_catalog=stack_catalog,
        target=target,
        stack_filter=stack or "",
        source_orders=source_orders,
        selected_source_order=selected_source_order,
        guest_required=guest_required,
    )
    return _template_response(request, "pages/swipe.html", context)


@router.post("/swipe/decision/{target}/{target_id}")
async def swipe_decision(
    target: str,
    target_id: int,
    request: Request,
    direction: str = Form(...),
    source_order_id: int | None = Form(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> JSONResponse:
    user = await resolve_current_user(session, request)
    if user is None:
        return JSONResponse({"detail": "Authentication required."}, status_code=401)
    if target not in {"orders", "executors"}:
        return JSONResponse({"detail": "Unsupported target."}, status_code=422)
    locale = detect_locale(request, get_settings())
    payload = await record_swipe_decision(
        session,
        actor=user,
        target=target,
        direction=direction,
        target_id=target_id,
        source_order_id=source_order_id,
        locale=locale,
    )
    return JSONResponse(payload)


@router.get("/tariffs")
async def tariffs_page(request: Request, session: AsyncSession = Depends(get_db_session)) -> Response:
    user = await resolve_current_user(session, request)
    tariffs = await list_tariffs(session)
    addons = await list_addon_packs(session)
    context = _build_context(
        request,
        title="Tariffs",
        active_route="tariffs",
        user=user,
        tariffs=tariffs,
        addons=addons,
    )
    return _template_response(request, "pages/tariffs.html", context)


@router.get("/ads/click/{campaign_code}")
async def ad_click_redirect(
    campaign_code: str,
    session: AsyncSession = Depends(get_db_session),
) -> RedirectResponse:
    campaign = await record_ad_click(session, campaign_code)
    return RedirectResponse(url=campaign.target_url, status_code=303)


@router.get("/admin")
async def admin_page(request: Request, session: AsyncSession = Depends(get_db_session)) -> Response:
    user = await resolve_current_user(session, request)
    if user is None:
        return _auth_redirect()
    ensure_admin(user)
    tickets = await list_moderation_tickets(session)
    campaigns = await list_ad_campaigns(session)
    orders = (await session.scalars(select(Order).order_by(Order.created_at.desc()))).all()
    users = (await session.scalars(select(User).order_by(User.id.asc()))).all()
    context = _build_context(
        request,
        title="Admin",
        active_route="profile",
        user=user,
        tickets=[serialize_ticket(ticket) for ticket in tickets],
        campaigns=[serialize_ad_campaign(campaign) for campaign in campaigns],
        admin_orders=[serialize_order(order, locale=detect_locale(request, get_settings())) for order in orders],
        admin_users=[serialize_user(item, detect_locale(request, get_settings())) for item in users],
    )
    return _template_response(request, "pages/admin.html", context)


@router.post("/admin/tickets/{ticket_id}/resolve")
async def resolve_ticket_from_form(
    ticket_id: int,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    user = await resolve_current_user(session, request)
    if user is None:
        return _auth_redirect()
    ensure_admin(user)
    await resolve_ticket(session, ticket_id=ticket_id)
    return RedirectResponse(url="/admin", status_code=303)


@router.post("/admin/orders/{order_slug}/hide")
async def hide_order_from_form(
    order_slug: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    user = await resolve_current_user(session, request)
    if user is None:
        return _auth_redirect()
    ensure_admin(user)
    order = await get_order_by_slug(session, order_slug)
    if order is None:
        return RedirectResponse(url="/admin", status_code=303)
    await hide_order(session, order=order)
    return RedirectResponse(url="/admin", status_code=303)


@router.post("/admin/users/{user_id}/ban")
async def ban_user_from_form(
    user_id: int,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    user = await resolve_current_user(session, request)
    if user is None:
        return _auth_redirect()
    ensure_admin(user)
    target_user = await get_public_user(session, user_id)
    if target_user is None:
        return RedirectResponse(url="/admin", status_code=303)
    await ban_user(session, user=target_user)
    return RedirectResponse(url="/admin", status_code=303)


@router.get("/chats")
async def chats_page() -> RedirectResponse:
    return RedirectResponse(url="/community?view=chats", status_code=303)


@router.get("/community")
async def community_page(
    request: Request,
    view: str = Query(default="chats", pattern="^(chats|forums)$"),
    topic_id: int | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    user = await resolve_current_user(session, request)
    chats = await list_user_chats(session, user=user) if user else []
    forum_topics = await list_forum_topics(session)
    active_topic = None
    if forum_topics:
        active_topic = next((topic for topic in forum_topics if topic.id == topic_id), None) or forum_topics[0]
    context = _build_context(
        request,
        title="Chats and Forums",
        active_route="community",
        user=user,
        guest_required=user is None,
        view=view,
        chats=[serialize_chat(chat) for chat in chats],
        forum_topics=[serialize_forum_topic(topic) for topic in forum_topics],
        active_topic=serialize_forum_topic(active_topic) if active_topic else None,
        active_topic_posts=[serialize_forum_post(post) for post in active_topic.posts] if active_topic else [],
        topic_error=None,
        post_error=None,
    )
    return _template_response(request, "pages/community.html", context)


@router.post("/community/forums/topics")
async def create_forum_topic_from_form(
    request: Request,
    title: str = Form(...),
    body: str = Form(...),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    user = await resolve_current_user(session, request)
    if user is None:
        return _auth_redirect()
    try:
        topic = await create_forum_topic(session, author=user, title=title, body=body)
        return RedirectResponse(url=f"/community?view=forums&topic_id={topic.id}", status_code=303)
    except Exception as exc:  # noqa: BLE001
        chats = await list_user_chats(session, user=user)
        forum_topics = await list_forum_topics(session)
        active_topic = forum_topics[0] if forum_topics else None
        context = _build_context(
            request,
            title="Chats and Forums",
            active_route="community",
            user=user,
            guest_required=False,
            view="forums",
            chats=[serialize_chat(chat) for chat in chats],
            forum_topics=[serialize_forum_topic(topic) for topic in forum_topics],
            active_topic=serialize_forum_topic(active_topic) if active_topic else None,
            active_topic_posts=[serialize_forum_post(post) for post in active_topic.posts] if active_topic else [],
            topic_error=_exception_message(exc),
            post_error=None,
        )
        return _template_response(request, "pages/community.html", context)


@router.post("/community/forums/{topic_id}/posts")
async def create_forum_post_from_form(
    topic_id: int,
    request: Request,
    body: str = Form(...),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    user = await resolve_current_user(session, request)
    if user is None:
        return _auth_redirect()
    topic = await get_forum_topic_by_id(session, topic_id)
    if topic is None:
        return RedirectResponse(url="/community?view=forums", status_code=303)
    try:
        await create_forum_post(session, topic=topic, author=user, body=body)
        return RedirectResponse(url=f"/community?view=forums&topic_id={topic_id}", status_code=303)
    except Exception as exc:  # noqa: BLE001
        chats = await list_user_chats(session, user=user)
        forum_topics = await list_forum_topics(session)
        active_topic = await get_forum_topic_by_id(session, topic_id)
        context = _build_context(
            request,
            title="Chats and Forums",
            active_route="community",
            user=user,
            guest_required=False,
            view="forums",
            chats=[serialize_chat(chat) for chat in chats],
            forum_topics=[serialize_forum_topic(item) for item in forum_topics],
            active_topic=serialize_forum_topic(active_topic) if active_topic else None,
            active_topic_posts=[serialize_forum_post(post) for post in active_topic.posts] if active_topic else [],
            topic_error=None,
            post_error=_exception_message(exc),
        )
        return _template_response(request, "pages/community.html", context)


@router.get("/chats/{chat_id}")
async def chat_thread_page(
    chat_id: int,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    user = await resolve_current_user(session, request)
    if user is None:
        return _auth_redirect()
    chat = await get_chat_by_id(session, chat_id)
    if chat is None:
        return RedirectResponse(url="/chats", status_code=303)
    assert_chat_member(chat, user)
    context = _build_context(
        request,
        title=f"Chat {chat.id}",
        active_route="community",
        user=user,
        chat=serialize_chat(chat),
        messages=[serialize_message(message) for message in sorted(chat.messages, key=lambda item: item.created_at)],
        message_error=None,
    )
    return _template_response(request, "pages/chat_thread.html", context)


@router.post("/chats/{chat_id}")
async def post_chat_message_from_form(
    chat_id: int,
    request: Request,
    body: str = Form(...),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    user = await resolve_current_user(session, request)
    if user is None:
        return _auth_redirect()
    chat = await get_chat_by_id(session, chat_id)
    if chat is None:
        return RedirectResponse(url="/chats", status_code=303)
    try:
        await create_message(
            session,
            chat=chat,
            author=user,
            body=CreateChatMessageRequest(body=body).body,
        )
        return RedirectResponse(url=f"/chats/{chat_id}", status_code=303)
    except Exception as exc:  # noqa: BLE001
        assert_chat_member(chat, user)
        context = _build_context(
            request,
            title=f"Chat {chat.id}",
            active_route="profile",
            user=user,
            chat=serialize_chat(chat),
            messages=[serialize_message(message) for message in sorted(chat.messages, key=lambda item: item.created_at)],
            message_error=_exception_message(exc),
        )
        return _template_response(request, "pages/chat_thread.html", context)


@router.get("/auth/demo/{user_id}")
async def demo_login(user_id: int, request: Request) -> RedirectResponse:
    request.session["test_mode_enabled"] = True
    request.session["user_id"] = user_id
    return RedirectResponse(url="/profile", status_code=303)


@router.get("/test-mode/toggle")
async def toggle_test_mode(request: Request) -> RedirectResponse:
    settings = get_settings()
    current = request.session.get("test_mode_enabled", settings.telegram.allow_dev_login)
    next_value = not current
    request.session["test_mode_enabled"] = next_value
    if next_value:
        request.session["user_id"] = request.session.get("user_id") or settings.demo.default_user_id
    else:
        request.session.pop("user_id", None)
    target = request.headers.get("referer") or "/swipe"
    return RedirectResponse(url=target, status_code=303)


@router.get("/logout")
async def web_logout(request: Request) -> RedirectResponse:
    request.session.clear()
    return RedirectResponse(url="/swipe", status_code=303)


@router.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/robots.txt", response_class=PlainTextResponse)
async def robots() -> str:
    return "User-agent: *\nAllow: /\nSitemap: /sitemap.xml\n"


@router.get("/sitemap.xml")
async def sitemap(session: AsyncSession = Depends(get_db_session)) -> Response:
    settings = get_settings()
    orders = (await session.scalars(select(Order).order_by(Order.created_at.desc()))).all()
    urls = [
        f"{settings.app.base_url}/",
        f"{settings.app.base_url}/catalog",
        f"{settings.app.base_url}/tariffs",
        f"{settings.app.base_url}/swipe",
    ]
    urls.extend(f"{settings.app.base_url}/orders/{order.slug}" for order in orders)
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    today = date.today().isoformat()
    for url in urls:
        lines.extend(
            [
                "  <url>",
                f"    <loc>{url}</loc>",
                f"    <lastmod>{today}</lastmod>",
                "  </url>",
            ]
        )
    lines.append("</urlset>")
    return Response("\n".join(lines), media_type="application/xml")
