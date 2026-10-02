# Валидация F285 — реализация и выпуск

Дата: 2026-10-02. Lane: `high-risk-ux`, полный Spec Kit.
Ветка: `285-refine-focus-indicators`.
Основа: `77e6aed8ff79127d6e6b284ad18b58da5793ef51`.
Проверены незакоммиченные файлы поверх этой основы, перечисленные ниже. Это локальное доказательство, не PR exact-SHA или release evidence.

## Результат исправления

У capture/custody контейнеров удалены две обычные keyboard focus цели. Scroll, явный navigation request и VoiceOver target сохранены; accessibility binding custody находится после итогового grouping/label. Аудиотракт, действия записи и NotificationCardButton не изменены.

Текстовые поля используют перекрашенную границу + inset1px без внешнего outline. Borderless редактор названия — inset2px. NativeSettingsComboBox рисует внутренний stroke2px и синхронизирует CALayer borderColor; blur возвращает обычную границу. Native HTML select использует outline2px с offset-2px, поскольку WebKit игнорирует внутреннюю тень native select. Forced colors — один внутренний Highlight outline2px; нативная перерисовка прозрачной границы перекрывается им.

Кнопки/ссылки/summary/checkbox/radio/range/file сохраняют keyboard indicators. Веб-тест проверяет отсутствие активации от focus, стандартную активацию от click, неизменную геометрию, contrast >=3:1 во всех соседних токенах, светлую/тёмную тему и increased contrast. На macOS WebKit полная навигация действий использует Option+Tab без изменения настройки системы.

## Проверки

| Проверка | Результат |
| --- | --- |
| Requirements/design reviewer и повторная сверка T001–T009 | PASS, requirements 4/0, ux 7/0 |
| Analyze FR-001–008, SC-001–004 → T001–T009 | PASS, 100% coverage, CRITICAL/HIGH/MEDIUM 0 |
| GitHub issue canon ensure / validate | PASS, 300 открытых Spec Kit issues проверено; все T001–T010 имеют owner |
| Swift AppControlAccessibility/NativeSettingsComboBox/DesktopNotificationAccessibility/DesktopNotificationProtectedConsumer | PASS, 75 XCTest, 0 failures |
| Финальная перестановка custody AX binding после grouping/label: Swift AppControlAccessibility | PASS, 25 tests, 0 failures; весь затронутый Swift модуль повторно собран |
| Chromium focus-indicators | PASS: поля, mouse/keyboard, геометрия, темы, контраст, forced colors |
| WebKit focus-indicators | PASS: поля, mouse/Option+Tab, геометрия, темы, повышенный контраст |
| pytest focus browser + cabinet static assets + settings contracts | PASS, 102 tests, 0 failures |
| meeting-delete-focus | PASS, все направления Tab удерживаются внутри диалога |
| local-recording-focus | PASS, stable nodes, changed actions, checkbox handoff, time context, dialog restoration/removal |
| Ruff нового pytest entrypoint | PASS |
| spec-kit-governance + frozen bootstrap doctor | PASS |
| validate-changelog-fragments | PASS |
| git diff --check | PASS |

Swift содержит существующие deprecation warnings старых AppKit accessibility API. pytest содержит один существующий PytestAssertRewriteWarning. Ошибок или skipped обязательных доказательств нет. Общие CI не запускались локально вместо положенных GitHub gates.

## Проверка причины и исправленных тестов

До кода новый Chromium тест отказал на двойном outline. Две Swift regression отказали (33 assertions), воспроизведя keyboard контейнеры и системный внешний контур. Дополнительный native layer check показал четыре отказа из-за separatorColor поверх stroke; после синхронизации цвета слоя все проверки прошли.

Существующий local-recording-focus одинаково отказал на baseline и F285: он менял graf-timezone серверной страницы вместо graf-time-preferred пользовательского предпочтения. T010 исправил только fixture из двух строк; production user-time.js не менялся. Полный сценарий после этого прошёл.

Новый pytest browser entrypoint попадает в changed contract selection governance-fast; release-full выполняет общую browser/contract проверку с установленным Chromium. WebKit выполняется отдельной обязательной локальной командой.

## Converge и tracker

T010 добавлен append-only при обнаружении устаревшей fixture, owner #7452. Других недостающих изменений реализации не найдено. Остаток уже описан T008/T009; локальная реализация готова, tracker/release pending. Issues не закрыты по неполным PR/release доказательствам.

- Umbrella: #7448.
- T001: #7450.
- T002–T003: #7451.
- T004–T007, T010: #7452.
- T008–T009: #7453.

## Что ещё обязательно

1. Пользователь после валидации явно одобрил коммит и продолжение выпуска: «Да, зафиксируй и продолжай выпуск». Коммит/PR/merge будут привязаны к полному SHA.
2. Только после одобренного коммита: штатные GRAF Dev build/promote/status/smoke на clean SHA и матрица quickstart (Stop, Tab, поля, notification→recording/VoiceOver и диалоги). Пока установлен Dev на `7c4f844a983f2fe10a5f51fa695310acd47abac1`, этот стенд не доказывает новое исправление.
3. PR checks governance-fast/macos-pr/pr-metadata на точном SHA и checked base.
4. Новый замороженный CalVer, один authoritative release-full, CD dry-run/execute; release boundary перепроверить после актуального опубликованного stable `v2026.10.02.6`.
5. Developer ID/notarization/stapling/Gatekeeper и Sparkle previous/new signature; публичные ZIP/PKG/appcast bytes и фактическая установленная версия проверяются отдельно.

Прод и публичное macOS обновление авторизованы пользователем. Повторное разрешение на коммит и deploy не требуется: одобрение после валидации получено. Нет нового production release, не объявляется ручная/установленная приёмка или фактический runtime VoiceOver PASS по одним source assertions.

## Разрешение и актуальная основа выпуска

2026-10-02: пользователь одобрил проверенные изменения после локальной валидации. Живой GitHub показывает опубликованный `v2026.10.02.6` от 2026-10-02T19:50:50Z, tag/master `56e98f101`. Новые изменения master касаются публичных руководств и подготовки выпуска; runtime/test файлы F285 не пересекаются. Перед PR ветка будет перенесена на эту основу с сохранением всех восьми проверенных файлов.

## Идентичность проверенных файлов

| Файл | SHA-256 |
| --- | --- |
| `apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift` | `95866ab0472e1009b78ea41b4b4008b1d2f0b9245e9abe628509b91018726f62` |
| `apps/macos/RecApp/Sources/Settings/NativeSettingsComboBox.swift` | `a535ac52f426beb00416c5850fa2d5d7d33e2912e971fa19165184a7206cd761` |
| `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css` | `a261058e23eff659b2ddb47e6d48e81a23940232631fbca2488f0ad2f761e169` |
| `apps/macos/Shared/Tests/AppControlAccessibilityTests.swift` | `59eac8f2cd7d8a8b8294c18bbf523d2f3c4a665c6e352d0367fa4329b9ba9752` |
| `apps/macos/Shared/Tests/NativeSettingsComboBoxTests.swift` | `51420bb9378b0809c420cb82b0979c370ae1154a9ef610384c7245742be2b8b8` |
| `apps/server/tests/browser/focus-indicators.test.cjs` | `7ce9125e4590b00875fca528275eae2b0e468b46dfc12ee0ac68623ae508ec3d` |
| `apps/server/tests/contract/test_focus_indicators_browser.py` | `5907ef1bb0e1c9bcdbe07f885b54a701a612c6ad88332c2de81ac5ab9e67fb6a` |
| `apps/server/tests/browser/local-recording-focus.test.cjs` | `2084cd757c40f140267d52f5889ab7d5372ab379ba30b90680146daaee57971b` |

## PR checkpoint и исправление T011

Коммит после одобрения перенесён на master без конфликтов: `00dc275bf9bfcdea1dfacbb31c2754fdbfb13a36`. PR #7461. Все восемь проверенных файлов сохранили байты при переносе. Первая попытка PR CI остановилась: governance-fast — отсутствует обязательный раздел Legacy Impact в spec.md; macos-pr — компилятор Swift CI не смог вывести тип сложного zip/reduce в новом тесте luminance. Это не успешные PR gates.

T011 добавлена append-only с ownership #7452. Раздел Legacy Impact: untouched добавлен; формула luminance разбита на явные CGFloat выражения без изменения коэффициентов/assertions. После этого: NativeSettingsComboBoxTests 28/0, legacy-impact/governance/changelog/diff PASS. Независимый reviewer подтвердил эквивалентность и лично прочитал 28 Swift, 102 pytest и local-recording PASS. Производственные файлы не менялись. Новые PR checks обязательны на новом SHA.

## Установленный GRAF Dev

На `00dc275bf9bfcdea1dfacbb31c2754fdbfb13a36` штатные build/promote/status/smoke PASS. Manifest `dev-00dc275bf9bf`, bundle ID `pro.2brain.graf.dev`, все 13 health checks PASS, source SHA каждого компонента совпадает. Подпись и разрешения сохранены.

Ручная проверка в единственном `/Applications/GRAF Dev.app`: короткая запись началась, Stop вернул «Запись остановлена» и доступную кнопку старта; большая синяя рамка отсутствует. Во встроенном WKWebView поиск показывает один контур, Tab → «Фильтры», Shift+Tab → поиск без выполнения действия. В настройках нативный часовой пояс в светлой теме показал один внутренний контур и стандартный popup по клику. Проверки продолжаются; фактическое озвучивание VoiceOver не подтверждено и не выдаётся за PASS. Частные снимки и аудио в доказательства не сохраняются.
