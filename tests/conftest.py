from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def _write_test_config(path: Path, db_path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "app:",
                "  name: SkillLane Test",
                "  brand_tagline: test app",
                "  secret_key: test-secret",
                "  default_locale: ru",
                "  base_url: http://testserver",
                "database:",
                f"  url: sqlite+aiosqlite:///{db_path}",
                "  echo: false",
                "telegram:",
                "  bot_token: ''",
                "  allow_dev_login: true",
                "demo:",
                "  seed_data: true",
                "  default_user_id: 1",
                "features:",
                "  fee_mode: deduct",
                "  fee_percent: 0.01",
                "  require_tariff_after_first_completed: true",
                "  new_user_max_orders: 20",
                "  new_user_max_applications: 100",
                "  new_user_max_matches: 3",
                "  new_user_max_unmatched_applications_per_week: 50",
                "  swipe_min_similarity: 0.2",
                "  swipe_mix_strategy: mixed",
            ]
        ),
        encoding="utf-8",
    )


@pytest.fixture()
def client(tmp_path: Path):
    config_path = tmp_path / "settings.yaml"
    db_path = tmp_path / "skilllane-test.db"
    _write_test_config(config_path, db_path)
    os.environ["APP_CONFIG_PATH"] = str(config_path)

    from app.core.config import get_settings

    get_settings.cache_clear()

    from app.main import create_app

    with TestClient(create_app()) as test_client:
        yield test_client

    get_settings.cache_clear()
    os.environ.pop("APP_CONFIG_PATH", None)
