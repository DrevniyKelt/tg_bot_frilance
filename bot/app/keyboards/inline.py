from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="Задания", callback_data="tasks")],
        [InlineKeyboardButton(text="Поиск", callback_data="search")],
        [InlineKeyboardButton(text="Мои отклики", callback_data="my_bids")],
        [InlineKeyboardButton(text="Мои задания", callback_data="my_tasks")],
        [InlineKeyboardButton(text="Профиль", callback_data="profile")],
        [InlineKeyboardButton(text="Поддержка", callback_data="support")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
