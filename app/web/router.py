from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import PlainTextResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.i18n import detect_locale, translator
from app.core.utils import csv_to_list, format_money
from app.db.models import Order, User
from app.db.session import get_db_session
from app.schemas.order import CreateOrderRequest
from app.schemas.profile import UpdateProfileRequest
from app.services.catalog import get_stack_catalog, list_addon_packs, list_tariffs
from app.services.orders import create_order, get_order_by_slug, list_orders, order_budget_preview, serialize_order
from app.services.profiles import resolve_current_user, serialize_user, update_profile, update_user_stacks
from app.services.swipe import build_swipe_cards


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
    return {
        "request": request,
        "title": title,
        "lang": locale,
        "t": translator(locale),
        "settings": settings,
        "user": serialize_user(user, locale) if user else None,
        "active_route": active_route,
        "demo_mode": settings.telegram.allow_dev_login,
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
    return RedirectResponse(url="/", status_code=303)


@router.get("/")
async def home(request: Request, session: AsyncSession = Depends(get_db_session)) -> Response:
    user = await resolve_current_user(session, request)
    locale = detect_locale(request, get_settings())
    orders = await list_orders(session, locale=locale)
    stack_catalog = await get_stack_catalog(session, locale)
    tariffs = await list_tariffs(session)
    addons = await list_addon_packs(session)
    context = _build_context(
        request,
        title="SkillLane",
        active_route="home",
        user=user,
        orders=orders.items[:3],
        stack_catalog=stack_catalog[:4],
        tariffs=tariffs,
        addons=addons,
    )
    return _template_response(request, "pages/home.html", context)


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
    context = _build_context(
        request,
        title="Catalog",
        active_route="catalog",
        user=user,
        orders=orders,
        stack_catalog=stack_catalog,
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
    context = _build_context(
        request,
        title=order.title,
        active_route="catalog",
        user=user,
        order=serialize_order(order, locale=locale),
    )
    return _template_response(request, "pages/order_detail.html", context)


@router.get("/profile")
async def profile_page(request: Request, session: AsyncSession = Depends(get_db_session)) -> Response:
    user = await resolve_current_user(session, request)
    if user is None:
        return _auth_redirect()
    locale = detect_locale(request, get_settings())
    stack_catalog = await get_stack_catalog(session, locale)
    tariffs = await list_tariffs(session)
    context = _build_context(
        request,
        title="Profile",
        active_route="profile",
        user=user,
        stack_catalog=stack_catalog,
        tariffs=tariffs,
        error=None,
        success=False,
    )
    return _template_response(request, "pages/profile.html", context)


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
            error=_exception_message(exc),
            success=False,
        )
        return _template_response(request, "pages/profile.html", context)

    context = _build_context(
        request,
        title="Profile",
        active_route="profile",
        user=user,
        stack_catalog=stack_catalog,
        tariffs=await list_tariffs(session),
        error=None,
        success=True,
    )
    return _template_response(request, "pages/profile.html", context)


@router.get("/swipe")
async def swipe_page(
    request: Request,
    target: str = Query(default="orders", pattern="^(orders|executors)$"),
    stack: str | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    user = await resolve_current_user(session, request)
    if user is None:
        return _auth_redirect()
    locale = detect_locale(request, get_settings())
    cards = await build_swipe_cards(session, user, target=target, stack=stack, locale=locale)
    stack_catalog = await get_stack_catalog(session, locale)
    context = _build_context(
        request,
        title="Swipe",
        active_route="swipe",
        user=user,
        cards=cards,
        stack_catalog=stack_catalog,
        target=target,
        stack_filter=stack or "",
    )
    return _template_response(request, "pages/swipe.html", context)


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


@router.get("/auth/demo/{user_id}")
async def demo_login(user_id: int, request: Request) -> RedirectResponse:
    request.session["user_id"] = user_id
    return RedirectResponse(url="/profile", status_code=303)


@router.get("/logout")
async def web_logout(request: Request) -> RedirectResponse:
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)


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
