from __future__ import annotations

import logging
from pathlib import Path

import aiosqlite


logger = logging.getLogger(__name__)


async def ensure_schema_table(conn: aiosqlite.Connection) -> None:
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL
        );
        """
    )
    await conn.commit()


async def apply_migrations(conn: aiosqlite.Connection, migrations_dir: Path) -> None:
    await ensure_schema_table(conn)

    rows = await conn.execute_fetchall("SELECT version FROM schema_migrations")
    applied = {row[0] for row in rows}

    migration_files = sorted(p for p in migrations_dir.glob("*.sql"))
    for path in migration_files:
        version = path.stem
        if version in applied:
            continue

        sql = path.read_text(encoding="utf-8")
        logger.info("Applying migration %s", version)
        try:
            await conn.execute("BEGIN")
            await conn.executescript(sql)
            await conn.execute(
                "INSERT INTO schema_migrations(version, applied_at) VALUES (?, datetime('now'))",
                (version,),
            )
            await conn.commit()
        except Exception:
            await conn.rollback()
            logger.exception("Migration failed: %s", version)
            raise
