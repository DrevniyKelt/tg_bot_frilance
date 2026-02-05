# tg_bot_frilance

Monorepo layout:

- backend/  FastAPI API service
- bot/      Aiogram v3 Telegram bot
- admin/    React admin panel (frontend)
- config/   JSON configs (permissions, roles, texts, app settings)
- migrations/  SQLite schema migrations
- scripts/  helper scripts
- tests/    backend/bot tests (to be organized)

Conventions:

- Любые соединения/ресурсы, которые нужно закрывать (БД, сессии, файлы), используются только через контекстные менеджеры (`with` / `async with`).

Bootstrapping (pip + venv):

1. Create venv: `python -m venv .venv`
2. Activate: `source .venv/bin/activate`
3. Install: `pip install -r requirements.txt`
