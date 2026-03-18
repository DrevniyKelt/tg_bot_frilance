from fastapi import APIRouter

from app.api.routers import auth, catalog, me, orders


api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(catalog.router, tags=["catalog"])
api_router.include_router(me.router, tags=["me"])
api_router.include_router(orders.router, tags=["orders"])
