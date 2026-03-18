from __future__ import annotations

from collections import defaultdict

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.utils import csv_to_list, make_slug
from app.db.models import AddonPack, StackCategory, StackSynonym, StackTag, Tariff
from app.schemas.profile import StackCategoryPublic, StackTagPublic


async def get_stack_catalog(session: AsyncSession, locale: str) -> list[StackCategoryPublic]:
    categories = (
        await session.scalars(
            select(StackCategory)
            .options(selectinload(StackCategory.tags).selectinload(StackTag.categories))
            .order_by(StackCategory.name_en)
        )
    ).all()
    result: list[StackCategoryPublic] = []
    for category in categories:
        tags = [
            StackTagPublic(
                id=tag.id,
                slug=tag.slug,
                name=tag.name_ru if locale == "ru" else tag.name_en,
                categories=[cat.name_ru if locale == "ru" else cat.name_en for cat in tag.categories],
            )
            for tag in sorted(category.tags, key=lambda item: item.name_en.lower())
        ]
        result.append(
            StackCategoryPublic(
                id=category.id,
                slug=category.slug,
                name=category.name_ru if locale == "ru" else category.name_en,
                tags=tags,
            )
        )
    return result


async def normalize_stack_slugs(session: AsyncSession, raw_terms: list[str] | str | None) -> list[str]:
    normalized = csv_to_list(raw_terms) if isinstance(raw_terms, str) else [make_slug(term) for term in (raw_terms or [])]
    normalized = [term for term in normalized if term]
    if not normalized:
        return []

    tags = (
        await session.scalars(
            select(StackTag).where(
                or_(
                    StackTag.slug.in_(normalized),
                    StackTag.id.in_(
                        select(StackSynonym.stack_id).where(StackSynonym.normalized.in_(normalized))
                    ),
                )
            )
        )
    ).all()
    deduped = {tag.slug for tag in tags}
    return sorted(deduped)


async def resolve_stack_tags(session: AsyncSession, raw_terms: list[str] | str | None) -> list[StackTag]:
    slugs = await normalize_stack_slugs(session, raw_terms)
    if not slugs:
        return []
    return (await session.scalars(select(StackTag).where(StackTag.slug.in_(slugs)))).all()


async def list_tariffs(session: AsyncSession) -> list[Tariff]:
    return (await session.scalars(select(Tariff).order_by(Tariff.price_rub))).all()


async def list_addon_packs(session: AsyncSession) -> list[AddonPack]:
    return (await session.scalars(select(AddonPack).order_by(AddonPack.price_rub))).all()


async def stack_synonym_index(session: AsyncSession) -> dict[str, list[str]]:
    synonyms = (await session.scalars(select(StackSynonym).order_by(StackSynonym.normalized))).all()
    grouped: dict[str, list[str]] = defaultdict(list)
    for synonym in synonyms:
        grouped[synonym.stack.slug].append(synonym.normalized)
    return dict(grouped)
