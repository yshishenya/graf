# Tasks: Понятное выделение активных элементов

Lane: `high-risk-ux`. Требования/дизайн независимо проверены: 11/11 PASS; фактическая реализация и выпуск проверяются отдельно.

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
- [ ] T009 После одобренного коммита выполнить GRAF Dev build/promote/status/smoke и ручную матрицу, точные PR checks, merge, frozen release-full, CD dry-run/execute, Developer ID/notarization/stapling/Gatekeeper и публичный Sparkle appcast/ZIP/PKG; записать отдельные доказательства source/server/public/installed в specs/285-refine-focus-indicators/validation.md и сверить закрытие issues.

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
