from __future__ import annotations

from aiogram import Bot
from aiogram.types import Message


async def edit_or_send(bot: Bot, chat_id: int, message_id: int | None, text: str, reply_markup=None) -> Message:
    if message_id:
        try:
            return await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=reply_markup,
            )
        except Exception:
            pass

    return await bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
