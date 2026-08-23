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

- [X] T015 [P] [US1] Написать state/transition tests в `apps/windows/Tests/GrafWindowsCoreTests/WindowsDesktopSessionTests.cpp` для readiness, Record/Pause/Resume/Stop, duplicate Stop и finalization states.
- [X] T016 [P] [US1] Написать native/web independence contract tests в `apps/windows/Tests/GrafWindowsContractTests/NativeCaptureWebFailureTests.cpp` для WebView offline/reload/close во время capture.
- [X] T017 [P] [US1] Написать synthetic framing/AEC contract fixtures в `apps/windows/Tests/GrafWindowsCoreTests/RecordingAudioTimelineTests.cpp` для 480-sample frames, clock/gap/overflow и no-raw-fallback.

### Implementation for User Story 1

- [X] T018 [US1] Реализовать `apps/windows/RecApp/Audio/WasapiEndpointEnumerator.h` и `.cpp` для default/selected render и physical microphone endpoint snapshots без Stereo Mix/virtual driver.
- [X] T019 [US1] Реализовать `apps/windows/RecApp/Audio/WasapiCaptureWorker.h` и `.cpp` с event-driven shared-mode workers, bounded batches, QPC/WASAPI position и callback no-I/O правилами.
- [X] T020 [US1] Реализовать `apps/windows/Native/GrafAEC3/GrafAEC3.h` и `.cpp` как минимальный pinned C ABI wrapper с reference-before-microphone order и explicit process errors.
- [X] T021 [US1] Реализовать `apps/windows/RecApp/Audio/RecordingAudioTimeline.h` и `.cpp` как единственный PTS/route-generation owner с canonical 48 kHz mono, exact 10 ms framing и trusted-prefix policy.
- [X] T022 [US1] Реализовать `apps/windows/RecApp/Recording/V5LocalRecordingWriter.h` и `.cpp` для PCM 16 kHz mono WAV, AAC-LC 48 kHz mono M4A, hash/byte/duration validation и atomic package finalization.
- [X] T023 [US1] Реализовать `apps/windows/RecApp/Capture/WindowsCaptureSessionController.h` и `.cpp` для readiness gate, worker lifetime, Pause zero-mic semantics, Stop idempotency и finalization result.
- [X] T024 [US1] Реализовать `apps/windows/RecApp/Shell/RecordingIndicator.h` и `.cpp` с persistent native strip, tray state и one-action Stop вне WebView.
- [X] T025 [US1] Реализовать `apps/windows/RecApp/Permissions/WindowsPermissionRecovery.h` и `.cpp` для microphone/privacy/endpoint/storage recovery и bounded user-facing reason actions.
- [X] T026 [US1] Добавить integration scenario в `apps/windows/Tests/GrafWindowsPackageTests/NativeRecordingOfflineWebViewTests.cpp` и прогнать acceptance matrix из User Story 1.

## Phase 4: User Story 2 — Тот же кабинет, что на macOS (Priority: P1)

**Goal**: WebView2 загружает server-owned cabinet routes с exact-origin policy,
а native bridge только показывает bounded state и открывает разрешённые native
settings/diagnostics.

**Independent test**: route/bridge contract matrix сравнивает Windows WebView2 и
macOS route/state matrix, включая hostile navigation/message cases, без запуска
capture.

### Tests for User Story 2

- [X] T027 [P] [US2] Написать route policy tests в `apps/windows/Tests/GrafWindowsContractTests/WebViewRoutePolicyTests.cpp` для approved routes, redirects, external browser, file/data/javascript и native-only paths.
- [X] T028 [P] [US2] Написать bridge schema/security tests в `apps/windows/Tests/GrafWindowsContractTests/WebViewBridgeEnvelopeTests.cpp` для origin, nonce, replay, payload limits, direction и denied commands.

### Implementation for User Story 2

- [X] T029 [US2] Реализовать `apps/windows/RecApp/Web/WebViewRoutePolicy.h` и `.cpp` с normalized exact origin и route-kind allowlist, не используя broad substring matching.
- [X] T030 [US2] Реализовать `apps/windows/RecApp/Web/WebView2Host.h` и `.cpp` с Evergreen readiness, standard-user settings, disabled generic host objects и lifecycle isolation.
- [X] T031 [US2] Реализовать `apps/windows/RecApp/Web/WebViewBridge.h` и `.cpp` с versioned JSON envelope, ephemeral nonce, 64 KiB/depth limits, typed allowlist и bounded ack/error.
- [X] T032 [US2] Подключить `apps/windows/RecApp/Shell/CabinetWindow.h` и `.cpp` к `/desktop/meetings`, detail, settings, auth recovery, review/deletion-report routes без копирования server business logic.
- [X] T033 [US2] Добавить runtime/unavailable/recovery UI в `apps/windows/RecApp/Web/WebRuntimeState.h` и `.cpp`, сохранив native capture/custody при WebView/network failure.
- [X] T034 [US2] Добавить parity/route smoke в `apps/windows/Tests/GrafWindowsPackageTests/WebViewCabinetParityTests.cpp` по `specs/200-windows-desktop-app/parity-matrix.md`.

## Phase 5: User Story 3 — Сохранить локально и догрузить после сбоя (Priority: P1)

**Goal**: запись сначала попадает в локальную custody, затем queue v2 безопасно
возобновляет upload после offline/relaunch/auth/network/wake без дублей.

**Independent test**: fault-injection test завершает synthetic package offline,
перезапускает app, частично принимает диапазон и проверяет server-truth
reconciliation, duplicate prevention и purge semantics.

### Tests for User Story 3

- [X] T035 [P] [US3] Написать queue/ledger contract tests в `apps/windows/Tests/GrafWindowsCoreTests/DesktopUploadQueueV2Tests.cpp` для atomic write, quarantine, immutable identity, accepted ranges и retry owner.
- [X] T036 [P] [US3] Написать custody recovery tests в `apps/windows/Tests/GrafWindowsContractTests/DesktopUploadRecoveryTests.cpp` для offline/relaunch/auth/wake, partial accept и duplicate meeting/upload prevention.

### Implementation for User Story 3

- [X] T037 [US3] Реализовать `apps/windows/RecApp/Recording/LocalRecordingPackage.h` и `.cpp` для v5 manifest, package integrity, hashes, duration and local deletion registration.
- [X] T038 [US3] Реализовать `apps/windows/RecApp/Upload/DesktopUploadQueueService.h` и `.cpp` с existing `desktop-upload-queue.v2`, atomic ledger, quarantine и server-truth reconciliation.
- [X] T039 [US3] Реализовать `apps/windows/RecApp/Upload/DesktopUploadRecoveryScheduler.h` и `.cpp` для launch, activation, auth/network recovery, wake и scheduled bounded retry без WebView route.
- [X] T040 [US3] Реализовать `apps/windows/RecApp/Upload/DesktopLocalPurgeService.h` и `.cpp` с deletion/tombstone/unrecoverability gate и безопасной локальной очисткой.
- [X] T041 [US3] Подключить `apps/windows/RecApp/Shell/CustodyStatusProjection.h` и `.cpp` к bounded native/web custody summary без paths, tokens, signed URLs или content.
- [X] T042 [US3] Добавить package/queue fault smoke в `apps/windows/Tests/GrafWindowsPackageTests/DesktopUploadCustodySmokeTests.cpp` и закрыть сценарии User Story 3.

## Phase 6: User Story 4 — Честно показать ограничения Windows audio (Priority: P1)

**Goal**: endpoint/clock/power/protected-audio failures fail closed or degrade
явно, сохраняя indicator/Stop и metadata-only diagnostics.

**Independent test**: synthetic and hardware fault matrix injects permission,
endpoint, clock, gap, overflow, sleep/wake, protected-audio and disk failures.

### Tests for User Story 4

- [X] T043 [P] [US4] Написать fault-state tests в `apps/windows/Tests/GrafWindowsCoreTests/CaptureFaultStateTests.cpp` для endpoint invalidation, clock discontinuity, overflow, protected audio, disk full и service restart.
- [X] T044 [P] [US4] Написать metadata-redaction tests в `apps/windows/Tests/GrafWindowsContractTests/WindowsDiagnosticsRedactionTests.cpp` для запретных fields, hashes, paths, transcript/audio content и reason-code bounds.

### Implementation for User Story 4

- [X] T045 [US4] Реализовать `apps/windows/RecApp/Audio/ClockMapper.h` и `.cpp` с QPC/WASAPI mapping, monotonicity, route generations, drift/gap validation и no-wall-clock-padding.
- [X] T046 [US4] Реализовать `apps/windows/RecApp/Capture/CaptureFaultRecovery.h` и `.cpp` для endpoint/service/power transitions, trusted-prefix finalization и explicit safe recovery actions.
- [X] T047 [US4] Реализовать `apps/windows/RecApp/Diagnostics/CaptureHealthProjection.h` и `.cpp` для bounded counters, safe reason codes и native indicator/bridge state projection.
- [X] T048 [US4] Добавить `apps/windows/scripts/validate-audio-contract.ps1` с synthetic, hardware-matrix, fault-injection и custody modes из quickstart.md.
- [X] T049 [US4] Добавить `apps/windows/Tests/GrafWindowsPackageTests/WindowsHardwareEvidenceSchemaTests.cpp` для x64 OS matrix, source/device class, state and metadata-only evidence schema.

## Phase 7: User Story 5 — Автоматическая запись по verified target (Priority: P2)

**Goal**: target-scoped auto-record сохраняет macOS semantics: verified identity,
8-second countdown, explicit opt-in, reversible policy, prerequisites and Stop.

**Independent test**: registry fixtures distinguish immediate start, skip,
timeout, saved policy, unknown target, media playback and missing prerequisites.

### Tests for User Story 5

- [X] T050 [P] [US5] Написать target identity/policy tests в `apps/windows/Tests/GrafWindowsCoreTests/VerifiedTargetPolicyTests.cpp` для exact executable proof, registry version, unknown name и reversible opt-in.
- [X] T051 [P] [US5] Написать prompt/accessibility tests в `apps/windows/Tests/GrafWindowsContractTests/AutomaticRecordingPromptTests.cpp` для countdown, immediate start, skip, timeout и missing prerequisites.

### Implementation for User Story 5

- [X] T052 [US5] Реализовать `apps/windows/RecApp/MeetingDetection/VerifiedTargetRegistry.h` и `.cpp` с bounded executable identity/publisher proof, user-scoped policy и stable fingerprint.
- [X] T053 [US5] Реализовать `apps/windows/RecApp/MeetingDetection/WindowsTargetDetector.h` и `.cpp` без запуска по arbitrary process name или ordinary media playback.
- [X] T054 [US5] Реализовать `apps/windows/RecApp/MeetingDetection/AutomaticRecordingPolicy.h` и `.cpp` с 8-second countdown, «Записать сейчас», «Пропустить» и reversible «Всегда писать это приложение».
- [X] T055 [US5] Реализовать `apps/windows/RecApp/Shell/AutomaticRecordingPrompt.h` и `.cpp` с keyboard/screen-reader accessible actions и тем же readiness/indicator/Stop path, что у manual Record.
- [X] T056 [US5] Добавить `apps/windows/Tests/GrafWindowsPackageTests/AutomaticRecordingSmokeTests.cpp` с unknown target/media playback zero-start и explicit consent evidence.

## Phase 8: Polish, accessibility, packaging and cross-cutting implementation

- [X] T057 [P] Реализовать `apps/windows/RecApp/Shell/AccessibilityState.h` и `.cpp` для keyboard focus, accessible names/descriptions, screen-reader state, High Contrast, 200% DPI и reduced-motion semantics.
- [X] T058 [P] Добавить `apps/windows/scripts/validate-webview-boundary.ps1` с hostile-origin, redirect, nonce, replay, oversized/deep-payload, denied-command и runtime-repair scenarios.
- [X] T059 [P] Создать `apps/windows/Installer/Package.appxmanifest`, `apps/windows/Installer/GrafWindows.Package.wapproj` и App Installer metadata для signed x64 MSIX without driver/service/elevation.
- [X] T060 Реализовать `apps/windows/scripts/validate-package-smoke.ps1` для install/update/interrupted-update/rollback/uninstall, WebView2 repair и preservation of local queue/recordings.
- [X] T061 Провести `apps/windows/Tests/GrafWindowsPackageTests/AccessibilityAndBrandDistanceTests.cpp` и оформить review evidence по `specs/200-windows-desktop-app/checklists/ux.md`.
- [X] T062 Обновить `CHANGELOG.md` на русском описанием Windows architecture/limitations/validation, не заявляя release, ARM64 или process-isolated capture без evidence.

## Dependencies & Execution Order

### Phase dependencies

- Phase 1 → Phase 2; foundational contracts block every user story.
- US1 → native capture/session primitives. US2 and US3 may start after Phase 2,
  but US3 consumes the package/queue contracts created by US1.
- US4 hardens US1 capture faults and must pass before release-readiness tasks.
- US5 consumes the native session and indicator from US1 and the parity/copy map
  from US2.
- Phase 8 follows the desired stories and contains implementation polish only.
- Phase 9 convergence must complete before the Phase 10 closeout tasks T063/T064.

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
| FR-003 | T029, T032, T034, T066 |
| FR-004 | T010, T023, T024, T033, T065 |
| FR-005 | T027, T029, T058, T066 |
| FR-006 | T028, T031, T058, T066 |
| FR-007 | T018, T019, T048 |
| FR-008 | T010, T018, T025, T048 |
| FR-009 | T017, T019, T021, T048 |
| FR-010 | T017, T020, T021, T043 |
| FR-011 | T022, T037, T049 |
| FR-012 | T008, T009, T022, T037, T044 |
| FR-013 | T009, T035, T038, T069 |
| FR-014 | T011, T038, T039, T069 |
| FR-015 | T024, T026, T047, T057, T068 |
| FR-016 | T050, T051, T052, T053, T054, T055, T056 |
| FR-017 | T043, T046, T047, T048 |
| FR-018 | T017, T045 |
| FR-019 | T001, T030, T059, T065, T070 |
| FR-020 | T010, T030, T033, T059, T060, T066, T070 |
| FR-021 | T008, T013, T044, T049 |
| FR-022 | T040, T041, T060 |
| SC-001 | T010, T030, T063 |
| SC-002 | T012, T034, T061, T064 |
| SC-003 | T017, T021, T022, T048, T063 |
| SC-004 | T016, T024, T043, T046, T047, T063, T068, T071 |
| SC-005 | T035, T036, T038, T039, T040, T041, T042, T063, T069, T071 |
| SC-006 | T028, T031, T044, T058 |
| SC-007 | T050, T051, T054, T056 |
| SC-008 | T059, T060, T063, T070, T071 |
| SC-009 | T051, T055, T057, T061 |
| SC-010 | T002, T003, T049, T059, T063 |

## Phase 9: Convergence — реальная сборка Windows shell

Convergence review 2026-08-24 обнаружил, что текущий portable contract surface
не является запускаемым Windows-приложением: entry point и часть native-моделей
не подключены к WinUI/WebView2/capture runtime. Эти задачи продолжают Feature
200 и не отменяют открытые Windows x64, hardware, package и release gates.

- [X] T065 [US1] Подключить `apps/windows/RecApp/AppMain.cpp` к реальному WinUI 3/Windows App SDK lifecycle с одним standard-user окном и native session composition; убрать пустой Windows `wWinMain` stub (FR-004, FR-019; implementation complete, Windows host build remains T071).
- [X] T066 [US2] Реализовать фактический WebView2 control в `apps/windows/RecApp/Web/WebView2Host.*` и `apps/windows/RecApp/Shell/CabinetWindow.*`: Evergreen readiness, approved-origin navigation events, fresh nonce/web-message bridge events, runtime unavailable/recreate и загрузка `/desktop/meetings` (FR-003, FR-005, FR-006, FR-020; implementation complete, Windows host evidence remains T071).
- [ ] T067 [US1] Собрать native capture pipeline в `apps/windows/RecApp/Capture/WindowsCaptureSessionController.*`: endpoint enumeration, pinned GrafAEC3 adapter, `RecordingAudioTimeline`, v5 writer/finalizer и WebView-independent local custody; сохранить fail-closed и idempotent Stop (FR-009–FR-012, US1/AC1–AC4; partial, HIGH).
- [X] T068 [US1] Подключить `apps/windows/RecApp/Shell/RecordingIndicator.*` к persistent native WinUI status strip с accessible status и one-action Stop, переживающим WebView close/minimize/network failure (FR-015, SC-004; implementation complete, Windows UI matrix remains T071).
- [ ] T069 [US3] Подключить реальный стандартный HTTP transport существующих GRAF desktop API к `apps/windows/RecApp/Upload/DesktopApiClient.*`, `apps/windows/RecApp/Upload/DesktopHttpTransport.*` и `DesktopUploadRecoveryScheduler.*`, включая auth/network/wake recovery, accepted ranges и server-truth reconciliation без MediaScribe/MinIO egress (FR-013–FR-014, SC-005; transport core added, queue/auth/reconciliation integration remains, HIGH).
- [ ] T070 [US2] Завершить `apps/windows/Installer/Package.appxmanifest`, `GrafWindows.Package.wapproj` и package assets/dependency declarations для собираемого signed x64 MSIX без elevation/driver/service; затем подтвердить clean-image install/update/rollback smoke (FR-019–FR-020, SC-008; partial, HIGH).
- [ ] T071 [P] Провести Windows x64 validation из `specs/200-windows-desktop-app/quickstart.md` для T065–T070, зафиксировать exact SHA, hardware/AEC3/WebView2/Media Foundation/MSIX evidence и оставить ARM64 lane явно skipped до отдельного proof (T063, SC-001/003/004/005/008/010; missing, HIGH).

## Phase 10: Closeout — evidence and final review

- [ ] T063 Выполнить полный `specs/200-windows-desktop-app/quickstart.md`, Windows x64 hardware/package evidence и `infra/scripts/ci-local.sh --fast`; зафиксировать exact SHA, skipped ARM64 lane и known limitations.
- [ ] T064 Провести финальный review `specs/200-windows-desktop-app/checklists/requirements.md`, `audio-capture.md`, `advanced-routing.md`, `security.md`, `ux.md`, `plan.md` и `tasks.md`; не запускать deploy/release без отдельного approval.
