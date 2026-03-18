from __future__ import annotations

from decimal import Decimal


def test_home_page_renders(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "SkillLane" in response.text
    assert "RoadMap" in response.text


def test_stack_synonym_search_normalizes_filters(client):
    response = client.get("/api/orders", params={"stack": "k8s"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["normalized_stack_filters"] == ["kubernetes"]
    assert payload["total"] >= 1


def test_create_order_calculates_fee_on_top(client):
    response = client.post(
        "/api/orders",
        json={
            "title": "FastAPI analytics dashboard for beta users",
            "category": "Backend",
            "summary": "Нужно собрать личный кабинет, фильтры и экспорт в CSV.",
            "description": "Ищем разработчика, который поднимет FastAPI слой, сделает Jinja страницы и подготовит выдачу под Mini App интерфейс.",
            "budget_type": "fixed",
            "currency": "RUB",
            "stack_mode": "specific",
            "budget_amount": "20000.00",
            "stack_slugs": ["python", "fastapi"],
            "auto_filters": {"min_rating": 4.5, "priority": "balanced"},
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert Decimal(str(payload["executor_amount"])) == Decimal("20000.00")
    assert Decimal(str(payload["client_total_amount"])) == Decimal("20200.00")


def test_swipe_returns_cards(client):
    response = client.get("/api/orders/swipe", params={"target": "orders"})

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) >= 1
    assert payload[0]["entity_type"] == "order"
    assert "similarity" in payload[0]
