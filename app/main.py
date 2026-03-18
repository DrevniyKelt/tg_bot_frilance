from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.db.seed import seed_demo_data
from app.db.session import close_engine, init_db
from app.web.router import router as web_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    await seed_demo_data()
    yield
    await close_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app.name,
        description="Closed-beta IT freelance marketplace MVP.",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(SessionMiddleware, secret_key=settings.app.secret_key)
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    app.include_router(api_router)
    app.include_router(web_router)
    return app


app = create_app()
