from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.db.models import Base


_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None
_current_database_url: str | None = None


def _build_engine():
    global _engine, _session_factory, _current_database_url
    settings = get_settings()
    if _engine is not None and _current_database_url == settings.database.url:
        return
    if _engine is not None:
        return
    _engine = create_async_engine(settings.database.url, echo=settings.database.echo)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    _current_database_url = settings.database.url


async def init_db() -> None:
    _build_engine()
    async with _engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        await _run_sqlite_compat_migrations(connection)


async def close_engine() -> None:
    global _engine, _session_factory, _current_database_url
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
    _current_database_url = None


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    _build_engine()
    if _session_factory is None:
        raise RuntimeError("Database session factory is not initialized.")
    return _session_factory


async def get_db_session():
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session


async def _run_sqlite_compat_migrations(connection) -> None:
    settings = get_settings()
    if not settings.database.url.startswith("sqlite"):
        return

    table_columns = {
        "users": {
            "chat_id": "ALTER TABLE users ADD COLUMN chat_id INTEGER",
        },
        "orders": {
            "escrow_status": "ALTER TABLE orders ADD COLUMN escrow_status VARCHAR(20) DEFAULT 'NONE'",
            "escrow_amount": "ALTER TABLE orders ADD COLUMN escrow_amount NUMERIC(12, 2) DEFAULT 0.00",
            "client_completion_confirmed_at": "ALTER TABLE orders ADD COLUMN client_completion_confirmed_at DATETIME",
            "executor_completion_confirmed_at": "ALTER TABLE orders ADD COLUMN executor_completion_confirmed_at DATETIME",
            "started_at": "ALTER TABLE orders ADD COLUMN started_at DATETIME",
            "completed_at": "ALTER TABLE orders ADD COLUMN completed_at DATETIME",
        },
    }

    for table_name, migrations in table_columns.items():
        result = await connection.execute(text(f"PRAGMA table_info({table_name})"))
        existing_columns = {row[1] for row in result.fetchall()}
        for column_name, ddl in migrations.items():
            if column_name not in existing_columns:
                await connection.execute(text(ddl))

    await connection.execute(
        text(
            """
            UPDATE orders
            SET escrow_status = CASE LOWER(COALESCE(escrow_status, 'none'))
                WHEN 'none' THEN 'NONE'
                WHEN 'held' THEN 'HELD'
                WHEN 'released' THEN 'RELEASED'
                WHEN 'refunded' THEN 'REFUNDED'
                ELSE escrow_status
            END
            """
        )
    )
