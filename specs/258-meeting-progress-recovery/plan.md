# Implementation Plan: Понятная готовность встречи

**Branch**: `codex/258-meeting-progress-recovery` | **Date**: 2026-09-08 | **Spec**: [spec.md](spec.md)

## Summary

Исправить существующие проекции и их потребителей. Аудио доступно до итогов; текущая попытка итогов видна в processing/sync/HTML; браузер автоматически получает опубликованный результат. Mac использует свою очередь и проверенные серверные метаданные для одной доставки, не события WKWebView.

## Technical Context

- Language/Version: Python >=3.13, Swift 6, обычный JavaScript.
- Primary Dependencies: существующие SQLAlchemy/FastAPI, SwiftUI/AppKit/UserNotifications, Temporal; новых библиотек нет.
- Storage: существующие PostgreSQL summary slots/attempts, локальная Codable очередь и UserDefaults.
- Testing: pytest с изолированным PostgreSQL, Node поведенческие тесты, Swift Tests, единственный GRAF Dev.
- Risk / Validation Lane: high-risk-feature — пользовательский путь, capture-adjacent UX, доступ к аудио, DB permissions.
- Release Gate: no deploy, no release; коммиты/push/PR разрешены пользователем 2026-09-08, merge отдельно.
- Target Platform: macOS Apple Silicon, web и WKWebView, Linux backend.
- Performance Goals: активный экран <=15 секунд, ограниченная частота фонового опроса, один запрос на поверхность; UI не блокирует capture.
- Constraints: без изменения raw capture, модели/промпта, retention и production; сохранить pause microphone, Stop, countdown и F255 menu.
- Scale/Scope: текущая встреча, существующий список и локальная очередь; без глобального лидера устройств/новой истории.

## Constitution Check

До исследования и после проектирования: I/II — capture pipeline неизменён, отклик только после подтверждения; III — только метаданные, генерация/egress не меняются; IV — deletion/access/source fences сохраняются; V — нет публичных артефактов; VI — clarify, reviewer checklist, tasks/analyze/issues до реализации; VII — только наблюдаемый Krisp UX, собственный код и системные символы. Нарушений нет. Readiness на Mac заменяет нижестоящий F249 запрет, не конституцию.

## Phase 0 — Research

[research.md](research.md): инцидент исследован read-only, F249 дополнительно изучен отдельным research agent согласно speckit-plan. Решения без содержимого встречи.

## Phase 1 — Design

[data-model.md](data-model.md), [contracts/progress.md](contracts/progress.md). Переиспользовать summary slot/attempt state. Для трёх потребителей допустима одна общая проекция outcomes/progress.py, не новый workflow. Auth context только из проверенного native запроса; offline — ранее подтверждённый контекст в той же auth epoch. Старые unknown sessions не присваивать.

## Validation Plan

[quickstart.md](quickstart.md): регрессии воспроизводят ошибки, затем исправления; focused PostgreSQL/Node/Swift, GRAF Dev после проверенного авторизованного коммита, governance-fast exact SHA в PR. Full CI отдельно на общем release candidate. Недоступная аппаратная проверка остаётся открытой. Legacy Impact: untouched — active paths; optional Codable поля читают прежнюю очередь.

## Project Structure

- `apps/server/src/twobrain_rec_server/cabinet/{egress.py,queries.py,rendering.py,view_models.py,static/cabinet/cabinet.js,templates/cabinet/pages/meeting_detail_content.html}`
- `apps/server/src/twobrain_rec_server/{processing/status.py,outcomes/progress.py,ingest/desktop_sync.py,api/schemas.py,normalization/worker.py}`
- `apps/server/scripts/bootstrap_runtime_database_roles.py` и role tests при необходимости grant.
- `apps/macos/Shared/Sources/Models/AudioModelCore.swift`, `RecApp/Sources/{Notifications,Upload,Calendar,Cabinet}`, `RecApp/App/TwoBrainRecApp.swift`.
- Существующие server contract/integration/unit tests, `apps/macos/Shared/Tests/`.

## Complexity Tracking

Новых очередей, content tables, библиотек и framework нет. Additive readiness metadata в существующем sync нужны для закрытого WKWebView и не меняют владельца обработки.
