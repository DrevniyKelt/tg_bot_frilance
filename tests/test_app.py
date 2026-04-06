from __future__ import annotations

from decimal import Decimal


def test_home_page_renders(client):
    response = client.get("/", follow_redirects=True)

    assert response.status_code == 200
    assert "SkillLane" in response.text
    assert "Swipe" in response.text


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


def test_apply_to_order_and_select_executor(client):
    client.get("/auth/demo/2")

    apply_response = client.post(
        "/api/orders/telegram-mini-app-fastapi-launch/apply",
        json={
            "cover_letter": "Готов собрать интерфейс, API и адаптацию под Mini App.",
            "proposed_amount": "118000.00",
            "delivery_days": 18,
            "attachment_name": "case-study.pdf",
        },
    )

    assert apply_response.status_code == 201
    application = apply_response.json()
    assert application["status"] == "pending"
    assert application["executor_name"] == "Lena Morozova"

    client.get("/auth/demo/1")

    list_response = client.get("/api/orders/telegram-mini-app-fastapi-launch/applications")
    assert list_response.status_code == 200
    applications = list_response.json()
    assert len(applications) == 1
    assert applications[0]["id"] == application["id"]

    select_response = client.post(
        "/api/orders/telegram-mini-app-fastapi-launch/select_executor",
        json={"application_ids": [application["id"]]},
    )
    assert select_response.status_code == 200
    selected = select_response.json()
    assert selected[0]["status"] == "selected"

    order_response = client.get("/api/orders/telegram-mini-app-fastapi-launch")
    assert order_response.status_code == 200
    assert order_response.json()["status"] == "matched"


def test_quick_apply_uses_executor_profile(client):
    client.get("/auth/demo/3")

    response = client.post(
        "/api/orders/figma-to-jinja-design-system/quick_apply",
        json={},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["is_quick"] is True
    assert payload["executor_name"] == "Ivan Petrov"
    assert payload["cover_letter"] != ""


def test_chat_is_created_after_executor_selection_and_accepts_messages(client):
    client.get("/auth/demo/2")
    apply_response = client.post(
        "/api/orders/telegram-mini-app-fastapi-launch/apply",
        json={"cover_letter": "Могу закрыть backend и web слой.", "delivery_days": 12},
    )
    assert apply_response.status_code == 201
    application_id = apply_response.json()["id"]

    client.get("/auth/demo/1")
    select_response = client.post(
        "/api/orders/telegram-mini-app-fastapi-launch/select_executor",
        json={"application_ids": [application_id]},
    )
    assert select_response.status_code == 200

    chats_response = client.get("/api/chats")
    assert chats_response.status_code == 200
    chats = chats_response.json()
    assert len(chats) == 1
    chat_id = chats[0]["id"]
    assert chats[0]["order_slug"] == "telegram-mini-app-fastapi-launch"

    message_response = client.post(
        f"/api/chats/{chat_id}/messages",
        json={"body": "Подтверждаю старт работ, давай синхронизируем scope."},
    )
    assert message_response.status_code == 201
    assert message_response.json()["author_name"] == "Mihai Demo"

    thread_response = client.get(f"/api/chats/{chat_id}")
    assert thread_response.status_code == 200
    thread = thread_response.json()
    assert len(thread["messages"]) == 1
    assert thread["messages"][0]["body"].startswith("Подтверждаю старт")

    client.get("/auth/demo/3")
    forbidden_response = client.get(f"/api/chats/{chat_id}")
    assert forbidden_response.status_code == 403


def test_wallet_topup_and_escrow_flow(client):
    client.get("/auth/demo/2")
    apply_response = client.post(
        "/api/orders/telegram-mini-app-fastapi-launch/apply",
        json={"cover_letter": "Готов взять заказ в работу", "delivery_days": 10},
    )
    application_id = apply_response.json()["id"]

    client.get("/auth/demo/1")
    select_response = client.post(
        "/api/orders/telegram-mini-app-fastapi-launch/select_executor",
        json={"application_ids": [application_id]},
    )
    assert select_response.status_code == 200

    topup_response = client.post(
        "/api/wallet/topup",
        json={"amount": "100000.00", "currency": "RUB", "note": "extra mock funding"},
    )
    assert topup_response.status_code == 201
    assert topup_response.json()["kind"] == "topup"

    fund_response = client.post("/api/orders/telegram-mini-app-fastapi-launch/escrow/fund")
    assert fund_response.status_code == 201
    assert fund_response.json()["kind"] == "escrow_hold"

    start_response = client.post("/api/orders/telegram-mini-app-fastapi-launch/start")
    assert start_response.status_code == 200
    assert start_response.json()["status"] == "in_progress"

    client.get("/auth/demo/2")
    executor_confirm = client.post("/api/orders/telegram-mini-app-fastapi-launch/confirm")
    assert executor_confirm.status_code == 200
    assert executor_confirm.json()["executor_completion_confirmed"] is True
    assert executor_confirm.json()["status"] == "in_progress"

    client.get("/auth/demo/1")
    client_confirm = client.post("/api/orders/telegram-mini-app-fastapi-launch/confirm")
    assert client_confirm.status_code == 200

    order_response = client.get("/api/orders/telegram-mini-app-fastapi-launch")
    assert order_response.status_code == 200
    assert order_response.json()["escrow_status"] == "released"
    assert order_response.json()["client_completion_confirmed"] is True
    assert order_response.json()["executor_completion_confirmed"] is True

    order_after_release = client.get("/api/orders/telegram-mini-app-fastapi-launch")
    assert order_after_release.status_code == 200
    assert order_after_release.json()["status"] == "completed"
    assert order_after_release.json()["escrow_status"] == "released"

    client.get("/auth/demo/2")
    executor_transactions = client.get("/api/wallet/transactions")
    assert executor_transactions.status_code == 200
    txs = executor_transactions.json()
    assert any(tx["kind"] == "escrow_release" for tx in txs)


def test_completed_order_accepts_bidirectional_reviews_and_updates_ratings(client):
    client.get("/auth/demo/2")
    apply_response = client.post(
        "/api/orders/telegram-mini-app-fastapi-launch/apply",
        json={"cover_letter": "Сделаю backend, swipe и чат", "delivery_days": 11},
    )
    application_id = apply_response.json()["id"]

    client.get("/auth/demo/1")
    client.post(
        "/api/wallet/topup",
        json={"amount": "100000.00", "currency": "RUB", "note": "fund for review flow"},
    )
    client.post(
        "/api/orders/telegram-mini-app-fastapi-launch/select_executor",
        json={"application_ids": [application_id]},
    )
    client.post("/api/orders/telegram-mini-app-fastapi-launch/escrow/fund")
    client.post("/api/orders/telegram-mini-app-fastapi-launch/start")

    client.get("/auth/demo/2")
    client.post("/api/orders/telegram-mini-app-fastapi-launch/confirm")

    client.get("/auth/demo/1")
    client.post("/api/orders/telegram-mini-app-fastapi-launch/confirm")

    review_exec = client.post(
        "/api/orders/telegram-mini-app-fastapi-launch/reviews",
        json={"reviewee_id": 2, "score": 5, "text": "Сильный исполнитель, закрыл задачу без шума."},
    )
    assert review_exec.status_code == 201
    assert review_exec.json()["role"] == "client_to_executor"

    duplicate = client.post(
        "/api/orders/telegram-mini-app-fastapi-launch/reviews",
        json={"reviewee_id": 2, "score": 4, "text": "Повторный отзыв"},
    )
    assert duplicate.status_code == 409

    client.get("/auth/demo/2")
    review_client = client.post(
        "/api/orders/telegram-mini-app-fastapi-launch/reviews",
        json={"reviewee_id": 1, "score": 4, "text": "Коммуникация по делу, оплата без задержек."},
    )
    assert review_client.status_code == 201
    assert review_client.json()["role"] == "executor_to_client"

    reviews = client.get("/api/orders/telegram-mini-app-fastapi-launch/reviews")
    assert reviews.status_code == 200
    assert len(reviews.json()) == 2

    me_executor = client.get("/api/me")
    assert me_executor.status_code == 200
    assert me_executor.json()["avg_executor_rating"] == "5.00"

    client.get("/auth/demo/1")
    me_client = client.get("/api/me")
    assert me_client.status_code == 200
    assert me_client.json()["avg_client_rating"] == "4.00"


def test_ads_and_moderation_admin_flow(client):
    ad_response = client.get("/api/ads/placement/catalog_inline")
    assert ad_response.status_code == 200
    assert ad_response.json()["code"] == "figma-audit-slot"

    impression_response = client.post("/api/ads/impression", json={"campaign_code": "figma-audit-slot"})
    assert impression_response.status_code == 200
    assert impression_response.json()["impressions_count"] >= 1

    click_response = client.post("/api/ads/click", json={"campaign_code": "figma-audit-slot"})
    assert click_response.status_code == 200
    assert click_response.json()["clicks_count"] >= 1

    client.get("/auth/demo/2")
    report_response = client.post(
        "/api/orders/telegram-mini-app-fastapi-launch/report",
        json={
            "target_type": "user",
            "target_user_id": 1,
            "reason": "Пользователь требует вынести обсуждение оплаты за пределы сделки.",
        },
    )
    assert report_response.status_code == 201
    ticket_id = report_response.json()["id"]

    client.get("/auth/demo/1")
    tickets_response = client.get("/api/admin/moderation")
    assert tickets_response.status_code == 200
    assert any(ticket["id"] == ticket_id for ticket in tickets_response.json())

    resolve_response = client.post(f"/api/admin/moderation/{ticket_id}/resolve")
    assert resolve_response.status_code == 200
    assert resolve_response.json()["status"] == "resolved"

    hide_response = client.post("/api/admin/orders/figma-to-jinja-design-system/hide")
    assert hide_response.status_code == 200

    banned_order = client.get("/api/orders/figma-to-jinja-design-system")
    assert banned_order.status_code == 200
    assert banned_order.json()["status"] == "banned"

    ban_user_response = client.post("/api/admin/users/3/ban")
    assert ban_user_response.status_code == 200

    client.get("/auth/demo/3")
    banned_apply = client.post(
        "/api/orders/telegram-mini-app-fastapi-launch/apply",
        json={"cover_letter": "Попробую откликнуться после бана."},
    )
    assert banned_apply.status_code == 403


def test_my_orders_page_supports_client_and_executor_modes(client):
    client.get("/auth/demo/2")
    client.post(
        "/api/orders/telegram-mini-app-fastapi-launch/apply",
        json={"cover_letter": "Отклик для личного кабинета."},
    )

    executor_page = client.get("/me/orders?mode=executor")
    assert executor_page.status_code == 200
    assert "Мои заказы" in executor_page.text
    assert "Telegram Mini App" in executor_page.text

    client.get("/auth/demo/1")
    client_page = client.get("/me/orders?mode=client")
    assert client_page.status_code == 200
    assert "Мои заказы" in client_page.text
    assert "UI-kit в стиле Ozon" in client_page.text
def test_swipe_match_executor_creates_chat_for_demo_client(client):
    client.get("/auth/demo/1")
    order_catalog = client.get("/api/orders")
    assert order_catalog.status_code == 200
    source_order = next(item for item in order_catalog.json()["items"] if item["slug"] == "react-onboarding-flow-rebuild")

    swipe_response = client.get(
        "/api/orders/swipe",
        params={"target": "executors", "source_order_id": source_order["id"]},
    )
    assert swipe_response.status_code == 200
    executors = swipe_response.json()
    assert len(executors) >= 1
    match_card = next(card for card in executors if card["selected_you"] is True and card["match_ready"] is False)

    match_response = client.post(
        f"/swipe/decision/executors/{match_card['id']}",
        data={"direction": "accept", "source_order_id": str(source_order["id"])},
    )
    assert match_response.status_code == 200
    payload = match_response.json()
    assert payload["matched"] is True
    assert payload["chat_url"].startswith("/chats/")

    chats_response = client.get("/api/chats")
    assert chats_response.status_code == 200
    assert any(chat["id"] == payload["chat_id"] for chat in chats_response.json())


def test_swipe_order_cards_show_inverse_state_for_executor(client):
    client.get("/auth/demo/6")

    swipe_response = client.get("/api/orders/swipe", params={"target": "orders"})
    assert swipe_response.status_code == 200
    orders = swipe_response.json()
    assert len(orders) >= 1
    card = next(card for card in orders if card["status_label"] in {"Выбрали тебя", "У вас мэтч", "Liked you", "You matched"})
    assert card["entity_type"] == "order"


def test_test_mode_toggle_disables_and_enables_demo_login(client):
    enabled_home = client.get("/", follow_redirects=True)
    assert enabled_home.status_code == 200
    assert "/logout" in enabled_home.text

    disable = client.get("/test-mode/toggle", follow_redirects=True)
    assert disable.status_code == 200
    assert "/logout" not in disable.text
    assert "/auth/demo/1" in disable.text

    enable = client.get("/test-mode/toggle", follow_redirects=True)
    assert enable.status_code == 200
    assert "/logout" in enable.text


def test_guest_swipe_and_community_show_registration_gate(client):
    client.get("/test-mode/toggle", follow_redirects=True)

    swipe = client.get("/swipe")
    assert swipe.status_code == 200
    assert "Зарегистрируйтесь для начала использования" in swipe.text

    community = client.get("/community?view=chats")
    assert community.status_code == 200
    assert "Зарегистрируйтесь для начала использования" in community.text


def test_community_forums_page_renders_and_creates_topic(client):
    client.get("/auth/demo/2")

    community = client.get("/community?view=forums")
    assert community.status_code == 200
    assert "Чаты и форумы" in community.text

    create_topic = client.post(
        "/community/forums/topics",
        data={
            "title": "Как оформлять портфолио в карточке",
            "body": "Хочу собрать практические советы по тому, какие кейсы лучше показывать прямо в карточке исполнителя.",
        },
        follow_redirects=True,
    )
    assert create_topic.status_code == 200
    assert "Как оформлять портфолио в карточке" in create_topic.text
