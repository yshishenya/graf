# Tasks: Единый интерфейс GRAF: токены, состояния и копирайт

**Feature**: 268-ui-consistency-unification
**Lane**: high-risk-product
**Contracts**: `plan.md`, `research.md`, `contracts/ui-tokens-and-copy.md`, `quickstart.md`

## Phase 1: Setup

- [X] T001 Зафиксировать базовую линию: focused pytest из `quickstart.md`, `swift build --package-path apps/macos`, скриншоты и замеры стенда `tests.fixtures.calendar_visual_ui_harness` (dark/light, 1440/390) в `specs/268-ui-consistency-unification/evidence/baseline/`; запись в `validation.md`.

## Phase 2: Foundational

- [X] T002 [P] Веб-токены: в `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css` добавить `--font-size-body: 14px`, `--font-size-body-compact: 13px`, `--radius-xs: 6px`, `--radius-sm: 8px`, `--overlay-backdrop`, `--shadow-dialog`, `--speaker-contrast-text`, задействовать `--pink`; удалить `--control-height-lg`, `--line-height-caption`, `--font-family-mono`, `--tooltip-offset`; обновить `apps/server/tests/contract/test_cabinet_static_assets_contract.py`.
- [X] T003 [P] macOS-токены: создать `apps/macos/RecApp/Sources/Cabinet/DesktopDesignTokens.swift` (динамические цвета кабинета для светлой и тёмной темы, радиусы, размеры шрифта, тона статусов) и тест `apps/macos/Shared/Tests/DesktopDesignTokensTests.swift`.

## Phase 3: US1 — единый визуальный язык (P1)

- [X] T004 [US1] Веб: убрать локальные палитры `cabinet.css:5667-5692`, `6034-6041` и белые подложки (список из инвентаря); перевести жёсткие цвета на токены/`color-mix`; свести радиусы к шкале; выровнять типографику (удалить позднее `body { font-size }`, единый заголовок страницы и диалога); удалить дубли правил и мёртвые правила; то же для `playback-comments.css`.
- [X] T005 [US1] macOS: применить `DesktopDesignTokens` в `DesktopMeetingShellView.swift`, `TwoBrainRecApp.swift`, `CaptureControlViewCore.swift`, `CaptureStatusItem.swift`, `DesktopPermissionOnboardingView.swift`, `MeetingDetectionSettingsView.swift`, `DesktopNotificationPresenter.swift`, `AppUpdateNotice.swift`, `DesktopSupportIncidentActionStrip.swift`, `DesktopCabinetWorkspaceView.swift`; заменить мёртвые hex-константы, убрать `Color.accentColor` в фирменных элементах.
- [X] T006 [US1] Проверка: `test_cabinet_theme_contract.py`, `test_cabinet_static_assets_contract.py`; замеры стенда (фон/акцент/границы карточки встречи = токены, контраст ≥ 4,5:1 в обеих темах); запись в `validation.md`.

## Phase 4: US2 — состояния кабинета (P1)

- [X] T007 [US2] Веб: компонент `.notice` с тонами и разметка в биллинге/рефералах/примитивах; оформление статусов списка (`.meeting-status`, `.meeting-content-readiness`, `[data-processing-retry-class]`, `.meeting-result-count`); исправление скелетона (токены, высота строки = реальной); сворачивание пустого `.meeting-toolbar`.
- [X] T008 [US2] Веб: один `.icon-button` с вариантом `--ghost` и исправление каскада `.danger-button`; единые диалоги (тень, backdrop, радиус, заголовок, отступы); тон автосохранения по `form[data-state]`; текст окна «Поделиться» по состоянию доступа; палитра спикеров (уникальные цвета, светлые варианты, контрастный текст).
- [X] T009 [US2] Проверка: focused pytest биллинга/настроек/списка/доступности/шеринга; замеры стенда (скелетон, кнопки закрытия, тона статусов); запись в `validation.md`.

## Phase 5: US3 — нативные состояния (P1)

- [X] T010 [US3] macOS: `MeetingDetectionStatus` в `apps/macos/Shared/Sources/MeetingDetection/MeetingDetectionModels.swift`; замена строковых статусов в `TwoBrainRecApp.swift`; честный `meetingDetectionSummary` в `CaptureControlViewCore.swift:402-419`; обновление `CaptureControlV5Tests`, `AppControlAccessibilityTests`.
- [X] T011 [US3] macOS: настройки уведомлений доступны без входа (`DesktopNotificationPresenter.swift:640`); онбординг — единая типографика, тон ошибки, стили кнопок, цели ≥ 40pt; настройки автозаписи — одна ошибка, без разделителя под последней строкой, фирменный акцент fallback; единый тон ошибки в полосе поддержки; цели нажатия ≥ 40pt (шестерёнки, кнопки промпта).
- [X] T012 [US3] macOS: трей — читаемая обрезка с полным текстом, честный заголовок ближайших событий, информационные строки не выглядят отключёнными; подсказка навигации без служебного текста; тесты.
- [X] T013 [US3] Проверка: `bash apps/macos/Scripts/run-swift-tests.sh`, ручная проверка в `/Applications/GRAF Dev.app`; запись в `validation.md`.

## Phase 6: US4 — словарь и текст (P2)

- [X] T014 [US4] Единый словарь: остановка записи — «Остановить запись» везде из одного источника; «Автозапись»/«Запись встреч»; «Расшифровка» вместо «Транскрипт» (`cabinet/rendering.py:1936,2826,2831`, `meeting_protocol.py`); подписи обновлений из одного источника; обновить тесты локализации.
- [X] T015 [US4] Конвенция без «ё» и опечатки «ЮKassa»/«недоступны» в `cabinet/templates`, `cabinet/*.py`, `public/**`, `admin/**`; синхронно обновить `apps/server/tests/**`.
- [X] T016 [US4] Конвенция без «ё» в `apps/macos/RecApp/**` и `apps/macos/Shared/Sources/**`; обновить `apps/macos/Shared/Tests/**`; тест-страж на отсутствие «ё» в пользовательских строках.
- [X] T017 [US4] Проверка: поиск запрещённых вариантов пуст, тесты текстов и локализации проходят.

## Phase 7: US5 — обновления (P2)

- [X] T018 [US5] Один постоянный индикатор: полоса `AppUpdateNotice` только для фаз `downloading/installing/readyToInstall/failed`; единый источник подписей для меню, трея, индикатора и полосы (`AppUpdateController.swift`, `AppUpdateNotice.swift`, `TwoBrainRecApp.swift:3581-3586`, `CalendarTray.swift:279-284`, `DesktopMeetingShellView.swift:405-436`); обновить `AppUpdateControllerTests`, `DesktopCalendarReminderTests`.
- [X] T019 [US5] Проверка: тесты фаз и подписей; один индикатор и полоса в Dev-приложении.

## Phase 8: US6 — навигация (P2)

- [X] T020 [US6] Убрать обрезку подписей: паддинг пункта и ширина панели настроек в `cabinet.css`, блок профиля с ограничением строк и `title` (`components/sections.html:44-51`); тест-замер переполнения.

## Phase 9: US7 — страницы вне системы (P3)

- [X] T021 [US7] История уведомлений через `base.html` + `cabinet_shell`: `web_routes/notifications.py:103-113`, `pages/notification_history.html`, навигация и профиль как у списка встреч; тест темы и компонентов.
- [X] T022 [US7] Страницы удаления: карточки, ссылки `.cabinet-link`, общая шкала заголовков, стили `report-band` в `pages/deletion_index_content.html`, `pages/deletion_report_content.html`; единый текст «Отчет удаления»; тесты.

## Phase 10: US8 — доступность (P3)

- [X] T023 [US8] Вкладки карточки встречи без `display: contents` (`cabinet.css:5707`, `pages/meeting_detail_content.html:38-80`) с сохранением визуального порядка; единая обводка фокуса (`--focus-ring`, offset 2px) с документированными исключениями.

## Phase 11: Validation и закрытие

- [X] T024 Финальная проверка: focused pytest из `quickstart.md`, `node --check`, `python3 scripts/check_spec_kit_governance.py`, `bash apps/macos/Scripts/run-swift-tests.sh`.
- [X] T025 Браузерные доказательства: скриншоты и замеры (контраст, обрезка, скелетон, радиусы, окна, статусы) в `specs/268-ui-consistency-unification/evidence/`, 320/390/768/1024/1440, dark/light, standalone/embedded.
- [ ] T026 Dev-приложение: `dev-harness build → promote → status → smoke`, ручная проверка индикатора обновления, статусов автозаписи, трея, онбординга; запись в `validation.md`.
- [ ] T027 Закрытие: `$speckit-converge`, фрагмент `changes/unreleased/268-ui-consistency-unification.md`, `validation.md`, сверка `tasks.md` с GitHub issues.

## Dependencies

- T002–T003 → US1–US8.
- T006 → T007–T008, T020, T023 (визуальные правки поверх токенов).
- T010 → T011–T013.
- T015–T016 → T017.
- T018 → T019, T026.
