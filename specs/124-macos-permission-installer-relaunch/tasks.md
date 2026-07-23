# Tasks: надёжная установка и выдача разрешений GRAF

**Execution order**: T001–T002 establish the installer contract, T003–T005
implement permission and termination behavior, T006–T009 update executable
evidence and product documentation, then T010–T012 validate the whole slice.

## User Story 1 — установка на чужом Mac (P1)

- [X] T001 [US1] Добавить в `apps/macos/Installer/Scripts/build-local-installer.sh` явное описание system-audio capture в generated `Info.plist`; сохранить стабильные bundle id/name и существующие strict signature checks.
- [X] T002 [US1] Обновить `apps/macos/Installer/README.md` и `apps/server/src/twobrain_rec_server/public/templates/public/download.html` с одним безопасным Finder/System Settings Gatekeeper path для no-account канала; явно не обещать notarization и не предлагать отключать защиту macOS.
- [X] T006 [US1] Расширить `apps/macos/Shared/Tests/InstallerLifecycleEvidenceTests.swift` и `apps/macos/Scripts/validate-app-updates.sh` проверками privacy metadata и сохранением запрета на TCC/driver workarounds.
- [X] T008 [US1] Обновить `apps/server/tests/unit/test_public_landing.py` проверками нового install handoff текста, не меняя download URL и analytics contract.

## User Story 2 — выдача разрешения микрофону (P1)

- [X] T003 [US2] В `apps/macos/RecApp/Sources/Capture/DesktopPermissionOnboardingView.swift` и `apps/macos/RecApp/Sources/Capture/MicrophoneCaptureService.swift` сделать denied/restricted microphone recovery settings-first, сохранить normal request только для unknown и добавить accessibility identifier для explicit restart action.
- [X] T007 [US2] Добавить в `apps/macos/Shared/Tests/SystemAudioPermissionUXTests.swift`, `apps/macos/Shared/Tests/MicrophoneCaptureServiceTests.swift` и `apps/macos/Shared/Tests/AppControlAccessibilityTests.swift` проверки truthful denied/restricted copy, отсутствия повторного prompt после denial, независимых permission actions и отсутствия false ready state.

## User Story 3 — системный звук и перезапуск (P1)

- [X] T004 [US3] В `apps/macos/RecApp/App/TwoBrainRecApp.swift` добавить bounded onboarding state для restart-required после открытия Screen & System Audio settings, explicit `Перезапустить GRAF` action и fresh permission refresh on launch/activation.
- [X] T005 [US3] В `apps/macos/RecApp/App/TwoBrainRecApp.swift` усилить `dismissModalWindowsForTermination()` для attached/detached sheets, active AppKit modal session и visible modal helper windows без force-kill и без ослабления ten-second cleanup reply.
- [X] T009 [US3] Добавить в `CHANGELOG.md` русскую запись `[Unreleased]` о фиксе Gatekeeper-инструкции, microphone recovery и relaunch cleanup с оговоркой no-account trust limitation.

## Validation and closeout

- [X] T010 Проверить формат shell scripts (`sh -n`), focused Swift tests для AppControl/SystemAudio/Installer/Packaging и server tests для public download page.
- [X] T011 Собрать локальный self-signed package существующей identity, проверить `codesign --verify --deep --strict`, bundle id и privacy descriptions; не устанавливать tracked public binary и не менять TCC.
- [X] T012 Запустить `infra/scripts/ci-local.sh`, проверить `git diff --check`, отсутствие новых driver/TCC paths и metadata-only evidence; после успешной проверки пометить закрытые задачи `[X]`.
