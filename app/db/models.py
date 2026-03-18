from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    Column,
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    type_annotation_map = {
        Decimal: Numeric(12, 2),
    }


class RoleMode(StrEnum):
    CLIENT = "client"
    EXECUTOR = "executor"
    BOTH = "both"


class BudgetType(StrEnum):
    FIXED = "fixed"
    AUCTION = "auction"


class Currency(StrEnum):
    RUB = "RUB"
    ETH = "ETH"
    INTERNAL = "INTERNAL"


class StackMode(StrEnum):
    FREE = "free"
    SPECIFIC = "specific"


class OrderStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    IN_REVIEW = "in_review"
    MATCHED = "matched"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    BANNED = "banned"


class SubscriptionStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


user_stack_table = Table(
    "user_stacks",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("stack_id", ForeignKey("stack_tags.id", ondelete="CASCADE"), primary_key=True),
)


order_stack_table = Table(
    "order_stacks",
    Base.metadata,
    Column("order_id", ForeignKey("orders.id", ondelete="CASCADE"), primary_key=True),
    Column("stack_id", ForeignKey("stack_tags.id", ondelete="CASCADE"), primary_key=True),
)


stack_category_tag_table = Table(
    "stack_category_tags",
    Base.metadata,
    Column("category_id", ForeignKey("stack_categories.id", ondelete="CASCADE"), primary_key=True),
    Column("stack_id", ForeignKey("stack_tags.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    display_name: Mapped[str] = mapped_column(String(120))
    primary_role: Mapped[RoleMode] = mapped_column(
        Enum(RoleMode, native_enum=False),
        default=RoleMode.BOTH,
    )
    locale: Mapped[str] = mapped_column(String(8), default="ru")
    completed_deals: Mapped[int] = mapped_column(Integer, default=0)
    total_matches: Mapped[int] = mapped_column(Integer, default=0)
    unmatched_applications_last_week: Mapped[int] = mapped_column(Integer, default=0)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_active_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    profile: Mapped["UserProfile"] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )
    stacks: Mapped[list["StackTag"]] = relationship(
        secondary=user_stack_table,
        back_populates="users",
        lazy="selectin",
    )
    subscriptions: Mapped[list["Subscription"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    orders: Mapped[list["Order"]] = relationship(back_populates="client", lazy="selectin")


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    headline: Mapped[str] = mapped_column(String(160), default="")
    bio: Mapped[str] = mapped_column(Text, default="")
    wallet_balance: Mapped[Decimal] = mapped_column(default=Decimal("0.00"))
    avg_executor_rating: Mapped[Decimal] = mapped_column(default=Decimal("0.00"))
    avg_client_rating: Mapped[Decimal] = mapped_column(default=Decimal("0.00"))

    user: Mapped[User] = relationship(back_populates="profile")


class StackCategory(Base):
    __tablename__ = "stack_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    name_ru: Mapped[str] = mapped_column(String(120))
    name_en: Mapped[str] = mapped_column(String(120))

    tags: Mapped[list["StackTag"]] = relationship(
        secondary=stack_category_tag_table,
        back_populates="categories",
        lazy="selectin",
    )


class StackTag(Base):
    __tablename__ = "stack_tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    name_ru: Mapped[str] = mapped_column(String(120))
    name_en: Mapped[str] = mapped_column(String(120))

    categories: Mapped[list[StackCategory]] = relationship(
        secondary=stack_category_tag_table,
        back_populates="tags",
        lazy="selectin",
    )
    synonyms: Mapped[list["StackSynonym"]] = relationship(
        back_populates="stack",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    users: Mapped[list[User]] = relationship(
        secondary=user_stack_table,
        back_populates="stacks",
        lazy="selectin",
    )
    orders: Mapped[list["Order"]] = relationship(
        secondary=order_stack_table,
        back_populates="stacks",
        lazy="selectin",
    )


class StackSynonym(Base):
    __tablename__ = "stack_synonyms"
    __table_args__ = (UniqueConstraint("normalized", name="uq_stack_synonym_normalized"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    stack_id: Mapped[int] = mapped_column(ForeignKey("stack_tags.id", ondelete="CASCADE"))
    synonym: Mapped[str] = mapped_column(String(120))
    normalized: Mapped[str] = mapped_column(String(120))

    stack: Mapped[StackTag] = relationship(back_populates="synonyms")


class Tariff(Base):
    __tablename__ = "tariffs"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    name_ru: Mapped[str] = mapped_column(String(120))
    name_en: Mapped[str] = mapped_column(String(120))
    price_rub: Mapped[Decimal] = mapped_column(default=Decimal("0.00"))
    period_days: Mapped[int] = mapped_column(Integer, default=30)
    create_orders_per_day: Mapped[int] = mapped_column(Integer, default=20)
    bids_per_day: Mapped[int] = mapped_column(Integer, default=200)
    ads_disabled: Mapped[bool] = mapped_column(Boolean, default=False)
    premium_ranking: Mapped[bool] = mapped_column(Boolean, default=False)
    priority_application: Mapped[bool] = mapped_column(Boolean, default=False)

    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="tariff", lazy="selectin")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    tariff_id: Mapped[int] = mapped_column(ForeignKey("tariffs.id", ondelete="CASCADE"))
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, native_enum=False),
        default=SubscriptionStatus.ACTIVE,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="subscriptions")
    tariff: Mapped[Tariff] = relationship(back_populates="subscriptions")


class AddonPack(Base):
    __tablename__ = "addon_packs"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    name_ru: Mapped[str] = mapped_column(String(120))
    name_en: Mapped[str] = mapped_column(String(120))
    extra_orders: Mapped[int] = mapped_column(Integer, default=0)
    extra_bids: Mapped[int] = mapped_column(Integer, default=0)
    price_rub: Mapped[Decimal] = mapped_column(default=Decimal("0.00"))


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(160), unique=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(180))
    category: Mapped[str] = mapped_column(String(120))
    summary: Mapped[str] = mapped_column(String(240))
    description: Mapped[str] = mapped_column(Text)
    budget_type: Mapped[BudgetType] = mapped_column(Enum(BudgetType, native_enum=False))
    currency: Mapped[Currency] = mapped_column(Enum(Currency, native_enum=False), default=Currency.RUB)
    stack_mode: Mapped[StackMode] = mapped_column(
        Enum(StackMode, native_enum=False),
        default=StackMode.SPECIFIC,
    )
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, native_enum=False),
        default=OrderStatus.PUBLISHED,
    )
    budget_amount: Mapped[Decimal] = mapped_column(default=Decimal("0.00"))
    executor_amount: Mapped[Decimal] = mapped_column(default=Decimal("0.00"))
    client_total_amount: Mapped[Decimal] = mapped_column(default=Decimal("0.00"))
    fee_percent: Mapped[Decimal] = mapped_column(default=Decimal("0.01"))
    post_moderation: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_filters: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    client: Mapped[User] = relationship(back_populates="orders", lazy="selectin")
    stacks: Mapped[list[StackTag]] = relationship(
        secondary=order_stack_table,
        back_populates="orders",
        lazy="selectin",
    )
