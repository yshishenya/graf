# Tasks: Постоянное напоминание об обновлении GRAF

Источник: spec.md, plan.md, research.md, data-model.md, contracts/update-ui.md. Lane: high-risk-feature. Umbrella: https://github.com/yshishenya/graf/issues/6644

## Phase 1: Подготовка

- [X] T001 Проверить требования, checklist и связь GitHub в specs/250-persistent-update-reminders/checklists/ux-security.md и tasks.md (FR-001–009).

## Phase 2: US1 — Сохранение и видимость

Независимая проверка: новая версия остается при skip, сбое и перезапуске, исчезает при установке/отзыве.

- [X] T002 [US1] Добавить проверки сохранения, восстановления, доверия и отзыва в apps/macos/Shared/Tests/AppUpdateControllerTests.swift (FR-002–004, SC-004).
- [X] T003 [US1] Сохранить известное обновление и корректно обрабатывать skip/сбои/отзыв в apps/macos/RecApp/Sources/Updates/AppUpdateController.swift (FR-002–004/006/009).
- [X] T004 [US1] Показать доступное уведомление, номер версии и действие через apps/macos/RecApp/Sources/Updates/AppUpdateNotice.swift, apps/macos/RecApp/Sources/Calendar/CalendarTray.swift и apps/macos/RecApp/App/TwoBrainRecApp.swift (FR-001/008, SC-001).

## Phase 3: US2 — Своевременное обнаружение

Независимая проверка: настройки 14400, запуск уважает disabled automatic checks, старый артефакт 86400 продолжает проходить continuity validator.

- [X] T005 [US2] Согласовать расписание в apps/macos/RecApp/Sources/Updates/AppUpdateController.swift, apps/macos/Installer/Scripts/build-local-installer.sh, apps/macos/Scripts/validate-app-updates.sh и apps/macos/Shared/Tests/InstallerLifecycleEvidenceTests.swift (FR-005, SC-002).

## Phase 4: US3 — Безопасное действие

Независимая проверка: все защищенные состояния и повторные действия не прерывают запись.

- [X] T006 [US3] Проверить единый путь кнопок и защиту записи через apps/macos/Shared/Tests/AppUpdateControllerTests.swift и apps/macos/Shared/Tests/EmbeddedCabinetUpdateBridgeTests.swift; сохранить canCheck/relaunch поведение в apps/macos/RecApp/Sources/Updates/AppUpdateController.swift (FR-006/007, SC-003).

## Phase 5: Проверка результата

- [X] T007 Провести focused tests, сборку, синтетическую UI-проверку и converge по specs/250-persistent-update-reminders/quickstart.md; записать evidence и ограничения в specs/250-persistent-update-reminders/validation.md и changes/unreleased/F250.yaml (FR-001–009, SC-001–004).

## Dependencies and delivery

T001 → T002 → T003 → T004 → T005 → T006 → T007. Общие файлы требуют последовательной реализации. Независимо можно исследовать Sparkle и текущее устройство приложения; реализация не делится по общим файлам. MVP — US1, затем US2/US3 и общая проверка. Чеклисты принадлежат рецензенту. Публикация и коммит не входят в эти задачи; перед merge нужен governance-fast на SHA PR, перед выпуском release-full и реальные проверки signed update.

## GitHub issues

- T001: https://github.com/yshishenya/graf/issues/6645
- T002: https://github.com/yshishenya/graf/issues/6646
- T003: https://github.com/yshishenya/graf/issues/6647
- T004: https://github.com/yshishenya/graf/issues/6648
- T005: https://github.com/yshishenya/graf/issues/6649
- T006: https://github.com/yshishenya/graf/issues/6650
- T007: https://github.com/yshishenya/graf/issues/6651

Локальная реализация T001–T007 и проверки завершены; ограничения живой приемки и выпуска записаны в validation.md. GitHub issues закрываются после PR/evidence на точном SHA, а не по базовому HEAD.
