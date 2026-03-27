from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class AppSection:
    name: str = "SkillLane"
    brand_tagline: str = "IT freelance exchange for Telegram and web"
    secret_key: str = "dev-secret-change-me"
    default_locale: str = "ru"
    base_url: str = "http://127.0.0.1:8000"


@dataclass(frozen=True)
class DatabaseSection:
    url: str = "sqlite+aiosqlite:///./data/skilllane.db"
    echo: bool = False


@dataclass(frozen=True)
class TelegramSection:
    bot_token: str = ""
    allow_dev_login: bool = True
    bot_username: str = "skilllane_beta_bot"


@dataclass(frozen=True)
class DemoSection:
    seed_data: bool = True
    default_user_id: int = 1


@dataclass(frozen=True)
class FeatureSection:
    fee_mode: str = "deduct"
    fee_percent: float = 0.01
    require_tariff_after_first_completed: bool = True
    new_user_max_orders: int = 5
    new_user_max_applications: int = 100
    new_user_max_matches: int = 3
    new_user_max_unmatched_applications_per_week: int = 50
    swipe_min_similarity: float = 0.5
    swipe_mix_strategy: str = "mixed"


@dataclass(frozen=True)
class Settings:
    app: AppSection = AppSection()
    database: DatabaseSection = DatabaseSection()
    telegram: TelegramSection = TelegramSection()
    demo: DemoSection = DemoSection()
    features: FeatureSection = FeatureSection()
    config_path: Path = Path("data/config/settings.yaml")


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    if not isinstance(loaded, dict):
        raise ValueError(f"Configuration file {path} must contain a mapping at the root.")
    return loaded


def _section(data: dict[str, Any], key: str) -> dict[str, Any]:
    section = data.get(key, {})
    if not isinstance(section, dict):
        raise ValueError(f"Configuration section '{key}' must be a mapping.")
    return section


def _load_config_path() -> Path:
    raw_path = os.getenv("APP_CONFIG_PATH", "data/config/settings.yaml")
    return Path(raw_path)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    config_path = _load_config_path()
    raw = _read_yaml(config_path)

    app_values = {
        **AppSection().__dict__,
        **_section(raw, "app"),
    }
    database_values = {
        **DatabaseSection().__dict__,
        **_section(raw, "database"),
    }
    telegram_values = {
        **TelegramSection().__dict__,
        **_section(raw, "telegram"),
    }
    demo_values = {
        **DemoSection().__dict__,
        **_section(raw, "demo"),
    }
    feature_values = {
        **FeatureSection().__dict__,
        **_section(raw, "features"),
    }

    if os.getenv("APP_SECRET_KEY"):
        app_values["secret_key"] = os.getenv("APP_SECRET_KEY", app_values["secret_key"])
    if os.getenv("APP_DATABASE_URL"):
        database_values["url"] = os.getenv("APP_DATABASE_URL", database_values["url"])
    if os.getenv("APP_TELEGRAM_BOT_TOKEN"):
        telegram_values["bot_token"] = os.getenv(
            "APP_TELEGRAM_BOT_TOKEN",
            telegram_values["bot_token"],
        )

    return Settings(
        app=AppSection(**app_values),
        database=DatabaseSection(**database_values),
        telegram=TelegramSection(**telegram_values),
        demo=DemoSection(**demo_values),
        features=FeatureSection(**feature_values),
        config_path=config_path,
    )
