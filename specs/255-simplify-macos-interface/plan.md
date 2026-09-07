# Implementation Plan: Единая и простая оболочка GRAF

**Branch**: `codex/255-simplify-macos-interface` | **Date**: 2026-09-06 | **Spec**: [spec.md](spec.md)
**Status**: Реализация начата после review требований; нативная приёмка GRAF Dev и обеих ОС ещё открыта.

## Summary

Одна структура навигации, два законченных материала. В браузере — матовая панель с мягкой геометрией. В macOS — стандартная нативная sidebar рядом с существующим WKWebView: системный Liquid Glass на macOS 26 и непрозрачное исполнение на предыдущих ОС/при уменьшении прозрачности. Содержимое встреч остаётся в существующем кабинете. Профиль теряет десять постоянных заглушек, основные разделы доступны также из настроек.

## Technical Context

- **Language/Version**: Swift 6, SwiftUI/AppKit/WebKit; Python 3.11+, FastAPI/Jinja; существующие CSS и JavaScript. Исследование SDK: Xcode 26.6 / Swift 6.3.3.
- **Primary Dependencies**: только существующие зависимости; стандартный split view и системные материалы, без библиотеки оформления.
- **Storage**: существующие preferences и сессии; новых таблиц, миграций, theme UserDefaults или настройки материала нет.
- **Testing**: текущие pytest и Swift Testing/XCTest; браузерные синтетические сценарии и нативная ручная проверка.
- **Risk / Validation Lane**: `high-risk-feature` — общая навигация, доступность и граница native/WebView рядом с записью и сессией.
- **Release Gate**: на подготовке/реализации `no deploy`; публикация только после exact-SHA gates, согласованного кандидата, CD dry-run и правил macOS notarization.
- **Target Platform**: macOS 14.5+; Liquid Glass с macOS 26; текущие поддерживаемые браузеры.
- **Project Type**: native desktop + серверный HTML кабинет.
- **Performance Goals**: 0 дополнительных HTTP-запросов ради материала; 0 опроса; 0 пересозданий WebView при смене темы/панели. Один снимок меню на готовый документ и обновление при реальной смене существующего предпочтения.
- **Constraints**: окно 1040×680; веб 320/390/768/1024/1440 px; текст/масштаб 200%; Stop одним действием; старые клиент/сервер сохраняют HTML-навигацию.
- **Scale/Scope**: общая оболочка и меню; инвентаризация всех пользовательских поверхностей плюс потребителей общих CSS в админке. Внутренние функции F245–F253 не переписываются.

## Constitution Check

До исследования и после проектирования проверены принципы I–VII. Проектных исключений не требуется:

| Принцип | Решение и необходимое доказательство |
|---|---|
| I–II: system-audio-first, видимое управление | Не менять capture state machine; native start/stop вне зависимости от готовности документа; T008/T012 |
| III: данные/границы | Мост передаёт только метаданные меню, без аудио, текста встреч и секретов; T003/T005 |
| IV: удаление | Удаление записей, retention и обещания очистки не меняются |
| V: распространение | Developer ID, notarization, stapling, Gatekeeper и Sparkle обязательны в T014 |
| VI: Spec Kit | clarify записан в spec; checklist reviewer-owned; analyze → issues → implement → converge |
| VII: reference/accessibility/provenance | Изменение оболочки по прямому запросу владельца; собственные/системные ресурсы, функциональные маршруты сохранены; T011/T012 |

Согласованность проекта не заменяет одобрение требований рецензентом. Все custom checklist остаются открыты до такого review.

## Architecture and sequence

1. После допуска выполнить маленький нативный прототип в существующем workspace: системная sidebar, один WebView, текущий titlebar accessory. Прототип должен визуально доказать материал на macOS 26 и геометрию при 1040×680. Если стандартный компонент не работает с текущим окном, исправить план по фактам до расширения интеграции; CSS blur не подменяет результат.
2. Сервер продолжает владеть пунктами, маршрутами и формами профиля. `sections.html` отдаёт компактное описание текущего меню. Swift не дублирует список категорий. Контракт и переход владения определены в `contracts/interface.md`.
3. `EmbeddedCabinetNavigationController` остаётся единственным владельцем истории и допуска маршрутов. Добавить узкий вход открытия разрешённого маршрута и небольшой bridge; не новый router и не новый preferences client.
4. Один сохраняющий identity WebView всегда находится в том же месте дерева. Видимость sidebar меняется отдельно. Существующий `.id(sessionBoundaryID)` остаётся только для смены сессии.
5. Тема приходит из существующего документа/профиля; native использует light/dark/system без отдельного хранения. Profile commands вызывают существующие формы/CSRF либо native callbacks обновления/завершения.
6. Матовое оформление использует общие роли цвета/отступов. Декоративный разделитель отделён от значимых границ полей и фокуса. Для desktop-native скрыть только HTML sidebar после подтверждённой передачи управления. Browser/no-JS всегда имеет рабочий HTML.
7. Удалить десять постоянных disabled-команд и два пустых подменю. Сохранить рабочий вход «Настройки» в профиле. Удалять перекрытый CSS и недостижимую compact-queue ветку только после повторного поиска всех потребителей; рабочий local mode сохраняется.
8. Совместная проверка открытых F245–F253 по фактическим SHA. Конфликтные файлы не брать из чужой ветки целиком. Не считать их слитыми, пока это не подтверждено.

## Validation Plan

Сценарии и команды — [quickstart.md](quickstart.md), измерение действий — [journeys.md](journeys.md). Автоматические проверки покрывают допуск bridge/route/session, один навигационный набор и формы. Нативная матрица обязательна: web screenshots не доказывают Liquid Glass. T012 требует реального запуска обоих поддерживаемых классов ОС; отсутствие машины macOS 14.5 остаётся незакрытой проверкой.

На PR нужен GitHub `governance-fast` на точном SHA; локальный fast — диагностический fallback по более специальной release guidance. Полный CI один раз на замороженном release candidate. После нового коммита прежнее SHA evidence не считается текущим. До коммита реализации — явное разрешение владельца после проверки.

## Project Structure

- `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetWorkspaceView.swift`: split/sidebar и стабильный WebView.
- `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift`: существующий controller, подключение bridge и сброс состояния.
- `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetShellBridge.swift`: новый узкий разбор сообщений/метаданных, если выделение нужно для проверки границы.
- `apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift`: семантические цвета и доказанно недостижимая ветка.
- `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/sections.html`: единственный источник меню и форм.
- `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.{css,js}`: матовое оформление и передача управления.
- `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/base.html`, `cabinet/view_models.py`: только необходимая передача existing theme/menu.
- `apps/macos/Shared/Tests/`, `apps/server/tests/{unit,contract}/`: профильные проверки.
- `specs/255-simplify-macos-interface/`: spec, plan, research, inventory, journeys, data-model, contracts, quickstart, checklists, tasks, validation evidence.
- `changes/unreleased/F255.yaml`: итоговый фрагмент изменений при реализации.

## Complexity Tracking

Нарушений constitution нет. Новая модель меню — краткоживущее представление существующего документа; не сервис, не хранилище прав и не история. Настоящее стекло требует этой узкой интеграции. Сквозная прозрачность WKWebView не выбрана из-за отсутствия публичной гарантии композиции; второй web/native продукт не создаётся.

## Уточнение владельца: плотность автозаписи, 2026-09-07

В рамках FR-003/FR-006/US3 и текущего active Spec Kit slice устранить декоративные `app.dashed` перед названиями приложений в `MeetingDetectionSettingsView.swift`. Иконки не загружаются: это одинаковые заглушки. Выбран разрешённый владельцем вариант без иконок, без нового поиска приложений или загрузки ресурсов. В общем `AutomaticRecordingRulePicker` высота 28 pt, радиус 6 pt; ширину и подписи не сокращать. Существующие bindings, сохранение, disabled, selected, focus и три правила неизменны. Пользовательский путь по-прежнему одно нажатие.

Показанная владельцем Release QA `ae593ee63` имеет дополнительные исправления F249 (имена для VoiceOver, контраст, пояснения) и высоту 40 pt; текущая ветка F255 имеет высоту 38 pt. Не переносить весь старый файл поверх новой ревизии. При объединении сохранить исправления F249, применить только удаление заглушек и геометрию. Проверки: существующие AppControlAccessibilityTests/CaptureControlV5Tests, Swift build, затем штатный GRAF Dev и визуальная проверка; не выдавать исходную Release QA за обновлённое приложение.
