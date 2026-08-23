# Tasks: Windows desktop-приложение GRAF (Feature 200)

**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Risk/validation lane**: `high-risk-feature`. Capture, privacy, local custody,
WebView trust boundary, tray UX and packaging gates are mandatory.

**Release boundary**: no deploy, public release or Microsoft Store publication in
this slice. Implementation commits require explicit user approval after
validation.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: создать минимальный Windows solution, pin dependencies and test
surfaces without reviving a driver or second web UI.

- [X] T001 Создать `apps/windows/GrafWindows.sln` и базовые `apps/windows/Directory.Build.props` для C++/WinRT, stable Windows App SDK, Windows 10 22H2 x64 и standard-user процесса.
- [X] T002 [P] Создать `apps/windows/Directory.Packages.props` с pinned Windows App SDK/WebView2 SDK versions и явным запретом preview API.
- [X] T003 [P] Создать `apps/windows/Native/GrafAEC3/upstream.lock`, `apps/windows/Native/GrafAEC3/notices/README.md` и `apps/windows/scripts/build-graf-aec3.ps1` для pinned WebRTC AEC3 source/license identity.
- [X] T004 [P] Создать проекты `apps/windows/Tests/GrafWindowsCoreTests/`, `apps/windows/Tests/GrafWindowsContractTests/` и `apps/windows/Tests/GrafWindowsPackageTests/` с общим test configuration.
- [X] T005 [P] Создать `apps/windows/scripts/README.md` с reproducible build, synthetic fixture, evidence-redaction и x64-only/ARM64-gate правилами.

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: общие контракты и safety boundaries, без которых ни одна user story
не может начинать реализацию.

- [X] T006 Создать `apps/windows/RecApp/Contracts/WindowsDesktopContracts.h` с session states, reason codes, exact v5 wire values (`local-recording-manifest.v5`, `canonical-mix.v1`, `initial_mixed_recording`, `single_wav_v1`, `manifest/media/playback`), queue version и bridge envelope constants из contracts/.
- [X] T007 [P] Создать `apps/windows/RecApp/Core/WindowsDesktopSession.h` и `.cpp` с одним active-session invariant и idempotent transition validation.
- [X] T008 [P] Создать `apps/windows/RecApp/Diagnostics/MetadataSafeDiagnostics.h` и `.cpp` с allowlist полей, redacted endpoint fingerprint и запретом raw/content-bearing fields.
- [X] T009 [P] Создать `apps/windows/RecApp/Storage/AtomicFileStore.h` и `.cpp` для temp-write, flush, atomic-rename и bounded failure codes.
- [X] T010 Создать `apps/windows/RecApp/Permissions/WindowsReadinessGate.h` и `.cpp` для microphone privacy, endpoint, storage, WebView runtime и AAC readiness без смешения reason codes.
- [X] T011 Создать foundation `apps/windows/RecApp/Upload/DesktopApiClient.h` и `.cpp` с exact existing GRAF meeting/upload request builders, без MediaScribe/MinIO credentials; transport execution remains in the queue slice.
- [X] T012 Создать `specs/200-windows-desktop-app/parity-matrix.md` с mapping macOS Features 057/058/177/193/194/197 к Windows ownership, state, copy, accessibility и evidence.
- [X] T013 [P] Добавить `apps/windows/Tests/GrafWindowsCoreTests/ContractFixtures.cpp` с metadata-only fixtures для session, manifest, queue, bridge и safe error states.
- [X] T014 Провести Constitution/contract re-check и зафиксировать итоговую проверку в `specs/200-windows-desktop-app/plan.md` до старта user story phases.

## Phase 3: User Story 1 — Нативно записать встречу (Priority: P1) 🎯 First Windows slice

**Goal**: native Record/Pause/Resume/Stop и локальный v5-пакет работают при
недоступном WebView и не выдают неподтверждённую запись за нормальную.

**Independent test**: core/contract tests плюс synthetic audio запускают native
session, WebView stub недоступен, выполняют Record/Pause/Resume/Stop и проверяют
indicator, state machine, package integrity и idempotent finalization.

### Tests for User Story 1

- [ ] T015 [P] [US1] Написать state/transition tests в `apps/windows/Tests/GrafWindowsCoreTests/WindowsDesktopSessionTests.cpp` для readiness, Record/Pause/Resume/Stop, duplicate Stop и finalization states.
- [ ] T016 [P] [US1] Написать native/web independence contract tests в `apps/windows/Tests/GrafWindowsContractTests/NativeCaptureWebFailureTests.cpp` для WebView offline/reload/close во время capture.
- [ ] T017 [P] [US1] Написать synthetic framing/AEC contract fixtures в `apps/windows/Tests/GrafWindowsCoreTests/RecordingAudioTimelineTests.cpp` для 480-sample frames, clock/gap/overflow и no-raw-fallback.

### Implementation for User Story 1

- [ ] T018 [US1] Реализовать `apps/windows/RecApp/Audio/WasapiEndpointEnumerator.h` и `.cpp` для default/selected render и physical microphone endpoint snapshots без Stereo Mix/virtual driver.
- [ ] T019 [US1] Реализовать `apps/windows/RecApp/Audio/WasapiCaptureWorker.h` и `.cpp` с event-driven shared-mode workers, bounded batches, QPC/WASAPI position и callback no-I/O правилами.
- [ ] T020 [US1] Реализовать `apps/windows/Native/GrafAEC3/GrafAEC3.h` и `.cpp` как минимальный pinned C ABI wrapper с reference-before-microphone order и explicit process errors.
- [ ] T021 [US1] Реализовать `apps/windows/RecApp/Audio/RecordingAudioTimeline.h` и `.cpp` как единственный PTS/route-generation owner с canonical 48 kHz mono, exact 10 ms framing и trusted-prefix policy.
- [ ] T022 [US1] Реализовать `apps/windows/RecApp/Recording/V5LocalRecordingWriter.h` и `.cpp` для PCM 16 kHz mono WAV, AAC-LC 48 kHz mono M4A, hash/byte/duration validation и atomic package finalization.
- [ ] T023 [US1] Реализовать `apps/windows/RecApp/Capture/WindowsCaptureSessionController.h` и `.cpp` для readiness gate, worker lifetime, Pause zero-mic semantics, Stop idempotency и finalization result.
- [ ] T024 [US1] Реализовать `apps/windows/RecApp/Shell/RecordingIndicator.h` и `.cpp` с persistent native strip, tray state и one-action Stop вне WebView.
- [ ] T025 [US1] Реализовать `apps/windows/RecApp/Permissions/WindowsPermissionRecovery.h` и `.cpp` для microphone/privacy/endpoint/storage recovery и bounded user-facing reason actions.
- [ ] T026 [US1] Добавить integration scenario в `apps/windows/Tests/GrafWindowsPackageTests/NativeRecordingOfflineWebViewTests.cpp` и прогнать acceptance matrix из User Story 1.

## Phase 4: User Story 2 — Тот же кабинет, что на macOS (Priority: P1)

**Goal**: WebView2 загружает server-owned cabinet routes с exact-origin policy,
а native bridge только показывает bounded state и открывает разрешённые native
settings/diagnostics.

**Independent test**: route/bridge contract matrix сравнивает Windows WebView2 и
macOS route/state matrix, включая hostile navigation/message cases, без запуска
capture.

### Tests for User Story 2

- [ ] T027 [P] [US2] Написать route policy tests в `apps/windows/Tests/GrafWindowsContractTests/WebViewRoutePolicyTests.cpp` для approved routes, redirects, external browser, file/data/javascript и native-only paths.
- [ ] T028 [P] [US2] Написать bridge schema/security tests в `apps/windows/Tests/GrafWindowsContractTests/WebViewBridgeEnvelopeTests.cpp` для origin, nonce, replay, payload limits, direction и denied commands.

### Implementation for User Story 2

- [ ] T029 [US2] Реализовать `apps/windows/RecApp/Web/WebViewRoutePolicy.h` и `.cpp` с normalized exact origin и route-kind allowlist, не используя broad substring matching.
- [ ] T030 [US2] Реализовать `apps/windows/RecApp/Web/WebView2Host.h` и `.cpp` с Evergreen readiness, standard-user settings, disabled generic host objects и lifecycle isolation.
- [ ] T031 [US2] Реализовать `apps/windows/RecApp/Web/WebViewBridge.h` и `.cpp` с versioned JSON envelope, ephemeral nonce, 64 KiB/depth limits, typed allowlist и bounded ack/error.
- [ ] T032 [US2] Подключить `apps/windows/RecApp/Shell/CabinetWindow.h` и `.cpp` к `/desktop/meetings`, detail, settings, auth recovery, review/deletion-report routes без копирования server business logic.
- [ ] T033 [US2] Добавить runtime/unavailable/recovery UI в `apps/windows/RecApp/Web/WebRuntimeState.h` и `.cpp`, сохранив native capture/custody при WebView/network failure.
- [ ] T034 [US2] Добавить parity/route smoke в `apps/windows/Tests/GrafWindowsPackageTests/WebViewCabinetParityTests.cpp` по `specs/200-windows-desktop-app/parity-matrix.md`.

## Phase 5: User Story 3 — Сохранить локально и догрузить после сбоя (Priority: P1)

**Goal**: запись сначала попадает в локальную custody, затем queue v2 безопасно
возобновляет upload после offline/relaunch/auth/network/wake без дублей.

**Independent test**: fault-injection test завершает synthetic package offline,
перезапускает app, частично принимает диапазон и проверяет server-truth
reconciliation, duplicate prevention и purge semantics.

### Tests for User Story 3

- [ ] T035 [P] [US3] Написать queue/ledger contract tests в `apps/windows/Tests/GrafWindowsCoreTests/DesktopUploadQueueV2Tests.cpp` для atomic write, quarantine, immutable identity, accepted ranges и retry owner.
- [ ] T036 [P] [US3] Написать custody recovery tests в `apps/windows/Tests/GrafWindowsContractTests/DesktopUploadRecoveryTests.cpp` для offline/relaunch/auth/wake, partial accept и duplicate meeting/upload prevention.

### Implementation for User Story 3

- [ ] T037 [US3] Реализовать `apps/windows/RecApp/Recording/LocalRecordingPackage.h` и `.cpp` для v5 manifest, package integrity, hashes, duration and local deletion registration.
- [ ] T038 [US3] Реализовать `apps/windows/RecApp/Upload/DesktopUploadQueueService.h` и `.cpp` с existing `desktop-upload-queue.v2`, atomic ledger, quarantine и server-truth reconciliation.
- [ ] T039 [US3] Реализовать `apps/windows/RecApp/Upload/DesktopUploadRecoveryScheduler.h` и `.cpp` для launch, activation, auth/network recovery, wake и scheduled bounded retry без WebView route.
- [ ] T040 [US3] Реализовать `apps/windows/RecApp/Upload/DesktopLocalPurgeService.h` и `.cpp` с deletion/tombstone/unrecoverability gate и безопасной локальной очисткой.
- [ ] T041 [US3] Подключить `apps/windows/RecApp/Shell/CustodyStatusProjection.h` и `.cpp` к bounded native/web custody summary без paths, tokens, signed URLs или content.
- [ ] T042 [US3] Добавить package/queue fault smoke в `apps/windows/Tests/GrafWindowsPackageTests/DesktopUploadCustodySmokeTests.cpp` и закрыть сценарии User Story 3.

## Phase 6: User Story 4 — Честно показать ограничения Windows audio (Priority: P1)

**Goal**: endpoint/clock/power/protected-audio failures fail closed or degrade
явно, сохраняя indicator/Stop и metadata-only diagnostics.

**Independent test**: synthetic and hardware fault matrix injects permission,
endpoint, clock, gap, overflow, sleep/wake, protected-audio and disk failures.

### Tests for User Story 4

- [ ] T043 [P] [US4] Написать fault-state tests в `apps/windows/Tests/GrafWindowsCoreTests/CaptureFaultStateTests.cpp` для endpoint invalidation, clock discontinuity, overflow, protected audio, disk full и service restart.
- [ ] T044 [P] [US4] Написать metadata-redaction tests в `apps/windows/Tests/GrafWindowsContractTests/WindowsDiagnosticsRedactionTests.cpp` для запретных fields, hashes, paths, transcript/audio content и reason-code bounds.

### Implementation for User Story 4

- [ ] T045 [US4] Реализовать `apps/windows/RecApp/Audio/ClockMapper.h` и `.cpp` с QPC/WASAPI mapping, monotonicity, route generations, drift/gap validation и no-wall-clock-padding.
- [ ] T046 [US4] Реализовать `apps/windows/RecApp/Capture/CaptureFaultRecovery.h` и `.cpp` для endpoint/service/power transitions, trusted-prefix finalization и explicit safe recovery actions.
- [ ] T047 [US4] Реализовать `apps/windows/RecApp/Diagnostics/CaptureHealthProjection.h` и `.cpp` для bounded counters, safe reason codes и native indicator/bridge state projection.
- [ ] T048 [US4] Добавить `apps/windows/scripts/validate-audio-contract.ps1` с synthetic, hardware-matrix, fault-injection и custody modes из quickstart.md.
- [ ] T049 [US4] Добавить `apps/windows/Tests/GrafWindowsPackageTests/WindowsHardwareEvidenceSchemaTests.cpp` для x64 OS matrix, source/device class, state and metadata-only evidence schema.

## Phase 7: User Story 5 — Автоматическая запись по verified target (Priority: P2)

**Goal**: target-scoped auto-record сохраняет macOS semantics: verified identity,
8-second countdown, explicit opt-in, reversible policy, prerequisites and Stop.

**Independent test**: registry fixtures distinguish immediate start, skip,
timeout, saved policy, unknown target, media playback and missing prerequisites.

### Tests for User Story 5

- [ ] T050 [P] [US5] Написать target identity/policy tests в `apps/windows/Tests/GrafWindowsCoreTests/VerifiedTargetPolicyTests.cpp` для exact executable proof, registry version, unknown name и reversible opt-in.
- [ ] T051 [P] [US5] Написать prompt/accessibility tests в `apps/windows/Tests/GrafWindowsContractTests/AutomaticRecordingPromptTests.cpp` для countdown, immediate start, skip, timeout и missing prerequisites.

### Implementation for User Story 5

- [ ] T052 [US5] Реализовать `apps/windows/RecApp/MeetingDetection/VerifiedTargetRegistry.h` и `.cpp` с bounded executable identity/publisher proof, user-scoped policy и stable fingerprint.
- [ ] T053 [US5] Реализовать `apps/windows/RecApp/MeetingDetection/WindowsTargetDetector.h` и `.cpp` без запуска по arbitrary process name или ordinary media playback.
- [ ] T054 [US5] Реализовать `apps/windows/RecApp/MeetingDetection/AutomaticRecordingPolicy.h` и `.cpp` с 8-second countdown, «Записать сейчас», «Пропустить» и reversible «Всегда писать это приложение».
- [ ] T055 [US5] Реализовать `apps/windows/RecApp/Shell/AutomaticRecordingPrompt.h` и `.cpp` с keyboard/screen-reader accessible actions и тем же readiness/indicator/Stop path, что у manual Record.
- [ ] T056 [US5] Добавить `apps/windows/Tests/GrafWindowsPackageTests/AutomaticRecordingSmokeTests.cpp` с unknown target/media playback zero-start и explicit consent evidence.

## Phase 8: Polish, accessibility, packaging and cross-cutting validation

- [ ] T057 [P] Реализовать `apps/windows/RecApp/Shell/AccessibilityState.h` и `.cpp` для keyboard focus, accessible names/descriptions, screen-reader state, High Contrast, 200% DPI и reduced-motion semantics.
- [ ] T058 [P] Добавить `apps/windows/scripts/validate-webview-boundary.ps1` с hostile-origin, redirect, nonce, replay, oversized/deep-payload, denied-command и runtime-repair scenarios.
- [ ] T059 [P] Создать `apps/windows/Installer/Package.appxmanifest`, `apps/windows/Installer/GrafWindows.Package.wapproj` и App Installer metadata для signed x64 MSIX without driver/service/elevation.
- [ ] T060 Реализовать `apps/windows/scripts/validate-package-smoke.ps1` для install/update/interrupted-update/rollback/uninstall, WebView2 repair и preservation of local queue/recordings.
- [ ] T061 Провести `apps/windows/Tests/GrafWindowsPackageTests/AccessibilityAndBrandDistanceTests.cpp` и оформить review evidence по `specs/200-windows-desktop-app/checklists/ux.md`.
- [ ] T062 Обновить `CHANGELOG.md` на русском описанием Windows architecture/limitations/validation, не заявляя release, ARM64 или process-isolated capture без evidence.
- [ ] T063 Выполнить полный `specs/200-windows-desktop-app/quickstart.md`, Windows x64 hardware/package evidence и `infra/scripts/ci-local.sh --fast`; зафиксировать exact SHA, skipped ARM64 lane и known limitations.
- [ ] T064 Провести финальный review `specs/200-windows-desktop-app/checklists/requirements.md`, `audio-capture.md`, `advanced-routing.md`, `security.md`, `ux.md`, `plan.md` и `tasks.md`; не запускать deploy/release без отдельного approval.

## Dependencies & Execution Order

### Phase dependencies

- Phase 1 → Phase 2; foundational contracts block every user story.
- US1 → native capture/session primitives. US2 and US3 may start after Phase 2,
  but US3 consumes the package/queue contracts created by US1.
- US4 hardens US1 capture faults and must pass before release-readiness tasks.
- US5 consumes the native session and indicator from US1 and the parity/copy map
  from US2.
- Phase 8 follows the desired stories and is the only closeout phase.

### Parallel opportunities

- After T001: T002–T005 can run in parallel.
- After T006–T011: T007–T009, T012–T013 can run in parallel where file ownership
  does not overlap.
- In each story, contract tests marked `[P]` can be prepared before implementation.
- After Phase 2: US2 WebView policy and US5 registry fixtures can progress in
  parallel with US1 capture implementation; they cannot claim an independent
  product-support claim
  validation until their native contracts are integrated.

### First-slice strategy

1. Complete Phase 1 and Phase 2.
2. Complete US1 with synthetic audio and native/WebView independence proof.
3. Complete US2 and US3 before any user-facing Windows distribution claim.
4. Complete US4 fault/hardware evidence; add US5 only after manual capture truth
   is stable.
5. Complete accessibility, signed-package and repository gates. Stop before
   release/deploy until explicit approval.

## Notes

- `[P]` означает разные файлы и отсутствие зависимости от незавершённой задачи.
- `[US#]` связывает задачу с independently testable user story.
- Все path names — будущая Windows surface; не копировать macOS Swift UI или
  server business logic в эти файлы.
- Ни одна задача не разрешает raw-microphone fallback, direct MediaScribe/MinIO
  egress, driver/service installation или второй web frontend.

## Requirements traceability

| Requirement | Tasks |
|---|---|
| FR-001 | T001, T002, T059 |
| FR-002 | T012, T032, T057, T061, T062 |
| FR-003 | T029, T032, T034 |
| FR-004 | T010, T023, T024, T033 |
| FR-005 | T027, T029, T058 |
| FR-006 | T028, T031, T058 |
| FR-007 | T018, T019, T048 |
| FR-008 | T010, T018, T025, T048 |
| FR-009 | T017, T019, T021, T048 |
| FR-010 | T017, T020, T021, T043 |
| FR-011 | T022, T037, T049 |
| FR-012 | T008, T009, T022, T037, T044 |
| FR-013 | T009, T035, T038 |
| FR-014 | T011, T038, T039 |
| FR-015 | T024, T026, T047, T057 |
| FR-016 | T050, T051, T052, T053, T054, T055, T056 |
| FR-017 | T043, T046, T047, T048 |
| FR-018 | T017, T045 |
| FR-019 | T001, T030, T059 |
| FR-020 | T010, T030, T033, T059, T060 |
| FR-021 | T008, T013, T044, T049 |
| FR-022 | T040, T041, T060 |
| SC-001 | T010, T030, T063 |
| SC-002 | T012, T034, T061, T064 |
| SC-003 | T017, T021, T022, T048, T063 |
| SC-004 | T016, T024, T043, T046, T047, T063 |
| SC-005 | T035, T036, T038, T039, T040, T041, T042, T063 |
| SC-006 | T028, T031, T044, T058 |
| SC-007 | T050, T051, T054, T056 |
| SC-008 | T059, T060, T063 |
| SC-009 | T051, T055, T057, T061 |
| SC-010 | T002, T003, T049, T059, T063 |
