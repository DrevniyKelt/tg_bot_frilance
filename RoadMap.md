**Overview**
Цель: спроектировать и реализовать Telegram-бот + админ-панель для полного цикла фриланс-задачи: заказ → отклики → выбор исполнителя → завершение → отзывы, с RBAC, аудитом, модерацией и поддержкой.

**Core Constraints**
- Python 3.11+
- FastAPI для REST API
- Aiogram v3 для бота
- SQLite как основная БД
- Конфиги и тексты в JSON
- Запрещено: SQLAlchemy и Alembic
- Доступ к БД только через явный SQL (aiosqlite или sqlite3 + async-слой)
- Миграции через папку `migrations/` и таблицу `schema_migrations`

**Global Deliverables**
- Согласованные роли, permissions и политика scope
- Проектирование БД с ограничениями целостности и индексами
- Автоматический мигратор и проверка валидности JSON-конфигов
- Надежная логика “одно окно” в боте
- Полный критический сценарий от задания до отзыва
- Админ-панель с RBAC и аудитом
- Документация и инструкции по деплою

**Milestones (Target)**
- Stage 0 (Prep): 2-3 дня
- Stage 1 (Core + RBAC + Migrator): 1.5 недели
- Stage 2 (Profile + Categories/Tags + Settings): 1 неделя
- Stage 3 (Tasks): 2 недели
- Stage 4 (Bids): 1.5 недели
- Stage 5 (Deal + Reviews + Complaints): 1.5 недели
- Stage 6 (Polish + QA + Release): 1.5-2 недели

**Stage 0 — Preparation**
- [ ] Зафиксировать структуру репозитория (backend, bot, admin, migrations, config)
- [ ] Описать минимальную архитектуру: модули, границы, слои, ответственность
- [ ] Формализовать список permissions и scopes (own/any/assigned)
- [ ] Утвердить базовую матрицу ролей
- [ ] Спроектировать таблицы БД с ключами и индексами
- [ ] Определить форматы JSON-конфигов и Pydantic-схемы
- [ ] Согласовать базовые сценарии “одно окно” и список экранов
- [ ] Подготовить план миграций и naming convention
- [ ] Утвердить формат ошибок API (code/message/details)
- [ ] Определить стандарт логирования и request_id

**Stage 0 — Deliverables**
- [ ] Документ архитектуры (краткий)
- [ ] ER-модель и DDL-черновик
- [ ] Проект матрицы ролей и permissions
- [ ] Черновик API-эндпоинтов (минимальный список)

**Stage 1 — Core Backend, RBAC, Migrator, Bot Shell**
- [ ] Инициализировать FastAPI проект и базовую структуру API
- [ ] Инициализировать Aiogram v3 проект и маршрутизацию
- [ ] Реализовать единый формат ошибок API
- [ ] Ввести middleware для request_id и логирования
- [ ] Реализовать слой доступа к БД с aiosqlite
- [ ] Включить PRAGMA foreign_keys = ON при каждом подключении
- [ ] Реализовать мигратор (schema_migrations, транзакционное применение .sql)
- [ ] Создать начальные миграции 0001_init.sql и 0002_indexes.sql
- [ ] Создать ядро RBAC: permissions, roles, user_roles
- [ ] Реализовать проверку permissions на уровне API
- [ ] Ввести базовый audit_log и запись действий админки
- [ ] Реализовать “одно окно”: active_message_id, chat_id, edit fallback
- [ ] Реализовать таблицу user_state для режимов ввода

**Stage 1 — Bot UI Shell**
- [ ] Экран главного меню (inline кнопки)
- [ ] Навигация по основным разделам (заглушки)
- [ ] Базовая обработка текста через user_state

**Stage 1 — Deliverables**
- [ ] Рабочий скелет API и бота
- [ ] Авто-миграции при старте
- [ ] Минимальный RBAC с проверками
- [ ] Логи ошибок и аудит действий

**Stage 2 — Profile, Categories, Tags, Settings**
- [ ] Онбординг: приветствие, правила, выбор роли
- [ ] Создание и редактирование профиля (name/description/contacts)
- [ ] Настройки уведомлений (по типам событий)
- [ ] Настройка быстрых кнопок (reply keyboard flag)
- [ ] CRUD категорий и тегов (через API)
- [ ] Реализовать роли пользователя: Customer/Executor/оба
- [ ] Валидировать JSON-конфиги при старте
- [ ] Реализовать загрузку config/texts/roles/permissions
- [ ] Сделать API для чтения текстов и правил
- [ ] Опционально: reload конфигов без redeploy

**Stage 2 — Admin Panel Base**
- [ ] Инициализировать React админку (routing, auth, layout)
- [ ] Реализовать login и сессионную модель
- [ ] Скрытие UI по правам (server-side enforcement обязателен)
- [ ] Раздел Users: просмотр списка и карточки
- [ ] Раздел Categories/Tags: базовый CRUD

**Stage 2 — Deliverables**
- [ ] Полный профиль пользователя через бота
- [ ] Справочники категорий/тегов в админке
- [ ] Рабочие JSON-конфиги

**Stage 3 — Tasks (Core)**
- [ ] Таблица tasks с полями и индексами
- [ ] Создание задачи (черновик)
- [ ] Редактирование задачи до in_progress
- [ ] Публикация задачи (draft → published)
- [ ] Закрытие/отмена задачи
- [ ] Лента задач (только published)
- [ ] Мои задачи (owner_user_id)
- [ ] Поиск/фильтры: категория, бюджет, ключевые слова
- [ ] Опционально: премодерация (draft → on_moderation → published)
- [ ] Тесты на статусы и переходы

**Stage 3 — Bot UX**
- [ ] Экран ленты задач
- [ ] Экран карточки задачи
- [ ] Экран мои задачи и действия
- [ ] Режимы ввода: title/description/budget

**Stage 3 — Admin Panel**
- [ ] Раздел Tasks: фильтры, просмотр, смена статуса
- [ ] Действия модерации (скрыть/править/удалить)

**Stage 3 — Deliverables**
- [ ] Полный цикл задач в боте
- [ ] Модерация задач в админке

**Stage 4 — Bids (Core)**
- [ ] Таблица bids с полями и индексами
- [ ] Создание отклика с message/price/time_estimate
- [ ] Отзыв отклика (withdraw)
- [ ] Статусы sent → viewed → accepted/rejected → withdrawn
- [ ] Ограничение: один активный отклик на задачу
- [ ] Список “Мои отклики”
- [ ] Список откликов на мои задачи
- [ ] Принятие/отклонение отклика заказчиком
- [ ] Уведомления о новых откликах

**Stage 4 — Bot UX**
- [ ] Экран “Мои отклики”
- [ ] Экран откликов на задачу
- [ ] Удобные кнопки принятия/отклонения

**Stage 4 — Admin Panel**
- [ ] Раздел Bids: просмотр, фильтры
- [ ] Модерация откликов (если включено)

**Stage 4 — Deliverables**
- [ ] Полный цикл отклика
- [ ] Уведомления по откликам

**Stage 5 — Deal, Reviews, Complaints**
- [ ] Переход задачи в in_progress при принятии отклика
- [ ] Назначение assigned_executor_user_id
- [ ] Завершение задачи (done) заказчиком
- [ ] Опционально: подтверждение исполнителем
- [ ] Таблица reviews и правила доступа
- [ ] Оставление отзыва (1-5 + текст)
- [ ] Сводный рейтинг в профиле
- [ ] Таблица complaints и статусы
- [ ] Создание жалоб на задачу/отклик/пользователя
- [ ] Обработка жалоб в админке
- [ ] Уведомления по статусам жалоб

**Stage 5 — Bot UX**
- [ ] Экран завершения задачи
- [ ] Экран отзыва
- [ ] Экран жалоб/поддержки

**Stage 5 — Admin Panel**
- [ ] Раздел Complaints: очередь, статусы, комментарии
- [ ] Раздел Reviews: просмотр при необходимости

**Stage 5 — Deliverables**
- [ ] Полный цикл сделки и отзывов
- [ ] Механизм жалоб и поддержка

**Stage 6 — Polish, QA, Release**
- [ ] Полная проверка RBAC на всех endpoint
- [ ] Пагинация всех списков > 20
- [ ] Идемпотентность callback’ов
- [ ] Rate limiting на создание задач/откликов
- [ ] Санитайз входных данных
- [ ] Повторные попытки отправки уведомлений
- [ ] Тестирование критических сценариев
- [ ] Нагрузочные sanity-check
- [ ] Подготовка документации API
- [ ] Подготовка инструкции по деплою
- [ ] Финальная проверка миграций

**Cross-Cutting Workstreams**
- [ ] Обновление `config/permissions.json` как источника истины
- [ ] Генерация ролей из `config/roles.json`
- [ ] Валидатор схем JSON (Pydantic)
- [ ] Централизованная обработка ошибок
- [ ] Системные логи и аудит
- [ ] API-версионирование `/api/v1/...`
- [ ] Стратегия тестов: unit, интеграционные, e2e

**Database Schema Tasks**
- [ ] Таблица users с полями telegram_user_id, status, created_at
- [ ] Таблица profiles с user_id, display_name, description, contacts
- [ ] Таблицы roles, permissions, role_permissions, user_roles
- [ ] Таблица tasks с owner_user_id, status, budget, published_at
- [ ] Таблица bids с task_id, executor_user_id, status
- [ ] Таблица reviews с task_id, author_user_id, target_user_id
- [ ] Таблица complaints с target_type, target_id, status
- [ ] Таблица notifications с user_id, event_type, payload
- [ ] Таблица audit_log с actor_user_id, action, entity
- [ ] Таблица user_state с state_key, payload

**Indexes & Constraints Tasks**
- [ ] Индекс tasks(status, published_at)
- [ ] Индекс tasks(owner_user_id)
- [ ] Индекс bids(task_id)
- [ ] Индекс bids(executor_user_id)
- [ ] Индекс complaints(status, created_at)
- [ ] Уникальности для отклика (по задаче и исполнителю)
- [ ] Внешние ключи для всех связей

**API Endpoints (Minimum)**
- [ ] Auth/session: login/logout, me
- [ ] Users: list, get, update, ban/unban
- [ ] Profile: get/update
- [ ] Roles/Permissions: list, assign
- [ ] Tasks: create, update, publish, close, list, my
- [ ] Bids: create, withdraw, list_mine, list_by_task
- [ ] Reviews: create, list_by_user
- [ ] Complaints: create, list, resolve
- [ ] Categories/Tags: CRUD
- [ ] Audit logs: list

**Bot Screens (Minimum)**
- [ ] Главное меню
- [ ] Лента задач
- [ ] Карточка задачи
- [ ] Мои задачи
- [ ] Мои отклики
- [ ] Отклики на задачу
- [ ] Профиль
- [ ] Настройки уведомлений
- [ ] Поддержка/Жалобы

**Admin Panel Modules (Minimum)**
- [ ] Dashboard (метрики)
- [ ] Users (поиск, роли, бан)
- [ ] Tasks (модерация)
- [ ] Bids (просмотр)
- [ ] Complaints (очередь)
- [ ] Categories/Tags
- [ ] RBAC (роли и права)
- [ ] Audit log

**Quality Gates (DoD)**
- [ ] Полный критический сценарий работает end-to-end
- [ ] RBAC проверяется сервером во всех endpoints
- [ ] “Одно окно” стабильно и имеет fallback
- [ ] Миграции применяются автоматически и безопасно
- [ ] Audit-log фиксирует админские действия
- [ ] Производительность inline p95 < 1.5 сек (цель)

**Risks & Mitigations**
- [ ] Сложность “одно окно”: предусмотреть fallback и повторные попытки
- [ ] Рост SQL-логики: ввести слой репозиториев
- [ ] Согласование RBAC: зафиксировать `permissions.json` на раннем этапе
- [ ] Споры/жалобы: четкие статусы и уведомления

**Open Questions (For Future Refinement)**
- [ ] Нужна ли премодерация задач по умолчанию
- [ ] Подтверждение завершения исполнителем обязательно или нет
- [ ] Политика повторного отклика на ту же задачу
- [ ] Механизм загрузки файлов/вложений
- [ ] Отдельный admin login или только Telegram-based
