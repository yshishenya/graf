# Implementation Plan: Измерение поисковых входов

**Branch**: `codex/289-organic-measurement` | **Date**: 2026-10-16 | **Spec**: [spec.md](spec.md)

## Summary

Повторно использовать существующий обезличенный счётчик для четырёх пропущенных публичных входов. Необязательные провайдеры, cookie и продуктовая идентификация сохраняют прежние границы. Сначала актуальный аудит и план на 90 дней, затем четыре входа и проверка на изолированной БД.

## Technical Context

- Language/Version: существующий Python 3.13, FastAPI/Jinja/SQLAlchemy; новых зависимостей нет.
- Storage: существующая anonymous_page_aggregate_buckets; без миграции, очереди или профиля.
- Testing: pytest, существующий disposable PostgreSQL runner и public/consent регрессии.
- Risk / Validation Lane: high-risk-product — приватность; полный Spec Kit с clarify, независимым checklist, analyze, issues, implement и converge.
- Release Gate: no deploy в локальном срезе. Коммит после явного разрешения; PR exact-SHA governance-fast/macos-pr/pr-metadata; frozen release-full, backup/restore/rollback, cd-remote.sh --dry-run и одобренный выпуск.
- Target: Linux web-service; desktop не запускается и не изменяется.
- Performance/constraints: один существующий safe upsert на запрос, без внешней сети; действующие таймауты/отказ наследуются. Ровно четыре пути, без middleware всех страниц.

## Constitution Check

До исследования: PASS. Capture, доступ, AI и deletion не затронуты. Только существующий обезличенный уровень 1 с действующим legal gate; основания профилирования и внешних провайдеров не предполагаются. Readiness flags не меняются.

После проектирования: PASS. Отдельный PUBLIC_ANONYMOUS_CONTENT_SURFACES включается только в PUBLIC_PAGE_SURFACES уровня 1. Не включать в PUBLIC_CONTENT_SURFACES: он также питает необязательную аналитику. Существующий public_page_response получает явный anonymous_only; текущий URL проходит normalize_public_campaign_attribution, без cookie, L2 и providers. Правовой шлюз и безопасная запись прежние. Ревью требований выполняет отдельный агент.

## Validation Plan

Четыре маршрута на настоящем disposable PostgreSQL: текущий путь, sanitization, referer/traffic_class, два запроса, отсутствие L2/cookie, неизменность существующего cookie, kill switch, отключение уровня/отзыв основания и DB unavailable. Обновить границу anonymous Zoom и unit-проверку соответствия инвентарей четырём новым путям. Соседние public/consent/anonymous aggregate тесты, Ruff, governance, fragment и diff checks. HTML/templates/static/sitemap не изменяются.

## Project Structure

- public/content.py: отдельный каталог четырёх поверхностей.
- product_analytics/anonymous_aggregate.py: включение только уровня 1.
- public/web.py: прежний response helper и два обработчика.
- tests/contract/test_public_organic_measurement.py и test_public_zoom_recording_guide.py: границы.
- docs/growth/: аудит и план. changes/unreleased/F289.yaml: результат.

Все пути к коду относительно apps/server/src/twobrain_rec_server; тесты относительно apps/server.

## Legacy Impact

Legacy не удаляется. Меняется только прежний запрет уровня 1 на четырёх входах F281/F282. Историческое evidence не переписывается. F273/F096 не закрываются. Новые статьи, schema и redirects — последующие срезы.
