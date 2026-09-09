# Implementation Plan: Единые настройки GRAF

**Branch**: `codex/260-unified-settings` · **Date**: 2026-09-09 · **Spec**: [spec.md](spec.md)
**Lane**: High-risk product / reference-fidelity UX.
**Stage**: Реализация в рабочем дереве; принятые требования и макет. Локальные профильные проверки пройдены, установленный Dev и проверки точного SHA ожидаются.

## Summary
Использовать текущие настройки кабинета как единственный обычный экран. Упростить композицию по наблюдаемому Krisp, встроить локальные уведомления через небольшой защищённый мост WebKit, сохранить нативное окно только как резерв без сервера. Движок записи, хранение и политики сохраняются.

## Technical Context
Python/FastAPI/Jinja, cabinet.css/cabinet.js; SwiftUI/AppKit/WebKit. Владельцы: MeetingDetectionSettingsStore, EmbeddedCabinetRecordingSettingsBridge, DesktopNotificationPresenter. Прежний локальный файл правил, UserDefaults по владельцу для уведомлений, серверные account preferences. Без миграций, новых фреймворков и зависимостей. Риски: WebView → локальное состояние, смена аккаунта, сохранение доступности без сервера и accessibility.

## Constitution Check
До исследования и после проектирования: сохранены §I/II полный реестр, три правила, 8 секунд, локальное владение, ручной старт/Stop и индикатор. §III/IV: без содержимого встреч, новых внешних запросов и изменения удаления. §V: без изменения упаковки/подписи. §VI: clarify/checklist/analyze/issue sync до реализации. §VII: наблюдаемый Krisp, независимый код, документированные отклонения. Принятие reviewer остаётся отдельным gate.

## Project Structure
Артефакты: specs/260-unified-settings/. Код: существующие apps/server/src/twobrain_rec_server/cabinet/ и apps/macos/RecApp/. Единственный новый продуктовый модуль: apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetNotificationSettingsBridge.swift.

## Phase 0 — Research
reference-audit.md — наблюдения Krisp/причины дефектов; research.md — технические решения и отдельное исследование границы владельца. design-handoff.md — композиция и поведение; prototype.html — синтетическая демонстрация.

## Phase 1 — Design
Создать data-model.md, contracts/settings.md, quickstart.md, reviewer checklists и tasks.md. Clarify в spec не содержит нерешённых продуктовых вопросов. Принятие итогового макета и checklist предшествует реализации.

## Implementation Approach
1. Порядок/группы в view_models.py, group_label в components/sections.html; /settings и /desktop/settings ведут в аккаунт. Убрать обзор карточками и дубль уведомлений в аккаунте; операции аккаунта/оплаты/календаря сохранить.
2. Стили ограничить settings: небольшой заголовок, две колонки строки, перенос узкого вида. Удалить только заменяемые мёртвые стили.
3. Recording: сохранить текущий bridge; резервный SwiftUI view получает имя + системный Picker и mixed state. Убрать вложенный sidebar из самого view.
4. Notifications: новый bridge использует presenter, одно поле за раз и generation аккаунта. Presenter возвращает явный успех; scheduling/privacy cleanup/тишина во время записи сохраняются.
5. Подключение/снятие bridge в EmbeddedCabinetWebView на тех же lifecycle этапах, что recording; дополнительно auth-change invalidation. JS — confirmed snapshot и защита от старых ответов.
6. Все готовые native входы и старые внутренние URL — в основной экран. Только недоступный кабинет открывает один существующий graf-settings-window с sidebar вместо NSTabViewController.
7. Простые переключатели автосохраняются. Серверные письма/подсказки сохраняют CSRF/version/conflict и обычный POST без JS. Профиль, безопасность и календарные подключения сохраняют явное подтверждение.

## Validation & Release
Checklist reviewer, analyze CRITICAL 0/HIGH 0, canonical issue sync. Затем quickstart, Ponytail review сложного diff, convergence, scoped tests и требуемый fast/governance-fast точного SHA по release-and-validation.md. Full CI, merge/production/public release не относятся к подготовке. Установка Dev требует чистого авторизованного коммита и harness; до этого допустимы тесты без установки.

## Complexity Tracking
Не нужны новая система настроек, серверное хранение Mac-правил, schema renderer, универсальный bridge, отдельная копия GRAF или кешированный автономный web-shell. Существующий native резерв сохраняет работу без кабинета.
