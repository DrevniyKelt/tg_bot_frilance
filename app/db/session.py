from __future__ import annotations

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
