# Tasks: F247 — настройка разрешений macOS

Prerequisites: spec/clarify, plan/research/data-model/contracts/quickstart, reviewer-owned checklists. Lane: high-risk-product. Umbrella #6598. Реализация последовательно; [P] отсутствует из-за общих файлов.

## Phase 1 — Foundation

- [X] T001 Добавить проверки переходов, ограниченного ожидания и входа без capture в apps/macos/Shared/Tests/SystemAudioPermissionUXTests.swift и AppControlAccessibilityTests.swift (FR-001–009, SC-002).

## Phase 2 — US1

Цель: последовательная настройка; независимая проверка unknown/partial/ready.
- [X] T002 [US1] Перестроить нативное окно и следующий шаг в apps/macos/RecApp/Sources/Capture/DesktopPermissionOnboardingView.swift и CTA в CaptureControlViewCore.swift (FR-001–004/009, SC-001).

## Phase 3 — US2

Цель: отказ/Позже/Settings не создают тупиков; независимая проверка повторного открытия и отсутствия автоокна.
- [X] T003 [US2] Отделить refresh от показа, сохранить историю, обработать Settings failure и оградить старт/текущий ask в apps/macos/RecApp/App/TwoBrainRecApp.swift (FR-002–004/007/008).

## Phase 4 — US3

Цель: bounded verification и безопасное восстановление; независимая проверка timeout/revoke/stale/retry/protected work.
- [X] T004 [US3] Убрать ложный restart и запросы вне мастера, ограничить проверку в apps/macos/RecApp/Sources/Capture/SystemAudioCaptureService.swift и TwoBrainRecApp.swift (FR-005–008/010, SC-002).

## Phase 5 — Validation

- [X] T005 Проверить нативные состояния/темы, focused Swift tests/build и high-risk fast gate; записать convergence/ограничения в specs/247-macos-permission-journey/validation.md и changes/unreleased/F247.yaml (SC-001–003, FR-009/010).

## Dependencies / Strategy

T001 → T002 → T003 → T004 → T005. Тесты T001 сначала показывают дефект; выполнение фиксируется после успешной проверки. MVP включает все три истории: recovery необходима для отсутствия тупиков. Независимые просмотры источников допустимы параллельно; правки общих файлов — последовательно.

## GitHub ownership

- T001: #6604
- T002: #6605
- T003: #6606
- T004: #6607
- T005: #6608

## Local implementation evidence — 2026-09-06

T001–T004 реализованы и проверены локально: 119 focused XCTest tests passed, Swift build passed. Native preview дополнительно проверен через NSHostingView с реальной прокруткой до «Позже» при высоте 380 pt.
T005 остается открытой: fast gate отказал до запуска стадий из-за dirty_worktree; нужен согласованный commit и проверка его точного SHA. GitHub issues T001–T004 остаются открыты до PR/окончательной приемки, с явными status comments. Подробности: validation.md. Реальные TCC/MDM/VoiceOver checks — перед выпуском на отдельном тестовом Mac.

## Convergence — 2026-09-06, повторная проверка

- [X] T006 [US3] Обновить устаревшие проверки запуска и восстановления в apps/macos/Shared/Tools/ContractValidation/ContractValidationV5.swift: права проверяются до preparing без запроса, runtime error запускает проверку доступности вместо безусловного restart (FR-005–008); выполнить ContractValidation и fast CI.

Зависимость: T004 → T006 → завершение T005. Найдено при расширенной проверке: полный набор 796 macOS tests проходит, отдельный ContractValidation пока требует прежнего поведения. Анализ: новые требования не добавляются; прежняя проверка противоречит FR-005–008, обновляется только тестовый контракт.

- T006: #6612

## Итог реализации

Все T001–T006 выполнены. GitHub governance-fast успешно завершен для implementation SHA `6e457dfe34f1c82270204b61579c1bcd19f74fe1`: https://github.com/yshishenya/graf/actions/runs/34017555088. PR: https://github.com/yshishenya/graf/pull/6613. Предыдущие записи об ожидании отражают ход проверки; блокировка снята. Изменения этого раздела документируют результат; CI итогового PR HEAD проверяется отдельно. Issues закрываются при слиянии PR, release acceptance остается отдельным этапом.

## Phase 6: Convergence

- [X] T007 [US3] Устранить блокировку системного Quit/Reopen открытой настройкой и продолжить её после запуска в apps/macos/RecApp/App/TwoBrainRecApp.swift и Sources/Capture/DesktopPermissionOnboardingView.swift; проверить границы в apps/macos/Shared/Tests/AppControlAccessibilityTests.swift и реальный процесс через apps/macos/Scripts/test-permission-restart.py; обновить evidence (FR-003/006/008/011, SC-002; partial, HIGH).

Источник: сообщение пользователя о блокировке перезапуска из System Settings. Прежние 119 тестов не проверяли внешний Quit при открытом sheet.

- T007: #6625

T007 также учитывает нативные кнопки заголовка: apps/macos/RecApp/Sources/Cabinet/DesktopCabinetWorkspaceView.swift должен уважать isEnabled скрытого workspace, чтобы Home/Back/Reload не оставались доступными за страницей.

T007: локальная реализация, внешний Quit proof, повторный запуск и нативный UI проверены; новый exact-SHA governance-fast обязателен перед merge. Подробности в validation.md.

## Phase 7: UX refinement

- [X] T008 [US1] Сделать настройку ориентированной на запись разговора: один текущий шаг, компактный прогресс, короткие тексты, контекстная помощь и различимые busy/restricted состояния в apps/macos/RecApp/Sources/Capture/DesktopPermissionOnboardingView.swift; передать признак проверки из apps/macos/RecApp/App/TwoBrainRecApp.swift, обновить профильные UX/accessibility tests, native screenshots и evidence (FR-001/003/004/009/011/012).

- T008: https://github.com/yshishenya/graf/issues/6627

T008: локальные тесты/рендеры/нативный путь пройдены, ограничения записаны в validation.md. Новый exact-SHA governance-fast обязателен перед merge.
