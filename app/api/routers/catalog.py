from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.i18n import detect_locale
from app.db.session import get_db_session
from app.services.catalog import (
    get_stack_catalog,
    list_addon_packs,
    list_tariffs,
    stack_synonym_index,
)


router = APIRouter()


@router.get("/catalog/stacks")
async def catalog_stacks(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    locale = detect_locale(request, get_settings())
    items = await get_stack_catalog(session, locale)
    return [item.model_dump() for item in items]


@router.get("/catalog/tariffs")
async def catalog_tariffs(session: AsyncSession = Depends(get_db_session)) -> list[dict]:
    tariffs = await list_tariffs(session)
    return [
        {
            "code": tariff.code,
            "name_ru": tariff.name_ru,
            "name_en": tariff.name_en,
            "price_rub": str(tariff.price_rub),
            "period_days": tariff.period_days,
            "create_orders_per_day": tariff.create_orders_per_day,
            "bids_per_day": tariff.bids_per_day,
            "premium_ranking": tariff.premium_ranking,
            "priority_application": tariff.priority_application,
            "ads_disabled": tariff.ads_disabled,
        }
        for tariff in tariffs
    ]


@router.get("/catalog/addons")
async def catalog_addons(session: AsyncSession = Depends(get_db_session)) -> list[dict]:
    addons = await list_addon_packs(session)
    return [
        {
            "code": addon.code,
            "name_ru": addon.name_ru,
            "name_en": addon.name_en,
            "price_rub": str(addon.price_rub),
            "extra_orders": addon.extra_orders,
            "extra_bids": addon.extra_bids,
        }
        for addon in addons
    ]


@router.get("/catalog/stack-synonyms")
async def catalog_stack_synonyms(session: AsyncSession = Depends(get_db_session)) -> dict[str, list[str]]:
    return await stack_synonym_index(session)
