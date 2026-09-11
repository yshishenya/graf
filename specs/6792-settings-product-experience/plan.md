# Implementation Plan: Понятные настройки GRAF

**Branch**: `codex/6792-settings-product-experience` | **Date**: 2026-09-11 | **Spec**: [spec.md](spec.md)
**Input**: Все семь разделов и связанные пути пользователя.

## Summary
Сохранить существующие маршруты и обработчики, переработать представление и русские тексты. Освободить центральную область macOS от раскрытой панели записи при входе в настройки, сохранив доступные Start/Stop и внимание к активной записи. Переиспользовать settings-section, нативные details и действующий механизм черновиков. Перед кодом — интерактивный макет и независимая проверка требований.

## Technical Context
- Language/Version: Python проекта, Jinja, CSS, JavaScript; Swift/SwiftUI/AppKit.
- Primary Dependencies: существующие FastAPI/Jinja и нативный WebKit; новых зависимостей нет.
- Storage: существующие значения аккаунта и локальные preferences; миграций нет.
- Testing: pytest, node:test, Swift Testing/XCTest; ручная проверка GRAF Dev.
- Risk / Validation Lane: high-risk-feature — общая навигация, доступность, формы входа, запись и оплата.
- Release Gate: no deploy; governance-fast на точном SHA перед merge, release-full и отдельное разрешение перед релизом.
- Target Platform: веб и macOS embedded WKWebView.
- Project Type: существующее приложение.
- Performance Goals: переключение разделов и поиск сохраняют текущий способ работы; не вводить новые запросы, библиотеки и внешние ресурсы.
- Constraints: все существующие form actions/CSRF/локальные bridge guards; полный список приложений; «Спрашивать» с 8 секундами; visible capture и Stop.
- Scale/Scope: семь категорий, вложенные календарные/аккаунтные/форматные формы и финансовые состояния.

## Constitution Check
До исследования: PASS — запрос разрешает изменение представления, сохраняет capture/consent/auth/egress/финансовые границы. После проектирования: PASS — нет новых протоколов, схем, внешних сервисов, маршрутов записи. Independent code/GRAF-owned assets; максимальная близость наблюдаемому Krisp, отклонения только для доступности и реальных возможностей GRAF. Legacy Impact: untouched; legacy_new=0.
Автор реализации не отмечает reviewer-owned checklists. Код начинается после независимого review и taskstoissues. Коммит — только после разрешения пользователя и проверки.

## Validation Plan
См. quickstart.md. Существующие контрактные/интеграционные проверки настроек и календарей, timezone node test; Swift shell/sidebar/bridge tests. Добавить минимальные проверки изменения маршрута/панели и представления форм. Ручная матрица всех разделов, две темы, 360 px, 200%, клавиатура. Установленная проверка только GRAF Dev через harness после разрешённого коммита, чистого checkout и проверки занятого стенда.

## Project Structure
- `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_*_content.html`: основные формы.
- `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/calendar_settings.html`: подключение и параметры календарей.
- `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_*_content.html`: финансовые пояснения.
- `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`, `cabinet.js`: оформление и существующая навигация/формы.
- `apps/server/src/twobrain_rec_server/cabinet/view_models.py`: только отображаемые подписи при необходимости.
- `apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift`, `apps/macos/RecApp/App/TwoBrainRecApp.swift`: маршрут и компактная панель.
- `apps/server/tests/`, `apps/macos/Shared/Tests/`: существующие проверки.
- `specs/6792-settings-product-experience/`: spec, plan, research, data-model, contracts, quickstart, tasks, checklists, prototype, validation.

## Complexity Tracking
Новых подсистем нет. Существующие settings styles редактируются на месте; без ещё одного конкурирующего слоя. Длинный список приложений остаётся полным, ограничивается высотой и поиском; автоматическое определение установленных приложений не добавляется.
