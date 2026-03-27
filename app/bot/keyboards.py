from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from app.core.config import get_settings


def main_menu_keyboard() -> InlineKeyboardMarkup:
    settings = get_settings()
    base_url = settings.app.base_url.rstrip("/")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Открыть Mini App",
                    web_app=WebAppInfo(url=base_url),
                )
            ],
            [
                InlineKeyboardButton(text="Каталог заказов", url=f"{base_url}/catalog"),
                InlineKeyboardButton(text="Swipe", url=f"{base_url}/swipe"),
            ],
            [
                InlineKeyboardButton(text="Профиль", url=f"{base_url}/profile"),
                InlineKeyboardButton(text="Мои заказы", url=f"{base_url}/me/orders"),
            ],
        ]
    )


def order_link_keyboard(order_slug: str) -> InlineKeyboardMarkup:
    base_url = get_settings().app.base_url.rstrip("/")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Открыть заказ", url=f"{base_url}/orders/{order_slug}")]
        ]
    )
