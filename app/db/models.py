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


class ApplicationStatus(StrEnum):
    PENDING = "pending"
    SELECTED = "selected"
    REJECTED = "rejected"
    ARCHIVED = "archived"
    CANCELLED = "cancelled"


class SubscriptionStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class WalletTransactionKind(StrEnum):
    TOPUP = "topup"
    WITHDRAW = "withdraw"
    ESCROW_HOLD = "escrow_hold"
    ESCROW_RELEASE = "escrow_release"
    ESCROW_REFUND = "escrow_refund"


class WalletTransactionStatus(StrEnum):
    SUCCEEDED = "succeeded"
    PENDING = "pending"
    CANCELLED = "cancelled"


class EscrowStatus(StrEnum):
    NONE = "none"
    HELD = "held"
    RELEASED = "released"
    REFUNDED = "refunded"


class ReviewRole(StrEnum):
    CLIENT_TO_EXECUTOR = "client_to_executor"
    EXECUTOR_TO_CLIENT = "executor_to_client"


class ModerationTicketStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"


class ModerationTargetType(StrEnum):
    ORDER = "order"
    USER = "user"


class AdEventKind(StrEnum):
    IMPRESSION = "impression"
    CLICK = "click"


class SwipeActorSide(StrEnum):
    CLIENT = "client"
    EXECUTOR = "executor"


class SwipeDecisionDirection(StrEnum):
    ACCEPT = "accept"
    REJECT = "reject"


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
    chat_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
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
    applications: Mapped[list["Application"]] = relationship(
        back_populates="executor",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    chats_as_client: Mapped[list["Chat"]] = relationship(
        foreign_keys="Chat.client_id",
        back_populates="client",
        lazy="selectin",
    )
    chats_as_executor: Mapped[list["Chat"]] = relationship(
        foreign_keys="Chat.executor_id",
        back_populates="executor",
        lazy="selectin",
    )
    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="author",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    wallet_transactions: Mapped[list["WalletTransaction"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    reviews_written: Mapped[list["Review"]] = relationship(
        foreign_keys="Review.reviewer_id",
        back_populates="reviewer",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    reviews_received: Mapped[list["Review"]] = relationship(
        foreign_keys="Review.reviewee_id",
        back_populates="reviewee",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    moderation_tickets_reported: Mapped[list["ModerationTicket"]] = relationship(
        foreign_keys="ModerationTicket.reporter_id",
        back_populates="reporter",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    moderation_tickets_targeting: Mapped[list["ModerationTicket"]] = relationship(
        foreign_keys="ModerationTicket.target_user_id",
        back_populates="target_user",
        lazy="selectin",
    )
    swipe_decisions: Mapped[list["SwipeDecision"]] = relationship(
        back_populates="actor",
        foreign_keys="SwipeDecision.actor_user_id",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


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
    escrow_status: Mapped[EscrowStatus] = mapped_column(
        Enum(EscrowStatus, native_enum=False),
        default=EscrowStatus.NONE,
    )
    escrow_amount: Mapped[Decimal] = mapped_column(default=Decimal("0.00"))
    client_completion_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    executor_completion_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    auto_filters: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    client: Mapped[User] = relationship(back_populates="orders", lazy="selectin")
    stacks: Mapped[list[StackTag]] = relationship(
        secondary=order_stack_table,
        back_populates="orders",
        lazy="selectin",
    )
    applications: Mapped[list["Application"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    chats: Mapped[list["Chat"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    wallet_transactions: Mapped[list["WalletTransaction"]] = relationship(
        back_populates="order",
        lazy="selectin",
    )
    reviews: Mapped[list["Review"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    moderation_tickets: Mapped[list["ModerationTicket"]] = relationship(
        back_populates="order",
        lazy="selectin",
    )
    swipe_decisions: Mapped[list["SwipeDecision"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    executor_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, native_enum=False),
        default=ApplicationStatus.PENDING,
    )
    cover_letter: Mapped[str] = mapped_column(Text, default="")
    proposed_amount: Mapped[Decimal | None] = mapped_column(nullable=True)
    delivery_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    attachment_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_quick: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    order: Mapped[Order] = relationship(back_populates="applications", lazy="selectin")
    executor: Mapped[User] = relationship(back_populates="applications", lazy="selectin")


class SwipeDecision(Base):
    __tablename__ = "swipe_decisions"
    __table_args__ = (
        UniqueConstraint("actor_user_id", "order_id", "executor_id", "actor_side", name="uq_swipe_decision_pair"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    executor_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    actor_side: Mapped[SwipeActorSide] = mapped_column(Enum(SwipeActorSide, native_enum=False))
    direction: Mapped[SwipeDecisionDirection] = mapped_column(
        Enum(SwipeDecisionDirection, native_enum=False),
        default=SwipeDecisionDirection.ACCEPT,
    )
    matched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    actor: Mapped[User] = relationship(foreign_keys=[actor_user_id], back_populates="swipe_decisions", lazy="selectin")
    order: Mapped[Order] = relationship(back_populates="swipe_decisions", lazy="selectin")
    executor: Mapped[User] = relationship(foreign_keys=[executor_id], lazy="selectin")


class Chat(Base):
    __tablename__ = "chats"
    __table_args__ = (UniqueConstraint("order_id", "client_id", "executor_id", name="uq_chat_order_pair"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    executor_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    order: Mapped[Order] = relationship(back_populates="chats", lazy="selectin")
    client: Mapped[User] = relationship(foreign_keys=[client_id], back_populates="chats_as_client", lazy="selectin")
    executor: Mapped[User] = relationship(foreign_keys=[executor_id], back_populates="chats_as_executor", lazy="selectin")
    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="chat",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    chat: Mapped[Chat] = relationship(back_populates="messages", lazy="selectin")
    author: Mapped[User] = relationship(back_populates="messages", lazy="selectin")


class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True)
    kind: Mapped[WalletTransactionKind] = mapped_column(Enum(WalletTransactionKind, native_enum=False))
    status: Mapped[WalletTransactionStatus] = mapped_column(
        Enum(WalletTransactionStatus, native_enum=False),
        default=WalletTransactionStatus.SUCCEEDED,
    )
    currency: Mapped[Currency] = mapped_column(Enum(Currency, native_enum=False), default=Currency.RUB)
    amount: Mapped[Decimal] = mapped_column(default=Decimal("0.00"))
    balance_after: Mapped[Decimal] = mapped_column(default=Decimal("0.00"))
    note: Mapped[str] = mapped_column(String(240), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(back_populates="wallet_transactions", lazy="selectin")
    order: Mapped[Order | None] = relationship(back_populates="wallet_transactions", lazy="selectin")


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (UniqueConstraint("order_id", "reviewer_id", "reviewee_id", name="uq_review_order_pair"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    reviewee_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[ReviewRole] = mapped_column(Enum(ReviewRole, native_enum=False))
    score: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    order: Mapped[Order] = relationship(back_populates="reviews", lazy="selectin")
    reviewer: Mapped[User] = relationship(foreign_keys=[reviewer_id], back_populates="reviews_written", lazy="selectin")
    reviewee: Mapped[User] = relationship(foreign_keys=[reviewee_id], back_populates="reviews_received", lazy="selectin")


class ModerationTicket(Base):
    __tablename__ = "moderation_tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    reporter_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    target_type: Mapped[ModerationTargetType] = mapped_column(Enum(ModerationTargetType, native_enum=False))
    target_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[ModerationTicketStatus] = mapped_column(
        Enum(ModerationTicketStatus, native_enum=False),
        default=ModerationTicketStatus.OPEN,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    reporter: Mapped[User] = relationship(foreign_keys=[reporter_id], back_populates="moderation_tickets_reported", lazy="selectin")
    target_user: Mapped[User | None] = relationship(foreign_keys=[target_user_id], back_populates="moderation_tickets_targeting", lazy="selectin")
    order: Mapped[Order | None] = relationship(back_populates="moderation_tickets", lazy="selectin")


class AdCampaign(Base):
    __tablename__ = "ad_campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    title: Mapped[str] = mapped_column(String(160))
    body: Mapped[str] = mapped_column(Text)
    placement_name: Mapped[str] = mapped_column(String(64), index=True)
    target_url: Mapped[str] = mapped_column(String(240))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    impressions_count: Mapped[int] = mapped_column(Integer, default=0)
    clicks_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    events: Mapped[list["AdEvent"]] = relationship(
        back_populates="campaign",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class AdEvent(Base):
    __tablename__ = "ad_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("ad_campaigns.id", ondelete="CASCADE"), index=True)
    kind: Mapped[AdEventKind] = mapped_column(Enum(AdEventKind, native_enum=False))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    campaign: Mapped[AdCampaign] = relationship(back_populates="events", lazy="selectin")
