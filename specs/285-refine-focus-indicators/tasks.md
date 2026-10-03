# Tasks: Понятное выделение активных элементов

Lane: `high-risk-ux`. Требования/дизайн независимо проверены: 14/14 PASS; фактическая реализация и выпуск проверяются отдельно.

## Phase 1: Setup

- [X] T001 Проверить активную ветку, требования, reviewer-owned чеклисты и зависимости в specs/285-refine-focus-indicators/checklist-review.md; завершить analyze и issue sync до кода.

## Phase 2: Foundation

Новых библиотек, API, persistent data или общей инфраструктуры не требуется. T001 блокирует реализацию.

## Phase 3: US1 — Панель записи без лишней рамки (P1)

Цель: информационная карточка не получает обычный keyboard focus, явный переход сохраняет scroll/VoiceOver, дочерние действия доступны.
Независимая проверка: AppControlAccessibilityTests плюс остановка/Tab/notification navigation в единственном GRAF Dev на clean SHA.

- [X] T002 [US1] Добавить regression существующего контракта контейнеров и перехода в apps/macos/Shared/Tests/AppControlAccessibilityTests.swift; подтвердить отказ до исправления.
- [X] T003 [US1] В apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift заменить keyboard focus контейнеров на accessibility focus; сохранить раскрытие, scrollTo, идентификаторы, Start/Stop/Pause/Resume и дочерние действия.

## Phase 4: US2 — Один контур активного поля (P1)

Цель: текстовые поля имеют один контур без изменения размеров; keyboard indicators остальных действий сохраняются.
Независимая проверка: native combo editing/arrows/Return/Escape, browser mouse/Tab в обеих темах, increased contrast/forced-colors, borderless title и non-field controls.

- [X] T004 [P] [US2] Добавить regression реального нативного контура/геометрии при сохранённых editing/keyboard/AX в apps/macos/Shared/Tests/NativeSettingsComboBoxTests.swift; подтвердить отказ до исправления.
- [X] T005 [P] [US2] Создать apps/server/tests/browser/focus-indicators.test.cjs с computed styles, contrast ≥3:1, неизменными размерами, click/Tab, native combobox HTML/code/title, checkbox/radio/range/file/button/link/summary и forced-colors; связать с pytest в apps/server/tests/contract/test_focus_indicators_browser.py; подтвердить отказ до исправления.
- [X] T006 [US2] Заменить внешний системный контур единым 2px stroke внутри bounds существующим focusRing в apps/macos/RecApp/Sources/Settings/NativeSettingsComboBox.swift; сохранить currentEditor/keyWindow guard и repaint lifecycle.
- [X] T007 [US2] В apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css дать текстовым полям/select/textarea inset contour, borderless title inset2px, native HTML select внутренний outline2px, code inset1px и один forced-colors Highlight outline; сохранить semantic/error/selection рамки, не отключать outline глобально.

## Phase 5: Проверки и выпуск

- [X] T008 Провести локальные проверки high-risk-ux и независимый просмотр реализации по quickstart, выполнить converge; записать доказательства/ограничения в specs/285-refine-focus-indicators/validation.md и русский changelog в changes/unreleased/F285.yaml; получить требуемое AGENTS.md одобрение коммита после валидации.
- [ ] T009 После одобренного коммита выполнить GRAF Dev build/promote/status/smoke и разрешённую ручную матрицу (исключение пользователя 2026-10-03: VoiceOver не включать/не проверять; его runtime-переход остаётся неподтверждённым и записывается в отчёте/заметках выпуска), точные PR checks, merge, frozen release-full, CD dry-run/execute, Developer ID/notarization/stapling/Gatekeeper и публичный Sparkle appcast/ZIP/PKG; записать отдельные доказательства source/server/public/installed в specs/285-refine-focus-indicators/validation.md и сверить закрытие issues.

## Dependencies & execution order

T001 → T002 → T003; T001 → T004 → T006; T001 → T005 → T007. T003/T006/T007 → T008 → T009. Tests-before-code внутри каждой истории. T004 и T005 независимы; их проверки можно запускать одновременно. US1 и US2 не требуют новых общих компонентов.

## Parallel examples

US1: его независимые проверки accessibility и notification могут выполняться одновременно после T003. US2: T004 (Swift) и T005 (browser) изменяют разные файлы; после кода Chromium и Swift независимы. Параллельное изменение одного файла не требуется.

## Implementation strategy

Сначала US1 как минимальное исправление фотографии, затем US2. Публиковать согласованный полный результат обеих историй только после обязательных ворот. Commit checkpoint определяется AGENTS.md; автоматические commit hooks отключены.

## GitHub ownership

Umbrella: #7448.
- T001: #7450
- T002, T003: #7451
- T004, T005, T006, T007: #7452
- T008, T009: #7453

## Phase 6: Convergence — существующая проверка локальных записей

- [X] T010 Исправить устаревшую timezone fixture в apps/server/tests/browser/local-recording-focus.test.cjs: задавать существующий graf-time-preferred для выбранного пользователем пояса; повторить все keyboard/stable-node/dialog-removal проверки без изменения production user-time.js. Исходная проверка одинаково отказала на baseline и F285. Ownership: #7452.

Локальный checkpoint: T008 — тесты/changelog/converge и итоговый независимый review выполнены; explicit approval пользователя после валидации получено: «Да, зафиксируй и продолжай выпуск». T009 — Dev/PR/release/public/installed pending. Доказательства: validation.md.

## Phase 7: Convergence — точные PR-проверки

- [X] T011 Устранить два отказа первого CI на SHA 00dc275bf9bfcdea1dfacbb31c2754fdbfb13a36: добавить обязательный Legacy Impact в spec.md и разбить вычисление яркости NativeSettingsComboBoxTests.swift на явные CGFloat выражения для компилятора Swift CI; сохранить формулу и все assertions, повторить профильные проверки и независимый review. Код продукта не меняется. Ownership: #7452.

## Phase 8: Convergence — повторный аудит 2026-10-04

- [X] T012 Уточнить FR-009/FR-010, независимые reviewer-owned требования и analyze; связать новые задачи с GitHub issue до кода.
- [X] T013 [US3] Дополнить apps/server/tests/browser/focus-indicators.test.cjs программными/интерактивными целями и карточкой руководства; подтвердить отказ на старом CSS.
- [X] T014 [US3] В apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css убрать рамки информационных программных целей, сохранив выделение настоящих действий; в apps/server/src/twobrain_rec_server/public/static/public/content.css заменить рамку карточки подчёркиванием заголовка.
- [X] T015 [US3] Проверить Chromium/WebKit/темы/forced colors/restore, независимый review и converge; записать отчёт specs/285-refine-focus-indicators/validation.md и changes/unreleased/F285.yaml; получить одобрение нового проверенного коммита перед PR/выпуском.

Ownership дополнения 2026-10-04: #7499 — T012–T015; выпуск всей F285 остаётся #7453/T009.

Checkpoint дополнения: T012–T015 выполнены локально; независимые требования 14/0 и read-only code review без дефектов, локальные проверки PASS, явное одобрение нового коммита получено. T009 остаётся открыта до Dev/PR/release/public/installed.
