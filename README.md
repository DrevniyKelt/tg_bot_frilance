<p align="center">
  <img src="https://img.shields.io/badge/python-3.12-blue" />
  <img src="https://img.shields.io/badge/FastAPI-009688" />
  <img src="https://img.shields.io/badge/Poetry-managed-blueviolet" />
  <img src="https://img.shields.io/badge/tests-4%20passed-brightgreen" />
  <img src="https://img.shields.io/badge/coverage-70%25-yellow" />
</p>

<p align="center">
  <h1 align="center">SkillLane</h1>
  <p align="center">
    Закрытая beta-основа для IT-фриланс биржи: сайт и Telegram Mini App
    на едином приложении <b>FastAPI + Jinja2</b>.
  </p>
</p>

---

## 🚀 О проекте

**SkillLane** — это закрытая beta-основа для IT-фриланс биржи, построенная по материалам из `roadmap1.md`.

Проект объединяет:

- веб-сайт
- Telegram Mini App
- единый backend на `FastAPI`

Цель текущей версии — собрать рабочее MVP-ядро с базовой логикой заказов, ролей, стека технологий и механикой swipe-подбора.

---

## ✅ Что уже реализовано

- архитектурный каркас: `web / api / core / db / services`
- Telegram auth endpoint + dev demo-login
- профиль пользователя
- переключение ролей
- каталог стека и синонимов
- создание заказов
- листинг заказов
- фильтры и поиск по стеку
- swipe / Tinder-режим
- каталог тарифов и доппакетов
- расчёт комиссии `0% / 1%`
- seed-данные
- OpenAPI документация
- минимальные тесты и CI

---

## 🛠 Технологии

- Python 3.12
- FastAPI
- Jinja2
- Poetry
- Pytest
- OpenAPI

---

## 📦 Установка и локальный запуск

Установка зависимостей:

```bash
poetry install --with dev