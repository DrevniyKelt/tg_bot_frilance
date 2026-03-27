from __future__ import annotations

from app.schemas.profile import PublicUserProfile


def start_text() -> str:
    return (
        "SkillLane\n\n"
        "Закрытая beta-биржа для IT-заказов: каталог, swipe, отклики, сделки и чат.\n"
        "Открой Mini App или используй быстрые кнопки ниже."
    )


def help_text() -> str:
    return (
        "Команды:\n"
        "/start - открыть главное меню\n"
        "/profile - краткий профиль\n"
        "/orders - мои заказы\n"
        "/catalog - перейти в каталог\n"
        "/swipe - открыть swipe-поиск\n"
        "/help - справка"
    )


def profile_text(profile: PublicUserProfile) -> str:
    stack = ", ".join(tag.name for tag in profile.stack[:6]) or "Стек пока не заполнен"
    tariff = profile.active_tariff or "Free"
    return (
        f"{profile.display_name}\n"
        f"Роль: {profile.role}\n"
        f"Тариф: {tariff}\n"
        f"Баланс: {profile.wallet_balance}\n"
        f"Матчи: {profile.total_matches}\n"
        f"Completed: {profile.completed_deals}\n"
        f"Стек: {stack}"
    )


def new_application_text(order_title: str, executor_name: str) -> str:
    return f"Новый отклик на заказ «{order_title}» от {executor_name}."


def executor_selected_text(order_title: str) -> str:
    return f"Тебя выбрали исполнителем по заказу «{order_title}»."
