import json
from pathlib import Path

from pydantic import BaseModel


BASE_DIR = Path(__file__).resolve().parents[3]
CONFIG_DIR = BASE_DIR / "config"


class AppConfig(BaseModel):
    feature_flags: dict = {}
    limits: dict = {}


class TextsConfig(BaseModel):
    rules: str = ""
    faq: str = ""
    templates: dict = {}


class PermissionsConfig(BaseModel):
    permissions: list[str]


class RolesConfig(BaseModel):
    roles: dict[str, list[str]]


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_configs() -> dict:
    app_cfg = AppConfig(**load_json(CONFIG_DIR / "app.json"))
    texts_cfg = TextsConfig(**load_json(CONFIG_DIR / "texts.json"))
    perms_cfg = PermissionsConfig(**load_json(CONFIG_DIR / "permissions.json"))
    roles_cfg = RolesConfig(**load_json(CONFIG_DIR / "roles.json"))

    return {
        "app": app_cfg,
        "texts": texts_cfg,
        "permissions": perms_cfg,
        "roles": roles_cfg,
    }
