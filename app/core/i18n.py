from __future__ import annotations

from collections.abc import Callable

from fastapi import Request

from app.core.config import Settings


SUPPORTED_LOCALES = ("ru", "en")

MESSAGES = {
    "ru": {
        "nav.home": "Главная",
        "nav.catalog": "Каталог",
        "nav.swipe": "Свайп",
        "nav.profile": "Профиль",
        "nav.tariffs": "Тарифы",
        "nav.new_order": "Создать заказ",
        "cta.demo_login": "Войти как demo",
        "label.ru": "Русский",
        "label.en": "English",
        "label.client": "Заказчик",
        "label.executor": "Исполнитель",
        "label.both": "Обе роли",
        "label.fixed": "Фикс",
        "label.auction": "Аукцион",
        "label.rub": "Рубли",
        "label.eth": "ETH",
        "label.internal": "Внутренний баланс",
        "label.free": "Свободный стек",
        "label.specific": "Конкретный стек",
        "hero.kicker": "Сайт и Mini App на одном коде",
        "hero.title": "Биржа для IT-заказов без лишнего шума",
        "hero.subtitle": "Стек хранится структурно, поиск работает по синонимам, а свайп-режим подмешивает релевантные карточки вместо тупой сортировки.",
        "section.featured_orders": "Актуальные заказы",
        "section.featured_stack": "Каталог стека",
        "section.tariffs": "Тарифы и доп. пакеты",
        "catalog.title": "Каталог заказов",
        "catalog.subtitle": "Фильтры, поиск по стеку и нормализация синонимов уже включены.",
        "catalog.empty": "По текущим фильтрам ничего не найдено.",
        "profile.title": "Профиль и стек",
        "profile.subtitle": "Минимальное ядро для закрытой беты: роли, био, стек, рейтинг, баланс и лимиты.",
        "order.new_title": "Создание заказа",
        "order.preview": "Предпросмотр комиссии",
        "swipe.title": "Swipe-поиск",
        "tariffs.title": "Тарифы и доппакеты",
        "common.search": "Поиск",
        "common.save": "Сохранить",
        "common.create": "Создать",
        "common.open": "Открыть",
        "common.reset": "Сбросить",
        "common.filters": "Фильтры",
        "common.details": "Подробнее",
        "common.similarity": "Совпадение",
        "common.demo_mode": "Demo mode включён",
    },
    "en": {
        "nav.home": "Home",
        "nav.catalog": "Marketplace",
        "nav.swipe": "Swipe",
        "nav.profile": "Profile",
        "nav.tariffs": "Plans",
        "nav.new_order": "Post job",
        "cta.demo_login": "Enter demo mode",
        "label.ru": "Russian",
        "label.en": "English",
        "label.client": "Client",
        "label.executor": "Executor",
        "label.both": "Both roles",
        "label.fixed": "Fixed",
        "label.auction": "Auction",
        "label.rub": "Rubles",
        "label.eth": "ETH",
        "label.internal": "Internal wallet",
        "label.free": "Free stack",
        "label.specific": "Specific stack",
        "hero.kicker": "Website and Mini App on one codebase",
        "hero.title": "An IT marketplace that stays structured",
        "hero.subtitle": "Skills are first-class entities, stack synonyms resolve automatically, and swipe mode mixes relevant cards instead of brute-force ranking.",
        "section.featured_orders": "Featured jobs",
        "section.featured_stack": "Stack catalog",
        "section.tariffs": "Plans and add-ons",
        "catalog.title": "Job catalog",
        "catalog.subtitle": "Filters, stack search, and synonym normalization are already wired.",
        "catalog.empty": "No jobs matched the current filters.",
        "profile.title": "Profile and stack",
        "profile.subtitle": "Closed-beta core: roles, bio, stack, rating, balance, and limits.",
        "order.new_title": "Create a new job",
        "order.preview": "Fee preview",
        "swipe.title": "Swipe discovery",
        "tariffs.title": "Plans and add-ons",
        "common.search": "Search",
        "common.save": "Save",
        "common.create": "Create",
        "common.open": "Open",
        "common.reset": "Reset",
        "common.filters": "Filters",
        "common.details": "Details",
        "common.similarity": "Similarity",
        "common.demo_mode": "Demo mode is enabled",
    },
}


def resolve_locale(raw: str | None, settings: Settings) -> str:
    candidate = (raw or settings.app.default_locale).lower()
    return candidate if candidate in SUPPORTED_LOCALES else settings.app.default_locale


def detect_locale(request: Request, settings: Settings) -> str:
    query_locale = request.query_params.get("lang")
    cookie_locale = request.cookies.get("locale")
    header_locale = request.headers.get("accept-language", "")
    header_candidate = header_locale.split(",", maxsplit=1)[0].split("-", maxsplit=1)[0]
    return resolve_locale(query_locale or cookie_locale or header_candidate, settings)


def translator(locale: str) -> Callable[[str], str]:
    bucket = MESSAGES.get(locale, MESSAGES["ru"])

    def translate(key: str) -> str:
        return bucket.get(key, key)

    return translate
