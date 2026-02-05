from __future__ import annotations

from contextlib import asynccontextmanager

import aiosqlite


class Database:
    def __init__(self, path: str) -> None:
        self._path = path

    @asynccontextmanager
    async def connection(self) -> aiosqlite.Connection:
        conn = await aiosqlite.connect(self._path)
        await conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
        finally:
            await conn.close()
