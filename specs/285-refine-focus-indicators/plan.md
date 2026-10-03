# Implementation Plan: Понятное выделение активных элементов

**Branch**: `285-refine-focus-indicators` | **Date**: 2026-10-02 | **Spec**: [spec.md](spec.md)

## Summary

Убрать системный прямоугольник информационных контейнеров записи и сохранности, сохранить целевую прокрутку/VoiceOver; дать полям один контур в существующей границе. Общий клавиатурный outline кнопок и ссылок сохраняется.

## Technical Context

Swift/SwiftUI/AppKit и существующий cabinet CSS. macOS 14+, embedded WKWebView и поддерживаемые браузеры. Данные/API/миграции не меняются. Зависимости не добавляются. Минимальный diff: DesktopMeetingShellView.swift, NativeSettingsComboBox.swift, cabinet.css и регрессионные проверки. Существующие NotificationCardButton используют стандартное выделение конкретных кнопок; оно не является дефектом и не требует нового рисования.

## Risk / Validation Lane

`high-risk-ux`: общая доступность и панель записи. Полный Spec Kit; обязательный clarify выполнен в spec.md. Reviewer-owned requirements/ux должны пройти независимую проверку до реализации. Анализ: CRITICAL 0 / HIGH 0 / без blocking clarification. Issue sync обязателен. Коммит только после локальной валидации и явного одобрения пользователя по AGENTS.md. Затем GRAF Dev harness на clean SHA, PR governance-fast/macos-pr/pr-metadata, converge и один frozen release-full. Прод и macOS update разрешены запросом пользователя при успешных воротах.

## Constitution Check

До исследования PASS: I/II — аудиотракт, видимость/Stop/согласие не меняются; III — данные/секреты не появляются; V — существующие Developer ID, notarization и Sparkle обязательны; VI — полный Spec Kit; VII — исправление известного дефекта и доступности на текущей поверхности GRAF, новые сторонние assets отсутствуют. После дизайна те же ворота PASS. 2026-10-03 пользователь явно разрешил выпуск F285 без фактической проверки перехода VoiceOver и запретил включать или проверять VoiceOver. Это исключение касается только ручного runtime-сценария capture/custody; доступность сохраняется по коду, результат не объявляется PASS. Ограничение записывается в отчёте и заметках выпуска. Применимы docs/agent-guidance/{spec-kit-flow,product-gates,local-development,release-and-validation,macos-notarization,tracker-policy,github-issue-canon}.md и PRD §29.

## Phase 0 — Research

См. research.md: нативный parent .focusable рисует неверный прямоугольник; замена на AccessibilityFocusState сохраняет семантический переход VoiceOver. CSS :focus-visible остаётся для действий, поля получают border + внутреннее расширение одной границы. Никакого глобального outline:none.

## Phase 1 — Design

См. contracts/focus.md, data-model.md и quickstart.md. Для явного перехода notification → recording по-прежнему раскрыть панель, прокрутить capture/custody id, назначить accessibility focus только после явного запроса. При старте/остановке нет отдельной новой команды фокусировки/активации.

## Project Structure

- apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift: AccessibilityFocusState, accessibilityFocused для двух контейнеров; без focusable.
- apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css: исключить range/radio/checkbox/file из поля, single contour text/search/textarea/code, select outline2px offset-2px для WebKit; forced-colors сохраняет outline.
- apps/macos/RecApp/Sources/Settings/NativeSettingsComboBox.swift: заменить NSFocusRingPlacement.only на единую 2px stroke внутри границы существующим DesktopDesignTokens.focusRing; focused field и keyboard loop сохраняются.
- apps/macos/Shared/Tests/NativeSettingsComboBoxTests.swift: нативный активный контур и сохранение доступности/editing.
- apps/macos/Shared/Tests/AppControlAccessibilityTests.swift: отсутствие keyboard parent target и сохранение scroll/AX route.
- apps/server/tests/browser/focus-indicators.test.cjs: реальные computed styles и mouse/Tab/checkbox/range/modal, WebKit и Chromium, light/dark/high contrast/forced-colors где поддерживается.
- apps/server/tests/contract/test_focus_indicators_browser.py: pytest browser entrypoint, changed contract selection в governance-fast и полный release-full.
- changes/unreleased/F285.yaml: русский changelog, compatibility и limits.
- specs/285-refine-focus-indicators/validation.md: проверки и SHA без частных снимков/данных.

## Complexity Tracking

Новых абстракций нет. Не менять notification keyboard loop, native combo без подтверждённого дефекта, JS restoration, focus traps и семантические рамки выбора/ошибок/источников. Не менять глобальные настройки macOS.
