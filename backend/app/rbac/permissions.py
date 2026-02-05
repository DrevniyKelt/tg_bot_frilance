from __future__ import annotations

from app.core.config import load_configs


_configs = load_configs()
PERMISSIONS = set(_configs["permissions"].permissions)
ROLES = _configs["roles"].roles
