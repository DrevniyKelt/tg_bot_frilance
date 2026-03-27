from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.utils import make_slug
from app.db.models import (
    AddonPack,
    AdCampaign,
    BudgetType,
    Currency,
    Order,
    RoleMode,
    SwipeActorSide,
    SwipeDecision,
    SwipeDecisionDirection,
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
        await _seed_stack_catalog(session)
        await _seed_tariffs(session)
        await _seed_users_and_orders(session)
        await _seed_ads(session)
        await session.commit()


async def _seed_stack_catalog(session: AsyncSession) -> None:
    existing_category = await session.scalar(select(StackCategory.id).limit(1))
    if existing_category is not None:
        return
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
    existing_codes = set((await session.scalars(select(Tariff.code))).all())
    existing_addons = set((await session.scalars(select(AddonPack.code))).all())
    payload = []
    addon_payload = []
    if "starter" not in existing_codes:
        payload.append(
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
            )
        )
    if "pro" not in existing_codes:
        payload.append(
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
            )
        )
    if "extra-bids-25" not in existing_addons:
        addon_payload.append(
            AddonPack(
                code="extra-bids-25",
                name_ru="+25 откликов",
                name_en="+25 bids",
                extra_orders=0,
                extra_bids=25,
                price_rub=Decimal("490.00"),
            )
        )
    if "extra-orders-10" not in existing_addons:
        addon_payload.append(
            AddonPack(
                code="extra-orders-10",
                name_ru="+10 публикаций",
                name_en="+10 job posts",
                extra_orders=10,
                extra_bids=0,
                price_rub=Decimal("790.00"),
            )
        )
    session.add_all(payload + addon_payload)
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

    users_by_tg = {
        user.tg_id: user
        for user in (await session.scalars(select(User).where(User.tg_id.is_not(None)))).all()
    }
    if 10001 not in users_by_tg:
        session.add(
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
            )
        )
    if 10002 not in users_by_tg:
        session.add(
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
            )
        )
    if 10003 not in users_by_tg:
        session.add(
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
            )
        )
    if 10004 not in users_by_tg:
        session.add(
            User(
                tg_id=10004,
                username="daria_front",
                display_name="Daria Volkova",
                primary_role=RoleMode.EXECUTOR,
                locale="ru",
                profile=UserProfile(
                    headline="React and product UX",
                    bio="React, TypeScript, dashboards, onboarding flows and growth pages.",
                    wallet_balance=Decimal("7300.00"),
                    avg_executor_rating=Decimal("4.78"),
                    avg_client_rating=Decimal("4.55"),
                ),
                stacks=[tags["react"], tags["typescript"], tags["figma"], tags["ux-research"]],
            )
        )
    if 10005 not in users_by_tg:
        session.add(
            User(
                tg_id=10005,
                username="maks_python",
                display_name="Maksim Kiselev",
                primary_role=RoleMode.EXECUTOR,
                locale="ru",
                profile=UserProfile(
                    headline="Backend for product MVP",
                    bio="FastAPI, PostgreSQL, async pipelines, admin panels and integrations.",
                    wallet_balance=Decimal("11800.00"),
                    avg_executor_rating=Decimal("4.88"),
                    avg_client_rating=Decimal("4.61"),
                ),
                stacks=[tags["python"], tags["fastapi"], tags["postgresql"], tags["redis"]],
            )
        )
    if 10006 not in users_by_tg:
        session.add(
            User(
                tg_id=10006,
                username="sergey_ops",
                display_name="Sergey Smirnov",
                primary_role=RoleMode.EXECUTOR,
                locale="ru",
                profile=UserProfile(
                    headline="Infra, observability, release setup",
                    bio="Docker, k8s, Terraform, alerts, rollout strategy and monitoring.",
                    wallet_balance=Decimal("9700.00"),
                    avg_executor_rating=Decimal("4.82"),
                    avg_client_rating=Decimal("4.58"),
                ),
                stacks=[tags["docker"], tags["kubernetes"], tags["terraform"], tags["clickhouse"]],
            )
        )
    await session.flush()
    users = (await session.scalars(select(User).order_by(User.id.asc()))).all()

    session.add(
        Subscription(
            user_id=users[1].id,
            tariff_id=tariffs["pro"].id,
            status=SubscriptionStatus.ACTIVE,
            started_at=utcnow(),
            ends_at=utcnow() + timedelta(days=30),
        )
    )

    existing_slugs = set((await session.scalars(select(Order.slug))).all())
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
        Order(
            slug="react-admin-console-beta",
            client_id=users[0].id,
            title="React admin console for support and moderation",
            category="Frontend / Admin",
            summary="Нужен интерфейс с таблицами, фильтрами, действиями по тикетам и банам.",
            description="Ищем фронтенд-разработчика, который быстро соберёт внутреннюю консоль для поддержки и модерации закрытой беты.",
            budget_type=BudgetType.FIXED,
            currency=Currency.RUB,
            stack_mode=StackMode.SPECIFIC,
            budget_amount=Decimal("78000.00"),
            executor_amount=Decimal("78000.00"),
            client_total_amount=Decimal("78780.00"),
            fee_percent=Decimal("0.01"),
            auto_filters={"min_rating": 4.6, "delivery_days": 16, "priority": "balanced"},
            stacks=[tags["react"], tags["typescript"], tags["figma"]],
        ),
        Order(
            slug="python-async-worker-dashboard",
            client_id=users[0].id,
            title="Async dashboard for background worker telemetry",
            category="Backend / Analytics",
            summary="Нужен дашборд очередей, статусов задач и ручных ретраев без тяжёлого BI.",
            description="Собираем backend-инструмент для внутренней команды: лента задач, health, retries, status slices и фильтрация по типам worker job.",
            budget_type=BudgetType.AUCTION,
            currency=Currency.RUB,
            stack_mode=StackMode.SPECIFIC,
            budget_amount=Decimal("54000.00"),
            executor_amount=Decimal("54000.00"),
            client_total_amount=Decimal("54540.00"),
            fee_percent=Decimal("0.01"),
            auto_filters={"min_rating": 4.4, "delivery_days": 12, "priority": "mixed"},
            stacks=[tags["python"], tags["fastapi"], tags["postgresql"]],
        ),
        Order(
            slug="landing-copy-for-beta-launch",
            client_id=users[0].id,
            title="Landing copy and structure for beta launch",
            category="Product / Content",
            summary="Нужен контент-дизайнер под главный лендинг, тарифы и onboarding сценарии.",
            description="Требуется собрать тексты, структуру блоков, CTA и UX-копирайтинг для закрытого запуска продукта.",
            budget_type=BudgetType.FIXED,
            currency=Currency.RUB,
            stack_mode=StackMode.FREE,
            budget_amount=Decimal("32000.00"),
            executor_amount=Decimal("32000.00"),
            client_total_amount=Decimal("32320.00"),
            fee_percent=Decimal("0.01"),
            auto_filters={"delivery_days": 7, "priority": "balanced"},
            stacks=[tags["figma"], tags["ux-research"]],
        ),
        Order(
            slug="infra-cost-monitoring-mvp",
            client_id=users[0].id,
            title="Infra cost monitoring MVP for Kubernetes cluster",
            category="DevOps / FinOps",
            summary="Нужен расчёт затрат по namespace, alerts по аномалиям и daily cost snapshots.",
            description="Ищем инженера, который соберёт MVP cost visibility слоя для k8s: ingestion, aggregation, simple dashboards and alerts.",
            budget_type=BudgetType.FIXED,
            currency=Currency.RUB,
            stack_mode=StackMode.SPECIFIC,
            budget_amount=Decimal("88000.00"),
            executor_amount=Decimal("88000.00"),
            client_total_amount=Decimal("88880.00"),
            fee_percent=Decimal("0.01"),
            auto_filters={"min_rating": 4.7, "delivery_days": 20, "priority": "strict"},
            stacks=[tags["docker"], tags["kubernetes"], tags["clickhouse"], tags["go"]],
        ),
        Order(
            slug="react-onboarding-flow-rebuild",
            client_id=users[0].id,
            title="React onboarding flow rebuild for first 3 screens",
            category="Frontend / Product",
            summary="Нужен быстрый передел onboarding-сценария с более ясной структурой карточек и CTA.",
            description="Ищем фронтенд-разработчика с продуктовым чутьем, который соберет 3 ключевых экрана onboarding flow, улучшит конверсию и не разнесет текущий дизайн.",
            budget_type=BudgetType.FIXED,
            currency=Currency.RUB,
            stack_mode=StackMode.SPECIFIC,
            budget_amount=Decimal("47000.00"),
            executor_amount=Decimal("47000.00"),
            client_total_amount=Decimal("47470.00"),
            fee_percent=Decimal("0.01"),
            auto_filters={"min_rating": 4.6, "delivery_days": 9, "priority": "balanced"},
            stacks=[tags["react"], tags["typescript"], tags["figma"]],
        ),
        Order(
            slug="fastapi-crm-integration-mvp",
            client_id=users[0].id,
            title="FastAPI CRM integration MVP for inbound leads",
            category="Backend / Integration",
            summary="Нужен backend-контур для lead ingestion, status sync и webhook retries.",
            description="Ищем человека, который быстро соберет MVP интеграции между лендингом, внутренней CRM и уведомлениями команды без тяжелого enterprise слоя.",
            budget_type=BudgetType.FIXED,
            currency=Currency.RUB,
            stack_mode=StackMode.SPECIFIC,
            budget_amount=Decimal("69000.00"),
            executor_amount=Decimal("69000.00"),
            client_total_amount=Decimal("69690.00"),
            fee_percent=Decimal("0.01"),
            auto_filters={"min_rating": 4.5, "delivery_days": 14, "priority": "balanced"},
            stacks=[tags["python"], tags["fastapi"], tags["postgresql"]],
        ),
    ]
    session.add_all([order for order in seeded_orders if order.slug not in existing_slugs])
    await session.flush()
    await _seed_swipe_decisions(session)


async def _seed_swipe_decisions(session: AsyncSession) -> None:
    await session.execute(delete(SwipeDecision))
    users_by_name = {
        user.display_name: user
        for user in (await session.scalars(select(User).options(selectinload(User.profile)))).all()
    }
    orders_by_slug = {
        order.slug: order
        for order in (await session.scalars(select(Order))).all()
    }

    seed_payload = [
        ("Daria Volkova", "react-onboarding-flow-rebuild", "Daria Volkova", SwipeActorSide.EXECUTOR, SwipeDecisionDirection.ACCEPT),
        ("Mihai Demo", "react-admin-console-beta", "Lena Morozova", SwipeActorSide.CLIENT, SwipeDecisionDirection.ACCEPT),
        ("Lena Morozova", "react-admin-console-beta", "Lena Morozova", SwipeActorSide.EXECUTOR, SwipeDecisionDirection.REJECT),
        ("Mihai Demo", "infra-cost-monitoring-mvp", "Sergey Smirnov", SwipeActorSide.CLIENT, SwipeDecisionDirection.ACCEPT),
        ("Sergey Smirnov", "infra-cost-monitoring-mvp", "Sergey Smirnov", SwipeActorSide.EXECUTOR, SwipeDecisionDirection.REJECT),
    ]

    for actor_name, order_slug, executor_name, actor_side, direction in seed_payload:
        actor = users_by_name.get(actor_name)
        order = orders_by_slug.get(order_slug)
        executor = users_by_name.get(executor_name)
        if actor is None or order is None or executor is None:
            continue
        session.add(
            SwipeDecision(
                actor_user_id=actor.id,
                order_id=order.id,
                executor_id=executor.id,
                actor_side=actor_side,
                direction=direction,
            )
        )


async def _seed_ads(session: AsyncSession) -> None:
    existing_codes = set((await session.scalars(select(AdCampaign.code))).all())
    payload = []
    if "figma-audit-slot" not in existing_codes:
        payload.append(
            AdCampaign(
                code="figma-audit-slot",
                title="Проведи UX-аудит карточек до запуска",
                body="Рекламный слот MVP: карточки, мобильный сценарий, CTA и конверсия в отклик.",
                placement_name="catalog_inline",
                target_url="/tariffs",
                is_active=True,
            )
        )
    if "pro-subscription-slot" not in existing_codes:
        payload.append(
            AdCampaign(
                code="pro-subscription-slot",
                title="Pro снижает рекламу и поднимает отклики",
                body="Подписка открывает повышенные лимиты, priority application и более чистый интерфейс.",
                placement_name="home_sidebar",
                target_url="/tariffs",
                is_active=True,
            )
        )
    session.add_all(payload)
