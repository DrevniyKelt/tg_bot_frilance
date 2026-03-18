from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.utils import make_slug
from app.db.models import (
    AddonPack,
    BudgetType,
    Currency,
    Order,
    RoleMode,
    StackCategory,
    StackMode,
    StackSynonym,
    StackTag,
    Subscription,
    SubscriptionStatus,
    Tariff,
    User,
    UserProfile,
    utcnow,
)
from app.db.session import get_session_factory


STACK_DATA = {
    ("backend", "Backend"): [
        ("python", "Python", ["py"]),
        ("fastapi", "FastAPI", []),
        ("django", "Django", []),
        ("node-js", "Node.js", ["node", "nodejs"]),
        ("go", "Go", ["golang"]),
    ],
    ("frontend", "Frontend"): [
        ("react", "React", ["reactjs"]),
        ("next-js", "Next.js", ["next", "nextjs"]),
        ("typescript", "TypeScript", ["ts"]),
        ("javascript", "JavaScript", ["js"]),
        ("tailwind-css", "Tailwind CSS", ["tailwind"]),
    ],
    ("data", "Data"): [
        ("postgresql", "PostgreSQL", ["postgres", "pgsql"]),
        ("redis", "Redis", []),
        ("clickhouse", "ClickHouse", []),
    ],
    ("devops", "DevOps"): [
        ("docker", "Docker", []),
        ("kubernetes", "Kubernetes", ["k8s"]),
        ("terraform", "Terraform", []),
    ],
    ("design", "Design"): [
        ("figma", "Figma", []),
        ("ux-research", "UX Research", ["ux"]),
    ],
}


async def seed_demo_data() -> None:
    settings = get_settings()
    if not settings.demo.seed_data:
        return

    session_factory = get_session_factory()
    async with session_factory() as session:
        existing = await session.scalar(select(User.id).limit(1))
        if existing is not None:
            return
        await _seed_stack_catalog(session)
        await _seed_tariffs(session)
        await _seed_users_and_orders(session)
        await session.commit()


async def _seed_stack_catalog(session: AsyncSession) -> None:
    tags_index: dict[str, StackTag] = {}
    for (slug, label_en), items in STACK_DATA.items():
        category = StackCategory(slug=slug, name_ru=label_en, name_en=label_en)
        session.add(category)
        for tag_slug, label, synonyms in items:
            tag = tags_index.get(tag_slug)
            if tag is None:
                tag = StackTag(slug=tag_slug, name_ru=label, name_en=label)
                tags_index[tag_slug] = tag
                session.add(tag)
                seen_normalized: set[str] = set()
                base_synonyms = [label, tag_slug, *synonyms]
                for raw_synonym in base_synonyms:
                    normalized = make_slug(raw_synonym)
                    if not normalized or normalized in seen_normalized:
                        continue
                    seen_normalized.add(normalized)
                    session.add(
                        StackSynonym(
                            stack=tag,
                            synonym=raw_synonym,
                            normalized=normalized,
                        )
                    )
            category.tags.append(tag)
    await session.flush()


async def _seed_tariffs(session: AsyncSession) -> None:
    session.add_all(
        [
            Tariff(
                code="starter",
                name_ru="Starter",
                name_en="Starter",
                price_rub=Decimal("1490.00"),
                period_days=30,
                create_orders_per_day=15,
                bids_per_day=80,
                ads_disabled=False,
                premium_ranking=False,
                priority_application=False,
            ),
            Tariff(
                code="pro",
                name_ru="Pro",
                name_en="Pro",
                price_rub=Decimal("3990.00"),
                period_days=30,
                create_orders_per_day=100,
                bids_per_day=300,
                ads_disabled=True,
                premium_ranking=True,
                priority_application=True,
            ),
            AddonPack(
                code="extra-bids-25",
                name_ru="+25 откликов",
                name_en="+25 bids",
                extra_orders=0,
                extra_bids=25,
                price_rub=Decimal("490.00"),
            ),
            AddonPack(
                code="extra-orders-10",
                name_ru="+10 публикаций",
                name_en="+10 job posts",
                extra_orders=10,
                extra_bids=0,
                price_rub=Decimal("790.00"),
            ),
        ]
    )
    await session.flush()


async def _seed_users_and_orders(session: AsyncSession) -> None:
    tags = {
        tag.slug: tag
        for tag in (await session.scalars(select(StackTag).order_by(StackTag.slug))).all()
    }
    tariffs = {
        tariff.code: tariff
        for tariff in (await session.scalars(select(Tariff).order_by(Tariff.code))).all()
    }

    users = [
        User(
            tg_id=10001,
            username="mihai",
            display_name="Mihai Demo",
            primary_role=RoleMode.BOTH,
            locale="ru",
            profile=UserProfile(
                headline="Full-stack product builder",
                bio="Запускаю закрытую бету и проверяю, как UX работает и в браузере, и внутри Telegram Mini App.",
                wallet_balance=Decimal("26450.00"),
                avg_executor_rating=Decimal("4.90"),
                avg_client_rating=Decimal("4.80"),
            ),
            stacks=[tags["python"], tags["fastapi"], tags["react"], tags["postgresql"]],
        ),
        User(
            tg_id=10002,
            username="lena_ux",
            display_name="Lena Morozova",
            primary_role=RoleMode.EXECUTOR,
            locale="ru",
            profile=UserProfile(
                headline="Product designer for B2B SaaS",
                bio="Figma, UX research, прототипирование и продуктовые лендинги под закрытые беты.",
                wallet_balance=Decimal("9100.00"),
                avg_executor_rating=Decimal("4.95"),
                avg_client_rating=Decimal("4.70"),
            ),
            stacks=[tags["figma"], tags["ux-research"], tags["react"]],
        ),
        User(
            tg_id=10003,
            username="ivan_devops",
            display_name="Ivan Petrov",
            primary_role=RoleMode.EXECUTOR,
            locale="ru",
            profile=UserProfile(
                headline="DevOps and infra",
                bio="Kubernetes, Docker, Terraform, CI/CD, observability.",
                wallet_balance=Decimal("12100.00"),
                avg_executor_rating=Decimal("4.85"),
                avg_client_rating=Decimal("4.60"),
            ),
            stacks=[tags["docker"], tags["kubernetes"], tags["terraform"], tags["go"]],
        ),
    ]
    session.add_all(users)
    await session.flush()

    session.add(
        Subscription(
            user_id=users[1].id,
            tariff_id=tariffs["pro"].id,
            status=SubscriptionStatus.ACTIVE,
            started_at=utcnow(),
            ends_at=utcnow() + timedelta(days=30),
        )
    )

    seeded_orders = [
        Order(
            slug="telegram-mini-app-fastapi-launch",
            client_id=users[0].id,
            title="Собрать Telegram Mini App для закрытой беты",
            category="Web / Product",
            summary="Нужен разработчик, который соберёт адаптивный FastAPI/Jinja2 интерфейс и подготовит его к Mini App контейнеру.",
            description="Ищем исполнителя под первую половину roadmap: каталог заказов, профиль, стек, swipe-режим, локализация RU/EN и базовый OpenAPI.",
            budget_type=BudgetType.FIXED,
            currency=Currency.RUB,
            stack_mode=StackMode.SPECIFIC,
            budget_amount=Decimal("120000.00"),
            executor_amount=Decimal("120000.00"),
            client_total_amount=Decimal("121200.00"),
            fee_percent=Decimal("0.01"),
            auto_filters={"min_rating": 4.7, "delivery_days": 21, "priority": "balanced"},
            stacks=[tags["python"], tags["fastapi"], tags["react"], tags["postgresql"]],
        ),
        Order(
            slug="figma-to-jinja-design-system",
            client_id=users[0].id,
            title="UI-kit в стиле Ozon без визуального мусора",
            category="Design / Frontend",
            summary="Нужен дизайнер, который соберёт лёгкую светлую систему карточек, таблиц и CTA для веба и Mini App.",
            description="Ожидаем сильный UX, аккуратные карточки, хороший mobile view и проектирование под Jinja-компоненты.",
            budget_type=BudgetType.AUCTION,
            currency=Currency.RUB,
            stack_mode=StackMode.SPECIFIC,
            budget_amount=Decimal("65000.00"),
            executor_amount=Decimal("65000.00"),
            client_total_amount=Decimal("65650.00"),
            fee_percent=Decimal("0.01"),
            auto_filters={"min_rating": 4.5, "delivery_days": 14, "priority": "mixed"},
            stacks=[tags["figma"], tags["react"], tags["tailwind-css"]],
        ),
        Order(
            slug="k8s-observability-foundation",
            client_id=users[0].id,
            title="Подготовить k8s-инфраструктуру под следующий релиз",
            category="DevOps",
            summary="Нужен инженер для проектирования Helm/Ingress/CI контура и закладки деплоя под следующий этап.",
            description="Пока без Redis и тяжёлых воркеров, но нужен внятный фундамент под масштабирование и k8s production.",
            budget_type=BudgetType.FIXED,
            currency=Currency.RUB,
            stack_mode=StackMode.SPECIFIC,
            budget_amount=Decimal("95000.00"),
            executor_amount=Decimal("95000.00"),
            client_total_amount=Decimal("95950.00"),
            fee_percent=Decimal("0.01"),
            auto_filters={"min_rating": 4.8, "delivery_days": 18, "priority": "strict"},
            stacks=[tags["docker"], tags["kubernetes"], tags["terraform"]],
        ),
    ]
    session.add_all(seeded_orders)
