# SkillLane

Закрытая beta-основа для IT-фриланс биржи из `roadmap1.md`: сайт и Telegram Mini App на одном `FastAPI + Jinja2` приложении.

Что уже реализовано:

* архитектурный каркас `web/api/core/db/services`
* Telegram auth endpoint + dev demo-login
* профиль пользователя, переключение ролей, каталог стека и синонимов
* создание заказов, листинг, фильтры, поиск по стеку и swipe-режим
* тарифы и доппакеты в каталоге, расчёт комиссии 0% / 1%
* seed-данные, OpenAPI, минимальные тесты и CI

Локальный запуск:

```bash
python3 -m venv .venv-local
source .venv-local/bin/activate
pip install -e ".[dev]"
uvicorn app.main:create_app --factory --reload
```

По умолчанию настройки читаются из `data/config/settings.yaml`.

Полезные URL:

* `/` лендинг и точка входа
* `/catalog` каталог заказов
* `/orders/new` создание заказа
* `/profile` профиль и стек
* `/swipe` swipe/Tinder режим
* `/docs` OpenAPI
* `/auth/demo/1` быстрая dev-авторизация
