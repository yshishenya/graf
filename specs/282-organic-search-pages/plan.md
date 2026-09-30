# Implementation Plan: Поисковые страницы ГРАФ

**Branch**: `282-organic-search-pages` | **Date**: 2026-09-30 | **Spec**: [spec.md](spec.md)
**Input**: specs/282-organic-search-pages/spec.md

## Summary

Три самостоятельные страницы через существующие FastAPI/Jinja2 и локальные активы. Главная получает только три ссылки в подвале. Новых зависимостей, аналитических поверхностей и изменений возможностей продукта нет.

## Technical Context

**Language/Version**: Python 3.13+, HTML/CSS.
**Primary Dependencies**: существующие FastAPI, Jinja2, pytest, Ruff.
**Storage**: новый контент в шаблоне; нет новой БД или миграций.
**Testing**: pytest с существующим TestClient, сравнение главной с исходным шаблоном, браузер на 320/390/768/1440.
**Risk / Validation Lane**: significant-feature; новые публичные страницы и маршруты требуют полного Spec Kit, clarify выполнен; не меняется обработка данных или запись.
**Release Gate**: no deploy в текущей подготовке. После разрешённого коммита — exact-SHA governance-fast, macos-pr, pr-metadata; выпуск отдельно требует frozen release-full, dry-run и разрешения оператора.
**Target Platform**: существующий веб-сервер; страницы без привязки заголовков к ОС.
**Project Type**: существующий web-service.
**Performance Goals**: 0 новых внешних запросов, 0 новых скриптов, максимум 1 локальный CSS на новых страницах; main не меняет набор активов.
**Constraints**: сохранение главной, доступность без JS, правдивые платформы, отсутствие новых счётчиков.
**Scale/Scope**: три фиксированных пути; один шаблон с тремя отдельными содержательными блоками, один локальный CSS.

## Constitution Check

До исследования PASS: не затрагиваются capture/auth/storage/AI, не добавляются внешние зависимости, секреты/частные материалы не используются; установка Windows не обещается. Используются собственные продуктовые изображения и локальный шрифт Onest с OFL.txt. Достоверность marketing и accessibility обязательны.
После проектирования PASS: повторно подтверждены те же границы. Reviewer-owned ux-search.md проверяется отдельным агентом перед реализацией; главный агент не меняет его отметки. Встроенный requirements.md проверен на стадии specify/clarify.

## Validation Plan

Quickstart: HTTP/метаданные/canonical/sitemap/404/безопасный query; точное сравнение исходного landing.html за вычетом трёх ссылок; подтверждение неизменности CSS/JS. Проверка новых страниц без JS, видимости фокуса, отсутствия переполнения и первого экрана главной на четырёх ширинах. Существующие тесты public landing/analytics/attribution — регрессия. Ruff, diff --check, Spec Kit governance и fragment validator. Локальная проверка не заменяет будущие exact-SHA GitHub checks. Нет запуска/сборки desktop app.

## Project Structure

Документация: spec.md, plan.md, research.md, data-model.md, contracts/public-search-pages.md, quickstart.md, tasks.md, checklists/ux-search.md, evidence/ в текущем каталоге фичи.
Код: apps/server/src/twobrain_rec_server/public/web.py; templates/public/search_guide.html; templates/public/landing.html (только footer links); static/public/search-guide.css.
Тест: apps/server/tests/contract/test_public_search_pages.py. Одноразовый acceptance check сохранения главной: specs/282-organic-search-pages/scripts/check_landing_preserved.py; не включается в постоянную CI-выборку. Фрагмент: changes/unreleased/F282.yaml.

## Delivery and rollback

Перед правками сохранить hashes исходных landing.html/CSS/JS и публичные метаданные в evidence/baseline.md. Общие handlers/templates/analytics untouched, маршруты новых страниц вызывают public_page_response без analytics_path override и без _analytics.html. Неизвестные пути не перехватываются catch-all. Постоянные title/description выбираются из фиксированного набора маршрутов, autoescape сохраняется. sitemap расширяется ровно тремя путями.
Откат релизом предшествующей версии возвращает маршруты, footer links и sitemap; миграций нет. Не сбрасывать чужие изменения.
