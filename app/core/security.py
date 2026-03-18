from __future__ import annotations

import hashlib
import hmac
import json
from urllib.parse import parse_qsl


def verify_telegram_init_data(init_data: str, bot_token: str) -> dict:
    if not bot_token:
        raise ValueError("Telegram bot token is not configured.")

    items = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = items.pop("hash", None)
    if not received_hash:
        raise ValueError("Telegram initData must include hash.")

    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(items.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(calculated_hash, received_hash):
        raise ValueError("Telegram initData hash mismatch.")

    user_payload = items.get("user")
    if not user_payload:
        raise ValueError("Telegram initData must include user payload.")
    return json.loads(user_payload)
