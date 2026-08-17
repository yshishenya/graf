# Tasks: надёжная установка и выдача разрешений GRAF

**Execution order**: T001–T002 establish the installer contract, T003–T005
implement permission and termination behavior, T006–T009 update executable
evidence and product documentation, then T010–T013 validate the whole slice.
T090–T095 establish and publish the Sparkle bootstrap/update channel. T096–T100
close the post-release Hardened Runtime microphone-registration regression.
These IDs are the next unused Feature 124 issue IDs; lower IDs are already
assigned to the parallel automatic-recording slice.

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
- [X] T013 [US2] Перед открытием панели микрофона повторно инициировать штатный AVFoundation permission flow для recovery после self-signed установки; сохранить normal request без повторного prompt после denial и добавить focused coverage.
- [X] T090 [US4] Собрать `v2026.07.24.2` updater-enabled bootstrap с HTTPS `SUFeedURL`, активным `SUPublicEDKey`, сохранением `pro.2brain.graf` и локальной signing identity; проверить app metadata, strict nested signature и package checksum.
- [X] T091 [US4] Проверить кандидат `v2026.07.24.2` против публичного предшественника `v2026.07.23.16` существующим `validate-app-updates.sh`, включая Sparkle continuity, designated requirement и монотонную CalVer.
- [X] T092 [US4] Довести release commit до актуального `master`, создать exact CalVer tag и draft GitHub Release с русскими notes, candidate ZIP/PKG и metadata-only Keychain attestation.
- [X] T093 [US4] Запустить защищённый `sign-graf-app-update.yml` из `master`; получить подписанный `GRAF-2026.07.24.2.zip`, appcast, checksum и cloud signing attestation без вывода приватного ключа.
- [X] T094 [US4] Опубликовать versioned ZIP/PKG и checksum в public runtime, заменить `graf-appcast.xml` последним, проверить HTTPS скачивание и Sparkle validator; сохранить предыдущий appcast/package для rollback.
- [X] T095 [US4] Закрыть release/deploy evidence: полный `infra/scripts/ci-local.sh`, `cd-remote.sh --dry-run/--execute`, GitHub Release и русская запись changelog о миграции `.1 → .2`.

## Post-release microphone registration correction

- [X] T096 [US2] Добавить в `apps/macos/Shared/Tests/InstallerLifecycleEvidenceTests.swift` source-contract проверки Audio Input entitlement и fail-closed сообщения validator до изменения сборки.
- [X] T097 [US2] Добавить `com.apple.security.device.audio-input` в подпись `GRAF.app` в `apps/macos/Installer/Scripts/build-local-installer.sh` и требовать его в `apps/macos/Scripts/validate-app-updates.sh` для teamless и team-identified сборок, сохранив отключение library validation только для teamless Sparkle.
- [X] T098 [US1] Обновить `apps/macos/Installer/README.md`, `specs/124-macos-permission-installer-relaunch/research.md` и `quickstart.md` с проверкой entitlement и ограничением перехода `.2 → .3`.
- [ ] T099 [US2] Выполнить focused tests, `sh -n`, локальную self-signed сборку и `apps/macos/Scripts/validate-app-updates.sh` против кандидата `.3` и предыдущего `.2`, подтвердив metadata-only evidence.
- [X] T100 [US4] Подготовить, подписать и опубликовать `v2026.07.24.3` через существующий Sparkle protected workflow, затем проверить публичные ZIP/PKG/appcast и обновление с `.2`.
- [X] T101 [US3] Добавить metadata-only ScreenCaptureKit functional probe для рассинхрона `CGPreflightScreenCaptureAccess`, сохранив fail-closed gate и запрет TCC reset.
