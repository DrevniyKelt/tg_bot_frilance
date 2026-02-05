from fastapi import FastAPI

from app.api.routes import api_router
from app.utils.errors import register_exception_handlers
from app.utils.logging import configure_logging


def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(title="Freelance System API", version="0.1.0")
    register_exception_handlers(app)

    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
