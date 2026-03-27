from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from app.bot.keyboards import main_menu_keyboard
from app.bot.messages import help_text, profile_text, start_text
from app.bot.service import upsert_bot_user
from app.core.config import get_settings
from app.db.session import get_session_factory
from app.services.profiles import serialize_user


router = Router(name="skilllane-bot")


@router.message(Command("start"))
async def command_start(message: Message) -> None:
    if message.from_user is None or message.chat is None:
        return
    session_factory = get_session_factory()
    async with session_factory() as session:
        await upsert_bot_user(
            session,
            tg_id=message.from_user.id,
            chat_id=message.chat.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            locale=message.from_user.language_code or get_settings().app.default_locale,
        )
    await message.answer(start_text(), reply_markup=main_menu_keyboard())


@router.message(Command("help"))
async def command_help(message: Message) -> None:
    await message.answer(help_text(), reply_markup=main_menu_keyboard())


@router.message(Command("catalog"))
async def command_catalog(message: Message) -> None:
    base_url = get_settings().app.base_url.rstrip("/")
    await message.answer(f"Каталог заказов: {base_url}/catalog", reply_markup=main_menu_keyboard())


@router.message(Command("swipe"))
async def command_swipe(message: Message) -> None:
    base_url = get_settings().app.base_url.rstrip("/")
    await message.answer(f"Swipe-поиск: {base_url}/swipe", reply_markup=main_menu_keyboard())


@router.message(Command("orders"))
async def command_orders(message: Message) -> None:
    base_url = get_settings().app.base_url.rstrip("/")
    await message.answer(f"Мои заказы: {base_url}/me/orders", reply_markup=main_menu_keyboard())


@router.message(Command("profile"))
async def command_profile(message: Message) -> None:
    if message.from_user is None:
        return
    session_factory = get_session_factory()
    async with session_factory() as session:
        user = await upsert_bot_user(
            session,
            tg_id=message.from_user.id,
            chat_id=message.chat.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            locale=message.from_user.language_code or get_settings().app.default_locale,
        )
        profile = serialize_user(user, user.locale)
    await message.answer(profile_text(profile), reply_markup=main_menu_keyboard())


@router.message(F.text)
async def fallback_text(message: Message) -> None:
    await message.answer(
        "Основной интерфейс сейчас в Mini App и web-кабинете. Используй /start или /help.",
        reply_markup=main_menu_keyboard(),
    )
