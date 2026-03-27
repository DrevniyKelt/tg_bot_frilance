from __future__ import annotations

from aiogram import Bot

from app.bot.keyboards import order_link_keyboard
from app.bot.messages import executor_selected_text, new_application_text
from app.core.config import get_settings
from app.db.models import Order, User


async def notify_new_application(*, order: Order, executor: User) -> bool:
    if order.client.chat_id is None:
        return False
    return await _send_message(
        chat_id=order.client.chat_id,
        text=new_application_text(order.title, executor.display_name),
        order_slug=order.slug,
    )


async def notify_executor_selected(*, order: Order, executor: User) -> bool:
    if executor.chat_id is None:
        return False
    return await _send_message(
        chat_id=executor.chat_id,
        text=executor_selected_text(order.title),
        order_slug=order.slug,
    )


async def _send_message(*, chat_id: int, text: str, order_slug: str) -> bool:
    settings = get_settings()
    if not settings.telegram.bot_token:
        return False
    bot = Bot(settings.telegram.bot_token)
    try:
        await bot.send_message(chat_id=chat_id, text=text, reply_markup=order_link_keyboard(order_slug))
        return True
    finally:
        await bot.session.close()
