from fastapi import APIRouter

from app.api.routers import ads, applications, auth, catalog, chats, me, moderation, orders, reviews, wallet


api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(catalog.router, tags=["catalog"])
api_router.include_router(me.router, tags=["me"])
api_router.include_router(orders.router, tags=["orders"])
api_router.include_router(applications.router, tags=["applications"])
api_router.include_router(chats.router, tags=["chats"])
api_router.include_router(wallet.router, tags=["wallet"])
api_router.include_router(reviews.router, tags=["reviews"])
api_router.include_router(ads.router, tags=["ads"])
api_router.include_router(moderation.router, tags=["moderation"])
