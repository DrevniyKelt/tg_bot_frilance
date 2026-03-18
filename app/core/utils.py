from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from slugify import slugify


def csv_to_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    seen: set[str] = set()
    values: list[str] = []
    for item in raw.split(","):
        normalized = slugify(item.strip(), lowercase=True, separator="-")
        if normalized and normalized not in seen:
            seen.add(normalized)
            values.append(normalized)
    return values


def money_to_decimal(value: int | float | Decimal) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def format_money(value: int | float | Decimal) -> str:
    amount = money_to_decimal(value)
    return f"{amount:,.2f}".replace(",", " ").replace(".00", "")


def make_slug(value: str) -> str:
    return slugify(value, lowercase=True, separator="-")
