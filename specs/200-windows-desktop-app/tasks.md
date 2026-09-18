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

**Goal**: WebView2 загружает server-owned cabinet routes с exact-origin policy.
Мост принимает только `request_app_quit` и действия `local_recording` над
известной записью с повторной проверкой нативного состояния. В обратном
направлении передаются `native_ready` и строки `local_recordings`. Настройки,
диагностика и восстановление доступны через нативные элементы и разрешённую
навигацию, без устаревших команд моста.

**Independent test**: route/bridge contract matrix сравнивает Windows WebView2 и
macOS route/state matrix, включая hostile navigation/message cases, без запуска
capture.

### Tests for User Story 2

- [X] T027 [P] [US2] Написать route policy tests в `apps/windows/Tests/GrafWindowsContractTests/WebViewRoutePolicyTests.cpp` для approved routes, redirects, external browser, file/data/javascript и native-only paths.
- [X] T028 [P] [US2] Написать bridge schema/security tests в `apps/windows/Tests/GrafWindowsContractTests/WebViewBridgeEnvelopeTests.cpp` для origin, nonce, replay, payload limits, direction и denied commands.

### Implementation for User Story 2

- [X] T029 [US2] Реализовать `apps/windows/RecApp/Web/WebViewRoutePolicy.h` и `.cpp` с normalized exact origin и route-kind allowlist, не используя broad substring matching.
- [X] T030 [US2] Реализовать `apps/windows/RecApp/Web/WebView2Host.h` и `.cpp` с Evergreen readiness, standard-user settings, disabled generic host objects и lifecycle isolation.
- [X] T031 [US2] Реализовать `apps/windows/RecApp/Web/WebViewBridge.h` и `.cpp` с versioned JSON envelope, ephemeral nonce, 64 KiB/depth limits, typed allowlist и ограниченными внутренними кодами отказа проверки. Уточнение T083 от 2026-09-06: `ack`/`ack_display` не поддерживаются и не доказывают сохранение, отправку или удаление.
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

  Историческое уточнение 2026-09-06: `[X]` относится к прежнему локальному
  прототипу, а не к проверенной серверной очистке. Удалённые API
  `purge(..., LocalPurgeProof)` и маркер `registerLocalPurge` не доказывали
  deletion/tombstone/unrecoverability. Серверная очистка и её ACK остаются
  заблокированы до достоверной авторизации конкретной установки и проверки
  по T083 (#6640); явное удаление локальной копии пользователем — отдельный
  сценарий, не подтверждение серверной очистки.

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

  Историческое уточнение 2026-09-06: `CaptureHealthProjection.*` удалён как
  неиспользуемая заготовка. Рабочий путь состояния и причины ошибки:
  `apps/windows/RecApp/Capture/WindowsCaptureSessionController.cpp`
  (`record/pause/resume/pollHealth/stop`) →
  `apps/windows/RecApp/Shell/RecordingIndicator.h` (`snapshot`) и `.cpp`
  (`publish`) →
  `apps/windows/RecApp/AppMain.cpp` (`NativeCapture::indicator`, native UI/tray).
  Наличие этого пути не подтверждает полноту counters/bridge или аппаратную
  и визуальную приёмку; проверки T081/T084 остаются открытыми.

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

Исторический T056 не задаёт текущие условия старта: Constitution 7 отменяет
проверку согласия. В T082 тесты заменены проверкой технических условий,
сохранённого выбора и отсутствия запуска для неизвестных приложений.

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
- Phase 9 shell convergence and Phase 10 native runtime convergence must complete
  before the Phase 11 closeout tasks T063/T064.

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
| FR-002 | T012, T032, T057, T061, T062, T076 |
| FR-003 | T029, T032, T034, T066, T076 |
| FR-004 | T010, T023, T024, T033, T065, T076 |
| FR-005 | T027, T029, T058, T066, T076 |
| FR-006 | T028, T031, T058, T066, T076 |
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
| SC-002 | T012, T034, T061, T064, T076 |
| SC-003 | T017, T021, T022, T048, T063 |
| SC-004 | T016, T024, T043, T046, T047, T063, T068, T071 |
| SC-005 | T035, T036, T038, T039, T040, T041, T042, T063, T069, T071 |
| SC-006 | T028, T031, T044, T058, T076 |
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
- [X] T067 [US1] Собрать native capture pipeline в `apps/windows/RecApp/Capture/WindowsCaptureSessionController.*`: endpoint enumeration, pinned GrafAEC3 adapter, `RecordingAudioTimeline`, v5 writer/finalizer и WebView-independent local custody; сохранить fail-closed и idempotent Stop (FR-009–FR-012, US1/AC1–AC4; implementation and Windows x64 build complete; hardware capture matrix remains T071).
- [X] T068 [US1] Подключить `apps/windows/RecApp/Shell/RecordingIndicator.*` к persistent native WinUI status strip с accessible status и one-action Stop, переживающим WebView close/minimize/network failure (FR-015, SC-004; implementation complete, Windows UI matrix remains T071).
- [X] T069 [US3] Подключить реальный стандартный HTTP transport существующих GRAF desktop API к `apps/windows/RecApp/Upload/DesktopApiClient.*`, `apps/windows/RecApp/Upload/DesktopHttpTransport.*` и `DesktopUploadRecoveryScheduler.*`, включая auth/network/wake recovery, accepted ranges и server-truth reconciliation без MediaScribe/MinIO egress (FR-013–FR-014, SC-005; implementation complete: WinHTTP, sync-state, missing ranges, offset/length checks, expired-session recovery and bounded queue retry; Windows host validation remains T071, HIGH).
- [X] T070 [US2] Завершить `apps/windows/Installer/Package.appxmanifest`, `GrafWindows.Package.wapproj` и package assets/dependency declarations для собираемого signed x64 MSIX без elevation/driver/service; затем подтвердить clean-image install/update/rollback smoke (FR-019–FR-020, SC-008; partial, HIGH). Состояние на 2026-09-17: пакет собирается, подписывается отладочным сертификатом, проходит статический smoke-тест, устанавливается, запускается и доходит до рабочей инициализации (WebView2, корень хранения, очередь отправки); обновление 0.1.0.0 → 0.1.0.1 и откат 0.1.0.1 → 0.1.0.0 через `-ForceUpdateFromAnyVersion` проверены, приложение запускается после обеих операций; ложная зависимость `Microsoft.NET.CoreRuntime.1.1` устранена (T092 закрыта). Осталось: установка на образ, где нет распространяемого пакета Visual C++ (T093). Неиспользуемая `Microsoft.WindowsAppRuntime.Bootstrap.dll` в полезной нагрузке оставлена как известный остаток: её копирование не управляется свойством `AppxPackage`, на работу она не влияет. Подробности в `validation-2026-09-17.md`. Дополнено 2026-09-18: закрыта оставшаяся часть T070 вместе с T093 — пакет больше не требует ничего доустанавливать на чистом образе Windows. Распространяемый пакет Visual C++ (`vcruntime140`, `msvcp140` и спутники) кладётся рядом с исполняемым файлом элементами `Content` из установленного набора инструментов: упакованное приложение загружает app-local копию раньше системной, лицензия это разрешает, а в репозиторий двоичные файлы не попадают. Зависимость `Microsoft.WindowsAppRuntime.2` объявлена в манифесте, и сам framework-пакет лежит рядом с MSIX в `Dependencies\x64\`, поэтому чистый образ не ходит в сеть: скрипт проверки ставит его из этой папки, когда его нет в системе. Проверено на текущем образе: установка, обновление 0.1.0.0 → 0.1.0.1 и откат 0.1.0.1 → 0.1.0.0 проходят, приложение запускается после каждой операции (`title="GRAF"`), а в полезной нагрузке установленного пакета присутствуют все импортируемые библиотеки, кроме системных (`machine_vcredist_required=false`). Осталось: буквальный прогон на образе без среды разработки — доступна одна виртуальная машина, и ограничение записано в `quickstart.md`. Дополнено 2026-09-18: упаковочный проект решает инкрементально и мог оставить MSIX, собранный до последней сборки приложения — то есть в пакет попадал старый двоичный файл, а полоса сообщала успех. Теперь полоса упаковки сначала удаляет прежние артефакты, затем проверяет, что MSIX новее приложения, и подписывает его отладочным сертификатом внутри той же полосы. Свежий пакет `0.1.0.0` собран, подписан (`CN=GRAF`), установлен и запущен из пакета; в полезной нагрузке установленного пакета присутствуют новые маршруты кабинета.
- [ ] T071 [P] Провести Windows x64 validation из `specs/200-windows-desktop-app/quickstart.md` для T065–T070, зафиксировать exact SHA, hardware/AEC3/WebView2/Media Foundation/MSIX evidence и оставить ARM64 lane явно skipped до отдельного proof (SC-001/003/004/005/008/010; missing, HIGH). Состояние на 2026-09-17: прогнаны скрипты репозитория — граница WebView2 `-Contract` 5/5, аудиоконтракт `-Synthetic` 4/4 и `-CustodyFaults` 4/4+3/3, переносимая полоса 22/22, идентичность AEC3 `846fe90a289f58b7c9303a635142aa2c7caa93e5`, пакет собран, подписан, установлен и запускается; среда — сборка 26200, WebView2 Runtime `153.0.4234.32`, Media Foundation 10.0.26100.8521/8972; контейнер `meeting-review.m4a` разобран как MPEG-4 (`ftyp`/`mp42`). Зафиксированы хеш базы `4b25d6cd2`, отпечатки рабочего дерева и артефактов. Дополнено 2026-09-18: проверки выполнены заново на текущем срезе (точка отсчёта `4b25d6cd2745b89da7a44910d848b2cefc313230`, изменения в рабочем дереве). Граница WebView2 `-Contract` — 7/7 (`WebView2 boundary validation passed`), аудиоконтракт `-Synthetic` — 4/4, отказы хранилища `-CustodyFaults` — 4/4 и 3/3, идентичность AEC3 — `846fe90a289f58b7c9303a635142aa2c7caa93e5`, портируемая полоса 26/26, полоса приложения и полоса пакета пройдены, пакет установлен и запускается. Среда: сборка `26200.9168`, `ARM64` с эмуляцией x64, WebView2 Runtime `153.0.4234.32`, Media Foundation `10.0.26100.8521`/`8972`. Осталось: ARM64 явно пропущена (собственной сборки нет), реальная аппаратная матрица и SC-003 (60 минут) не выполнялись — нужен физический x64-компьютер с двумя источниками звука, кабинет под входом не проверялся — нужен аккаунт. Подробности в `validation-2026-09-17.md`. Дополнено 2026-09-18 (раунд 27): отказ любого источника ограничивает запись вместо обрыва (паритет с macOS `markDegraded(source:)`), причина называет отказавший источник. Живая проверка ограниченной записи по-прежнему требует физического компьютера: в ВМ оба источника нерабочие.

Дополнено 2026-09-18 (раунд 26): установка, обновление и откат пройдены обычным
путём, без принудительного ключа. Приложение удалено полностью, установлено на
пустое место, обновлено до `0.1.1.0` (рост версии, то же семейство пакетов),
затем возвращено откатом на `0.1.0.0`; после каждой операции приложение
запускается. Отдельно зафиксированы отказ `0x80073D02` при работающем приложении
и отказ `0x80073D06` при понижении версии, а также сохранность данных приложения
и пользовательской настройки при обновлении. Остаток: образа без среды
разработки нет, предустановленный `Microsoft.WindowsAppRuntime.2` из-под
пользователя не удаляется; framework лежит рядом с MSIX и объявлен зависимостью.

## Phase 10: Convergence — оставшиеся native runtime gaps

Convergence review 2026-08-25 подтвердил, что portable contract surface и
fail-closed guards собраны, но четыре runtime composition gap-а нельзя закрыть
на macOS: реальный pinned AEC3 backend, нормализация произвольного WASAPI mix
format, microphone privacy preflight и подключение queue recovery к AppMain.

Validation re-check 2026-08-30 подтвердил current dirty-worktree host evidence:
native Release MSBuild и fresh Windows CMake/Ninja build проходят, CTest — 20/20,
synthetic/custody/WebView smoke — 2/2, 3/3 и 4/4, pinned AEC3 — 440/440,
а `GrafWindowsApp.exe` скомпилирован с native adapter и запускается с auth
cabinet. `.wapproj` формирует unsigned x64 MSIX, а static package smoke
проверяет manifest, entry point, capabilities и embedded certificate. Это не
закрывает T070/T071/T063: trusted release signature, cabinet auth, hardware
WASAPI capture и clean-image evidence отсутствуют.

- [X] T072 [US1] Подключить `apps/windows/scripts/build-graf-aec3.ps1` к реально собираемой pinned WebRTC AEC3 static library, добавить native adapter и wire-up в `apps/windows/RecApp/AppMain.cpp`, чтобы `aecReady` становился true только после create/process smoke (FR-010, US1/AC2; implementation complete; VM build 440/440 and x64 app link passed).
- [X] T073 [US1] Добавить bounded worker-side normalizer actual WASAPI mix format → 48 kHz mono float через Media Foundation или другой approved native path, обновить readiness и synthetic coverage без работы в capture callback (FR-009, FR-018, US1/AC1; implementation and synthetic coverage complete; hardware matrix remains T071).
- [X] T074 [US1] Заменить hardcoded `microphonePermissionGranted = false` в `apps/windows/RecApp/AppMain.cpp` на Windows microphone privacy/endpoint preflight с metadata-safe recovery action и повторной проверкой перед Record (FR-008, FR-017, US1/AC3; implementation complete; privacy-denial hardware scenario remains T071).
- [X] T075 [US3] Подключить `DesktopUploadQueueService`, `DesktopHttpTransport` и `DesktopUploadRecoveryScheduler` к native local finalization/launch/wake lifecycle в `apps/windows/RecApp/AppMain.cpp`, чтобы saved v5 package сразу получал queue item и восстанавливался без WebView route (FR-013–FR-014, US3/AC1–AC3; implementation and contract smoke complete; authenticated end-to-end upload remains T071).
- [X] T076 [US2] Перенести в Windows parity-срез последнюю macOS cabinet-доработку: общий embedded profile menu, marker `data-graf-app-quit`, exact-origin/nonce-bound `request_app_quit`, native close lifecycle и server/contract tests (FR-002–FR-006, SC-002/006; completed in current dirty worktree).

## Phase 10b: Native parity convergence (2026-08-30)

- [X] T077 [US2] Убрать ошибочную зависимость кабинета от MSIX identity: WebView2 получает user-scoped профиль в `apps/windows/RecApp/Web/WebView2Host.*`, сохраняет native download dialog и обновляет in-memory auth callback после успешного document boundary; runtime/package evidence остаётся в T071.
- [X] T078 [US1] Добавить Windows-native parity surfaces в `apps/windows/RecApp/AppMain.cpp` и `apps/windows/RecApp/Shell/WindowsTray.*`: верхний persistent indicator, tray Stop/open/quit, WinUI settings, permission onboarding и dynamic custody status.
- [X] T079 [US2] Исправить exact route classification в `apps/windows/RecApp/Web/WebViewRoutePolicy.cpp` и добавить regressions для meeting share/deletion-report и slash в query; portable contract evidence зафиксирована в quickstart.

## Phase 11: Closeout — evidence and final review

### Повторное сведение с master от 2026-09-06

Исторические `[X]` выше подтверждают только указанные там прежние этапы.
Новые расхождения покрыты следующими открытыми задачами до финального closeout.

Текущий срез T081/T082: скрытая подготовка существующего CompactOverlay и
проверка его показа перед фоновым стартом; перенос слежения за принятой
авто-записью в `MeetingDetection/AutomaticRecordingPolicy.*` с порогами
свежести/отсутствия/потери доказательств 2/15/600 секунд. Сначала расширить
`Tests/GrafWindowsPackageTests/AutomaticRecordingSmokeTests.cpp`, затем удалить
заменённые поля и ветви `AppMain.cpp`. US5/AC4–6; каталог/миграция предпочтений
и настоящая аппаратная встреча остаются незакрытыми частями T082/T084.

Продолжение T082, US5/AC7–9: сначала дополнить
`Tests/GrafWindowsCoreTests/VerifiedTargetPolicyTests.cpp`, затем разделить
постоянный targetKey и точный identityKey в `MeetingDetection/VerifiedTargetRegistry.*`,
`AutomaticRecordingPolicy.*`, `WindowsTargetDetector.cpp` и вызовах AppMain.
В существующий реестр добавить только подтверждённую Teams-запись; проверить
формат V2, единственную строку на продукт, сохранение всех режимов при обновлении,
отказ подменённому ключу/хешу и строгую идентичность слежения. Полный каталог,
реальные встречи и остальные версии/архитектуры всё ещё входят в T082/T084.

- [X] T080 [US2] Восстановить реальный WebView2 lifecycle, безопасный код ошибки, повторный запуск и навигацию в `apps/windows/RecApp/Web/WebView2Host.*` и `apps/windows/RecApp/Shell/CabinetWindow.*`; добавить regressions и проверить installed Runtime + offline/retry (FR-003–006/020, SC-001/006). Состояние на 2026-09-17: жизненный цикл, безопасный код отказа, повтор и навигация реализованы; добавлены регрессии `Tests/GrafWindowsContractTests/WebView2HostLifecycleTests.cpp` (переносимая полоса 22/22), закрепляющие состояние `closed`, цель повтора, отказ запрещённым и внешним адресам, устойчивость к исключению в обработчике и запрет действий вне состояния `ready`. В ВМ проверены установленный Runtime `153.0.4234.32` и поведение при недоступном источнике: приложение живо, профиль WebView2 создан и переиспользован, отчётов WER нет. Осталось: нажатие «Повторить загрузку» в живом интерфейсе — дерево автоматизации WinUI 3 на стенде отдаёт только окно и кнопки заголовка, поэтому нужна ручная приёмка. Подробности в `validation-2026-09-17.md`. Дополнено 2026-09-18 (оформление): живая проверка окна в двух системных темах нашла два дефекта — кнопки и текст оболочки брали цвета из системной темы, а тема кабинета не доходила до окна на старте. Исправлено: единый набор кистей в двух темах по значениям кабинета, рецепт кнопок и текста оболочки, чтение `data-theme` у страницы после рукопожатия, явный `prefers-color-scheme` кабинета. Проверено снимками (светлая и тёмная системные темы), портируемая полоса 27/27, сборка и установка пакета. Дополнено 2026-09-18: проверены две дополнительные возможности увидеть содержимое страницы, обе закрыты по объективной причине. Принудительная доступность (`WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=--force-renderer-accessibility`) дерево не меняет: содержимое WebView2 в него не попадает. Отладочный порт WebView2 для пакетного приложения не работает (WebView2 не читает переменные среды упакованных приложений), а запуск «россыпью» завершается сразу. Зато снимок настоящего окна подтверждает, что пакетное приложение рисует нативную оболочку вместе с кабинетом («Мои встречи», «Поиск встреч», тёмное оформление). Нажатие «Повторить загрузку» остаётся за ручной приёмкой: кнопка живёт в содержимом кабинета. Инвентарь нативной части снят точно: три безымянных панели и четыре кнопки — «Назад в кабинете» (выключена), «Вперёд в кабинете» (выключена), «Открыть кабинет» (включена), «Встречи» (включена). Все четыре вызваны через UIA: ошибок нет, приложение живо, состояния не меняются, потому что история на старте пуста. Сценарий без сети (перенаправление `rec.2brain.pro` на `127.0.0.1` в каталоге хостов) дерево не меняет: экран отказа и его повтор находятся внутри веб-содержимого. Дополнено 2026-09-18 (живой клик): прежний вывод «кнопка живёт в содержимом кабинета» неверен — экран восстановления нативный, он виден на снимке всего окна, и кнопка «Повторить загрузку» нажата по координатам. Порядок: hosts → `127.0.0.1`, перезапуск, снимок экрана отказа (окно 1080×620 логических точек); затем hosts восстановлен, нажатие в центре кнопки (274, 580), ожидание 22 с — кабинет открылся в том же окне («Мои встречи», календарь, список записей, панель «Запись»). Снимки: `graf-offline-true.png` sha256 `64bcbf4763ea0221cfd6cd80c37164c1bba0ee05aa2af0c9d33f9ea78046c7e0`, `graf-after-retry.png` sha256 `0ffffa8de3437c1527face18b3fc97f169d165020edb7143037f1ebe6d2f19ec`; файл hosts очищен и проверен. Вместе с этим исправлены два дефекта оформления, найденных на снимках: размер окна задавался в физических пикселях (на экране с масштабом панель управления обрезалась) — теперь размер в логических точках ставится при первой активации и центрируется; акцентная кнопка и шкалы брали системный акцент Windows — добавлена кисть `AccentFillColorDefaultBrush` и рецепт акцентной кнопки. Осталось открытым: ручная приёмка на физическом x64-компьютере и работа под входом в аккаунт (T081/T082). Закрыто 2026-09-18: живая проверка без сети и с повтором загрузки выполнена в ВМ — приложение показало собственную поверхность с безопасным кодом отказа и рабочей панелью записи, а после возврата сети «Повторить загрузку» вернуло кабинет без перезапуска (`graf-r32-webview-offline.png`, `graf-r32-webview-retry.png`). Живой сценарий падения процесса WebView2 остаётся непроверенным.
- [X] T081 [P] [US1] Довести нативные окна и действия до текущей macOS версии: читаемые настройки, двустороннее сворачивание, навигация, микрофон, состояния с таймером и пауза/продолжение/остановка, recovery и очередь без статических заглушек — сверено по доказательствам раундов 25, 26, 31–36. Действия кабинета проверены живьём: переключение оформления (раунды 31, 34), меню учётной записи, а в раунде 38 — действие панели, открывающее нативное окно настроек. Сверка и доказательства: `specs/200-windows-desktop-app/validation-2026-09-17.md`, раздел раунда 38.
- [ ] T082 [P] [US5] Перенести локальную трёхрежимную автозапись Constitution 7 в `apps/windows/RecApp/MeetingDetection/`, `apps/windows/RecApp/Shell/AutomaticRecordingPrompt.*` и соответствующие `apps/windows/Tests/`; подключить подтверждённый Windows detector и prompt к shell после T081, сохранить countdown/remember/negative cases (FR-016, SC-007). В совместном с T081 срезе удалить отменённые `recordingPolicyAllowed`/`consentSatisfied`, мёртвые reason/copy в `Permissions/WindowsReadinessGate.*` и `Contracts/WindowsDesktopContracts.h`; до изменения кода скорректировать тесты технических отказов и проверить все позиционные инициализации. Правки AppMain выполнять последовательно с T081. Состояние на 2026-09-17: отменённые поля и мёртвые причины удалены, `targetKey` и `identityKey` разделены, автозапись подключена к оболочке (выбор режима, условия, отсчёт, `AutomaticRecordingPrompt::view`); в упакованном приложении проверен отрицательный случай — за 90 секунд без активного подтверждённого источника запись не началась, приложение устойчиво. Осталось: положительный случай настоящей встречи, полный каталог приложений и миграция предпочтений. Дополнено 2026-09-18: живая проверка каталога и настроек упирается в отсутствие входа в аккаунт на стенде; содержимое страницы не читается ни деревом доступности, ни отладочным портом. Снимок окна показывает, что кабинет рисуется и тёмное оформление применяется. Дополнено 2026-09-18 (раунд 26): окно «Настройки GRAF» проверено живьём — у «Для всех приложений» и у «Microsoft Teams» стоит «Спрашивать», рядом пояснение про 8 секунд и «Запомнить выбор». Само поведение (обнаружение встречи → вопрос → отсчёт → запоминание) требует живого обнаружения встречи и остаётся открытым. Дополнено 2026-09-18 (раунд 37): настройки трёх режимов проверены живьём — список «Всегда»/«Спрашивать»/«Никогда», отдельная настройка для Teams, выбор сохраняется между открытиями окна. Живое срабатывание упирается в намеренное свойство: определитель доверяет только подписанному процессу (отпечатки файла и издателя), поэтому нужен настоящий Teams или Zoom в машине. Доказательства: `specs/200-windows-desktop-app/validation-2026-09-17.md`, раздел раунда 37.
- [ ] T083 [P] [US3] Проверить и исправить несовместимость Windows upload/auth/bridge с актуальным master в `apps/windows/RecApp/Upload/`, `apps/windows/RecApp/Web/` и `apps/windows/Tests/GrafWindowsContractTests/`, не меняя server business logic; записать matrix в `specs/200-windows-desktop-app/parity-matrix.md` (FR-003/005/006/011/013/014/022, SC-005/006). Состояние на 2026-09-17: сверка с master выполнена и записана в `parity-matrix.md`, раздел «Проверка 2026-09-17». Корневая причина — master-коммит `977310d1a` (F262): схема очереди, мост удаления и серверные API жизненного цикла. Найдено двенадцать расхождений; порядок исправлений и минимальные правки записаны. Исправления внесены частично. Закрыт R3: `decodeSyncState` распознаёт уже принятую ревизию по `meeting.status` (`ingested_pending_processing`, `degraded`) с нормализацией регистра и пробелов, поэтому потерянный ответ `finalize` больше не порождает вторую сессию для неизменяемой ревизии. Закрыт R4: транспорт читает серверный класс повтора `custody.retry_class` и очередь действует по нему — `paused_until_user_action` переводит строку в `needsAuth`, `paused_until_admin_action` и `not_retryable` в новое состояние `blocked` без автоматических попыток с явной отправкой владельцем, `terminal` в карантин. Диапазон чтения реестра расширен без сдвига прежних значений, интерфейс показывает причину остановки. Регрессии в `DesktopUploadRecoveryTests.cpp`; портируемая полоса 22/22, полоса приложения собрана. Закрыт R5 в части идентификатора встречи: он сохраняется в реестре очереди, принимается один раз и передаётся кабинету, поэтому серверная строка замещает локальную, а не показывается рядом с ней. Закрыт R6: писатель пакета сохраняет время начала и окончания записи и смещение часового пояса в манифесте, читатель проверяет их и отбрасывает невозможную пару, транспорт отправляет `title`, `title_source`, `started_at`, `ended_at` и `recording_display_timezone_offset_minutes` в теле `POST /api/v1/meetings` — в тех же условиях, что и macOS. Заголовок строится из местного времени начала записи, источник `generic`. Поля манифеста добавлены как необязательные, поэтому пакеты прежних сборок остаются читаемыми и просто не сообщают время. `calendar_match_attempt_id` не отправляется: интеграция с календарём исключена из объёма Feature 200 (`spec.md:296`). Регрессии в `ContractFixtures.cpp` (`createMeetingBody` — точные байты тела) и `V5LocalRecordingWriterTests.cpp`; портируемая полоса 22/22, полоса приложения собрана. Дополнено 2026-09-18: закрыта часть строки R5, выводимая из локального пакета. Строка получает время начала в ISO-8601, префикс заголовка «Запись », длительность всей сессии и признак частичной записи, поэтому кабинет сам форматирует дату в часовом поясе читателя, а прежние пакеты без времени по-прежнему показывают «На этом компьютере». Соответствие полей проверено против `EmbeddedCabinetLocalRecordingRow` и `cabinet.js`: у macOS 16 полей, у Windows стало 13. Остаются R1, R2, R8, R9, R10, R11 и R12, а также `localDeletionPending`, `deletionIsLocalOnly` и `progressPercent` в строке R5 — порядок и минимальные правки записаны в `parity-matrix.md`. Дополнено 2026-09-18: R7 закрыт, кроме строки про `/desktop/settings/meeting-detection` — она решается вместе с R2. Кабинет снова открывает страницы уведомлений и удалений (раньше это были мёртвые ссылки: колокольчик уведомлений и переход к удалениям), а ссылка поддержки `mailto:` передаётся почтовой программе. Адрес при этом проверяется: один адрес, без темы, копий и вложений. `/api/v1/notifications/{id}/read` остаётся вне списка маршрутов осознанно: кабинет обращается к нему через `fetch`, а не переходом документа. До появления настоящей серверной операции мост удаления R1 включать нельзя: это было бы фиктивным подтверждением. Дополнено 2026-09-18: закрыта часть R10 — ответ 429 с заголовком `Retry-After` больше не превращается в немедленный повтор. Транспорт читает заголовок, планировщик держит паузу и не начинает попытку раньше срока, а строка остаётся в состоянии `retry` с причиной `rate_limited` без расхода лимита автоповторов: ожидание, которого потребовал сервер, не должно приближать запись к исчерпанию бюджета. Нечитаемое значение даёт 60 секунд, как в macOS, пауза длиннее суток не удерживается, а 408, 5xx и сетевой сбой идут прежним путём. Осталось чтение `X-GRAF-Auth-Expires-At`: ему нужно место в реестре очереди, которое появится вместе с R9. Регрессия `testRateLimitPause` в `DesktopUploadRecoveryTests.cpp`. Дополнено 2026-09-18: закрыт R12 — подтверждение аккаунта больше не повторяется на каждую попытку отправки. Оболочка подтверждает текущего пользователя и рабочее пространство через `GET /api/v1/auth/me` для текущей сессии и передаёт этот снимок в полёт, а транспорт использует его вместо нового запроса; смена токена сессии стирает снимок до начала любой отправки. Снимок не является полномочием сам по себе: он должен описывать настоящий аккаунт и совпадать с рабочим пространством, с которым едет, иначе отправка блокируется, а проверка совпадения владельца перед отправкой осталась на месте. Регрессия `testConfirmedIdentitySnapshot` считает запросы и проверяет порядок «сначала пространство, потом `/auth/me`» для первой проверки. Осталось чтение `X-GRAF-Auth-Expires-At` вместе с R9. Дополнено 2026-09-18: закрыт R10 — приложение читает срок сессии, который сервер называет в `X-GRAF-Auth-Expires-At`, и переписывает им срок cookie кабинета, как это делает macOS. Заголовок принимается тем же правилом (только цифры), срок доходит от рабочего полёта до потока владельца и ставится на ту же cookie `__Host-twobrain_rec_owner_session`, из которой приложение берёт токен. Переписывание происходит только при трёх условиях: токен есть, значение cookie всё ещё равно этому токену, срок в будущем — иначе старый ответ откатил бы уже продлённую сессию назад. Место в реестре очереди, о котором говорила матрица, не понадобилось: macOS тоже нигде не хранит этот срок, его хранит cookie. Ошибка переписывания не показывается пользователю. Регрессии: `WebView2HostLifecycleTests.cpp` (правило переписывания cookie) и `testSessionDeadlineHeader` в `DesktopUploadRecoveryTests.cpp` (разбор значения: только цифры, отказ на знаках, дроби, экспоненте и слишком длинном значении). Портируемая полоса 26/26, полоса приложения и полоса пакета пройдены, установленный пакет содержит строку `X-GRAF-Auth-Expires-At`. Последняя сборка: `sha256=D858D51F71A620A384DD1D05BA0BED7923AF2E9F00F79E5E72D341F138307746`, установка и запуск `hr=0x00000000`. Дополнено 2026-09-18: закрыта часть R8 — ворота протокола удаления, область запроса и чтение жизненного цикла. Перед любой мутацией транспорт читает `GET /api/v1/desktop/notification-context` и требует `recording_deletion_protocol_version == 1`: иначе клиент не отличит старый сервер, который молча игнорирует заголовки ожидаемого аккаунта, а нечитаемая квитанция пришла бы уже после удаления. Область передаётся заголовками `X-Graf-Expected-Actor` и `X-Graf-Expected-Workspace`, и запрос не уходит вовсе, если область не описывает настоящий аккаунт или сессии нет. `deletion-requests` для локальной записи и встречи и `recordings/lifecycle` собраны из точного контракта сервера: одна проверенная часть пути, литерал подтверждения `Delete this meeting everywhere GRAF controls.`, `extra="forbid"`, от 1 до 100 целей. Разбор ответов строгий: непонятное состояние, неизвестная цель или неподтверждённая квитанция отвергаются целиком, а не частично. Регрессия `DesktopDeletionProtocolTests.cpp`; портируемая полоса 23/23. Осталось в R8: `local-purge-tasks` (создание, список, подтверждение), затем мост R1 — версия моста не выставляется раньше настоящей серверной операции. Дополнено 2026-09-18: закрыта вторая часть R8 — контракт задач очистки локальных копий. Клиент адресует задачу по встрече (`/api/v1/desktop/meetings/{id}/local-purge-task`, без тела), читает список (`/api/v1/desktop/local-purge-tasks`) и подтверждает по идентификатору задачи; понимаются только типы и состояния, которые сервер действительно присылает, а одна непригодная задача отвергает весь список. Подтверждение несёт код доказательства из словаря клиента и говорит, что удалось доказать, а не что запрос отправлен. `ack_url` из ответа не используется как адрес: путь строится из проверенного идентификатора задачи (сознательно строже macOS). Найденная регрессией ошибка — кабинетный префикс вместо `/api/v1/desktop/meetings/` — исправлена до сборки приложения. Остался поток: сопоставление задач со строками очереди, очистка и подтверждение, затем мост R1. Версия моста не выставляется раньше настоящей серверной операции. Дополнено 2026-09-18: закрыта часть R9 — схема реестра очереди. Каждая строка получила отметку времени `updated_at_ms`, у документа появилась своя отметка, а запросы удаления живут в `deletion_operations`: серверное удаление не имеет локального пакета, за который можно было бы зацепиться, поэтому переживает перезапуск только в реестре. Запрос хранится один раз на цель и аккаунт, его имя выводится из цели и аккаунта, поэтому повтор после перезапуска — та же операция для сервера и ничего не удаляет дважды. Принятие удаления записывается только с квитанцией, назвавшей именно эту цель, а состояние монотонно: принятое удаление может стать только подтверждённым, и поздний сбой не возвращает запись в список. Реестры `v2` по-прежнему читаются и обновляются при первой же записи. Проверено в ВМ на настоящем реестре: приложение подняло существующий файл из одиннадцати строк и перезаписало его как `v3`, не потеряв ни строки. Регрессия `DesktopDeletionLedgerTests.cpp`; портируемая полоса 24/24. Дополнено 2026-09-18: закрыт R9 — отпечаток сервера пишется в строку реестра и читается после перезапуска. Строка хранит идентификатор принятой медиаревизии, идентификатор сессии загрузки, состояние встречи, состояние обработки и состояние ревизии; каждое значение проверяется перед записью, поэтому один негодный ответ не портит файл, а прежнее значение строки остаётся. Снимок заменяется новым целиком: он описывает то, что сервер держит сейчас. Поля объявлены последними, поэтому старые реестры читаются как прежде, а позиционные инициализаторы в тестах сохранили смысл. Проверено на настоящем реестре в ВМ: реестр версии 2 мигрирован установленным приложением в версию 3 со всеми новыми полями, исходные одиннадцать строк восстановлены после проверки. Конфликт и срок хранения остаются вне строки осознанно: конфликт приходит серверным классом повтора и превращается в `blocked` или `needsAuth` с причиной, а локальные копии удаляются только по задаче сервера. Регрессия в `DesktopUploadQueueV2Tests.cpp`; портируемая полоса 26/26. Дополнено 2026-09-18: закрыт R1 в части моста — кабинет может попросить приложение удалить выбранные записи, и это тот же запрос, который принимает macOS: версия 1, действие `deleteSelection`, идентификатор запроса в форме UUID, от одной до ста целей, без повторов, встречи только как UUID, локальные строки только те, которые приложение само предлагает удалять. Цель локальной записи берётся из каталога, который знает сервер, а не из идентификатора строки, которую показал кабинет. Ворота страницы повторяют macOS: список встреч принимает любой выбор, страница встречи — только эту встречу или одни локальные копии, общая встреча считается одной встречей, прочие страницы поверхностью удаления не являются. Ответ уходит только на ту страницу, которая спросила. Мост при этом ещё не выставлен странице: сценарий объявляет версию 1 только тогда, когда у приложения есть обработчик выбора, а его пока нет — иначе страница встречи отказалась бы от работающей веб-формы ради несуществующего исполнителя. Найденная проверкой ошибка: ворота требовали вид маршрута «одна встреча», из-за чего список встреч отверг бы любой выбор. Остался исполнитель: сохранить запросы в реестре R9, отправить транспортом с областью запроса и воротами R8, посчитать принятые, ожидающие и отклонённые, ответить странице и включить обработчик. Дополнено 2026-09-18: R1 закрыт целиком — исполнитель готов и включён, поэтому версия моста появилась в выпуске. Проход устроен в три фазы, потому что реестр очереди пишется только из потока владельца окна: выбор сохраняется на этом потоке, отправляется рабочим потоком без доступа к реестру, а ответы записываются снова на потоке владельца. Перед первой отправкой читается контекст уведомлений, и без объявленной поддержки `recording_deletion_protocol_version == 1` ни один запрос не уходит: старый сервер игнорирует заголовки области, а нечитаемая квитанция пришла бы уже после удаления. `saved` означает, что запросы durable, и никогда — что что-то удалено; принятым считается только запрос, названный квитанцией, а ответ читается обратно из фаз реестра. Счётчик попыток растёт при записи ответа, а не при планировании, поэтому сбой сети не сжигает расписание повторов у неотправленных запросов. Проход продолжается только на двух ответах про саму цель (`403 deletion_forbidden`, `404 meeting_not_found`), а сеть, истёкшая сессия, ограничение частоты и обновление сервера останавливают его: это одно и то же для всех запросов аккаунта. Копия, о которой сервер не знает, удаляется локально без запроса, а ответ `meeting_deletion`, назвавший локальную копию, подтверждает просьбу о ней и учит строку встрече — как `RecordingDeletionReceipt.matches` в macOS. Найдены и исправлены два дефекта: `decodeDeletionReceipt` не читал `meeting_id` у отмены копии, из-за чего встреча из ответа терялась, и правило общего сбоя останавливало проход на `403`, то есть отказ одной цели отменял остальные. Регрессии: девять наборов в `DesktopDeletionLedgerTests.cpp` (ворота, сохранение и отправка, обе цели, нечитаемый ответ, отказ и общий сбой, отказ до сети, `Retry-After`, локальная копия без сервера, проверка аккаунта и адреса) и чтение `meeting_id` с отрицательным `deletion_epoch` в `DesktopDeletionProtocolTests.cpp`; портируемая полоса 25/25, полоса приложения собрана. Дополнено 2026-09-18: закрыт R2 — страницы настроек отвечают кабинету. Страницы кабинета разговаривают с приложением так, как это устроено в macOS (`window.webkit.messageHandlers.<handler>.postMessage` возвращает обещание, ответ приходит телом `{version: 1, ...}`), и в WebView2 такого моста не было: обе страницы ждали ответ пятнадцать секунд и печатали «Не удалось загрузить настройки этого Mac». Теперь сценарий-переходник выставляет `window.webkit.messageHandlers`, при загрузке страницы настроек приложение отдаёт ей рукопожатие `connect(nonce)`, а запрос принимается только на своём маршруте и только со своим обработчиком. Правила автозаписи читаются и пишутся через то же хранилище, что у нативного окна настроек (`AutomaticRecordingPolicy`), поэтому две поверхности не расходятся; словарь правил общий с реестром (`always`, `ask`, `never`). Страница уведомлений получает правду о платформе (`canEdit: false`, нулевые настройки и причину): местных напоминаний о встречах в Windows нет, и обещать их было бы ложью. Строка `/desktop/settings/meeting-detection` остаётся расхождением осознанно: сервер такой страницы не отдаёт, а у Windows есть работающая нативная страница определения встреч. Регрессия в `NativeSettingsBridgeTests.cpp`. Дополнено 2026-09-18: закрыт R11 — тема кабинета решает оформление нативных окон. Сервер отдаёт выбранную тему в `<html data-theme>`, страница настроек меняет её на месте, и приложение теперь узнаёт её тем же объявлением, что macOS (`grafAppAppearance`): принимаются ровно `light`, `dark` и `system`, а `ElementTheme::Dark` в четырёх местах заменён на тему в силе. За страницей следует системная часть оформления — меню, диалоги, элементы управления, — а собственные цвета оболочки остаются утверждёнными тёмными токенами: у macOS оболочка тоже фиксированная, от темы зависит только системная часть, и выдумывать светлые токены значило бы менять макет без утверждённого образца. До объявления страницы оформление системное, как и в macOS; окна, созданные позже, берут тему в силе. Регрессия в `WebView2HostLifecycleTests.cpp` — принимаются три значения, отвергаются пустое, другой регистр, `high-contrast` и мусор. Дополнено 2026-09-18: закрыта оставшаяся часть R5 — кабинет получает удаления в работе и признак скрытых записей тем же вызовом, что и macOS (`update(rows, operations, recoveryRequired)`), а строка — `localDeletionPending` и `deletionIsLocalOnly`. До этого страница получала только строки, поэтому панель «Удаления» с состоянием сохранённого запроса и уведомление о скрытых записях не появлялись никогда. Фазы передаются именами реестра, причины ожидания переводятся в словарь страницы, цель — в форму перечисления, которую читает страница; ссылка на отчёт появляется только когда встречу назвала квитанция. `deletionIsLocalOnly` выводится из того же правила, по которому действует исполнитель удаления, поэтому диалог обещает ровно то, что приложение сделает. `localDeletionPending` показывает строку как незавершённую очистку, и удаление, прерванное между записью намерения и «Корзиной», доводится до конца в обычном проходе восстановления — иначе обещание «повторим автоматически» было бы неправдой. `recoveryRequired` на Windows всегда `false`: строки не скрываются, а показываются с причиной. Осталось `progressPercent`, который кабинет не читает. Регрессии — два набора в `DesktopDeletionLedgerTests.cpp` и словарь причин в `DesktopDeletionProtocolTests.cpp`; портируемая полоса 25/25. Дополнено 2026-09-18: закрыта третья часть R8 — выполнение задач очистки локальных копий. Задача сопоставляется со строками очереди только по идентификатору встречи, который вернул сервер, и удаляются лишь те копии, которые сервер уже считает своими (`uploaded`): незавершённая отправка не уничтожается, а ждёт. Файлы уходят тем же безопасным путём, что и подтверждённое пользователем удаление (проверка каталога внутри хранилища, отсутствие второго владельца пути, запись намерения в реестр до операции ОС, перенос в Корзину), но с другим доказательством — `serverRequestedPurge`, которое не может прийти из меню. Тип задачи, который клиент не может проверить (`purge_local_exports`, `confirm_local_expiry`), не трогает файлы и честно отвечает `failed` / `local_purge_unverified`: это то же правило, по которому из порта уже удаляли фиктивные подтверждения удаления. Достижимы три состояния проверки — `deleted`, `failed` и `unverified`; `tombstoned` и `cryptographicallyUnrecoverable` в порт не переносятся, потому что строка уходит вместе с копией, а локальные буферы не шифруются. Доказанное удаление записывается в реестр (`purge_acknowledgements`) до отправки ответа, поэтому потерянный ответ не превращает выполненную очистку в неудачу, когда сервер спросит снова; записываются только доказанные удаления, иначе неудача заморозила бы копию. Проход идёт в рабочем потоке по сети и на потоке владельца по файлам и реестру, запускается раз в минуту и сразу после принятого удаления; встречи с подтверждённым удалением без задачи запрашиваются адресно. Расхождение с macOS: macOS отвечает от терминальной строки, которую оставляет в очереди, а Windows хранит запись об ответе. Регрессии — семь наборов в `DesktopDeletionLedgerTests.cpp`; портируемая полоса 25/25, полоса приложения собрана, установленный пакет содержит `local-purge-tasks`, `purge_local_buffers`, `purge_acknowledgements`, `local_artifacts_deleted` и `local_purge_unverified`, запуск из пакета `hr=0x00000000`, процесс жив 30 секунд, `responding=True`.
- [X] T084 [P] Починить живое переключение оформления: смена темы внутри кабинета меняет страницу, но не оболочку — панель записи, рельс, панель инструментов и заголовок окна остаются прежними, пока не нажата перезагрузка. Мост `app_appearance` объявлен и в macOS, и в Windows; нужно найти, почему при живом изменении `data-theme` объявление не доходит, и закрыть расхождение. Доказательства: `specs/200-windows-desktop-app/validation-2026-09-17.md`, раздел раунда 30. Закрыто 2026-09-18: причина — объявление `app_appearance` не входило в список разрешённых команд моста, поэтому проверка конверта отбрасывала его как `commandDenied`; добавлено в `isAllowedWebCommand`, покрыто проверкой конверта, живая смена темы в обе стороны снята (`graf-r31-theme-live-light.png`, `graf-r31-theme-live-dark.png`).
- [X] T084 [US2] После T080–T083 собрать и запустить Windows приложение, пройти сценарии из актуального spec.md и `specs/200-windows-desktop-app/quickstart.md`, сохранить безопасные результаты в `specs/200-windows-desktop-app/validation-2026-09-06.md`, обновить `changes/unreleased/F200.yaml`; не закрывать непроверенные auth/hardware/signing сценарии (SC-001–010). Ручной `--run-unmuted` и повторный `--run` прошли Record/Pause/Resume/WebView reload/Stop до `saved_local`; auth/upload, hardware, signing и SC-003 оставлены открытыми.

- [ ] T063 После T067/T070/T071/T072/T073/T074/T075 выполнить полный `specs/200-windows-desktop-app/quickstart.md`, Windows x64 hardware/package evidence и `infra/scripts/ci-local.sh --fast`; зафиксировать exact SHA, skipped ARM64 lane и known limitations. Состояние на 2026-09-18: выполнимая часть зафиксирована. Точка отсчёта `4b25d6cd2745b89da7a44910d848b2cefc313230`; плановые серверные тесты для этого diff (`test_settings_ui_contract.py`, `test_settings_view_models.py`) — 36 passed; тесты управления репозиторием — 735 passed, 16 skipped; полосы Windows (портируемая 26/26, приложение, пакет) пройдены, пакет установлен и запускается. Диагностическая полоса `infra/scripts/ci-local.sh --focused` проходит: `ci_focused_result=pass scope=working_tree_diagnostic coverage=partial`, те же 36 плановых тестов. `--plan` показывает `dirty_worktree=true`, `next_gate=governance-fast_then_release-full`. Сам `--fast` доказательств не связывает и отвечает `ambiguous` / `fail` с причиной `dirty_worktree`: он отказывается привязывать доказательство к состоянию, которое нельзя назвать точным, пока изменения Feature 200 не закоммичены. Значит, ворота нужно запустить после согласованного коммита, и до этого момента задача остаётся открытой. `scripts/check_spec_kit_governance.py` сообщает о расхождении окружения: установлен `specify v1.0.4` вместо ожидаемого замком `v1.0.7`; это не связано с Feature 200. Аппаратная матрица и кабинет под входом (T080/T081/T082, SC-001/SC-003) не выполнялись: нужен физический x64-компьютер с двумя реальными источниками звука и аккаунт для входа. Виртуальная машина даёт только эмуляцию ARM64 с x64-приложением и кабинет без входа. Подробности в `validation-2026-09-17.md`. Дополнено 2026-09-18 (коммит и полоса): работа закоммичена в `4f8127615d7f86bcff702d657086a691106b1b59`, дерево чистое, и `infra/scripts/ci-local.sh --fast` впервые связал доказательство с точным коммитом: `ci_lane requested=fast effective=fast components=server,infra,docs,unknown coverage=partial next_gate=full_before_release`, доказательство `.dev/ci-evidence/ci-fast-4f8127615d7f-f513a6f0ebf8.json`. Проверки процесса пройдены (`development-process: OK feature=repository-only`, `changelog-fragments: OK`, `legacy-impact: OK`). Итог `fail` по единственной внешней причине: `spec-kit-governance` сообщает `doctor found specify v1.0.4, expected v1.0.7` (замок проекта ожидает `spec_kit.version = v1.0.7`, ref `fe1d00e3ccaf495880aaf90fb0e17679e82f065b`; установлен `v1.0.4`, ref `cb610277fdea781fcfa83d20522c2db37c94068d`, путь `~/.local/share/uv/tools/specify-cli`). Штатное исправление — `speckit-bootstrap . --frozen` без `--skip-cli-update`; это правка окружения вне репозитория и оставлена на решение владельца.
- [X] T064 Провести финальный review `specs/200-windows-desktop-app/checklists/requirements.md`, `audio-capture.md`, `advanced-routing.md`, `security.md`, `ux.md`, `plan.md` и `tasks.md`; review 2026-08-29: 104/104 checklist items complete, T070/T071/T063 остаются открытыми до signed MSIX/clean-image и hardware/authenticated-cabinet evidence; deploy/release не запускать без отдельного approval.

## Phase 12: Convergence

- [X] T085 [US1] CRITICAL: исправить общую шкалу двух источников в `apps/windows/RecApp/Audio/ClockMapper.*`, `AudioNormalizer.*`, `RecordingAudioTimeline.*` и `WasapiCaptureWorker.cpp` per FR-009/FR-018/SC-003, plan: Audio pipeline (partial). Сначала воспроизвести независимые device origins, сдвиг начала источников, округлённые метки при ±100 ppm, краткое колебание, переменный размер пакетов, startup/midstream discontinuity и противоречие count/device delta в существующих `Tests/GrafWindowsCoreTests/`. Использовать QPC в 100-нс единицах для общей шкалы, отделить погрешность метки от устойчивого дрейфа, реализовать только обоснованную коррекцию в пределах 48 кадров по правилам macOS; недостоверные метки, смена устройства и невосстановимый разрыв по-прежнему прекращают нормальный сегмент. До реализации уточнить контракт и провести независимую проверку требований/analyze; после — portable/native tests и отдельную реальную проверку T084. Не заменять 60-минутную SC-003 коротким запуском VM. Реализованы bounded dispatch queue и `GetNextPacketSize`; portable/native 20/20 и ручной Windows-прогон PASS. SC-003 остаётся в T063.

Продолжение T085/T081 по контракту §5: ограниченная подготовка первого пакета
и точная безопасная диагностика через существующие
`Capture/WindowsCaptureSessionController.*`, `Diagnostics/MetadataSafeDiagnostics.*`
и `AppMain.cpp`. Отбрасывание учитывается, не меняет общий origin и не
ослабляет дальнейшие clock/count/flag gates. Тесты — существующие
`CaptureFaultStateTests`, `AudioNormalizerTests`, `WindowsDiagnosticsRedactionTests`.

Проверка startup-среза 2026-09-07: код/review и portable20/native20/ASan+UBSan4
прошли; первая попытка настоящего приложения после успешного отбрасывания
первого пакета отказала с render clock_drift / microphone sample_count_mismatch.
Эта запись историческая и дополнена последующим bounded-dispatch прогоном:
`--run-unmuted` и `--run` прошли до `saved_local`; тихий режим без пригодного
источника ожидаемо завершился fail-closed. Техническая часть T085 закрыта,
а SC-003 и аппаратные/пакетные ворота остаются в T063/T070/T071.
Evidence: последний раздел `validation-2026-09-06.md`.

## Phase 13: Сведение с master от 2026-09-17 (Windows parity)

Ветка Feature 200 отстала от master на 68 коммитов; сведение выполнено коммитом
`4b25d6cd2`. Всё, что master добавил в macOS-приложении, должно появиться и в
Windows-приложении, иначе «полная копия под Windows» неполна. Серверные фичи
(F266, F267, F268, F270) приходят через кабинет на WebView и отдельной нативной
работы не требуют. Задачи ниже закрываются только с evidence в
`specs/200-windows-desktop-app/`.

- [X] T086 [US1] Реализовать порог короткой записи F6796 в Windows: 30 секунд канонического аудио, отмена сохранения только при нормальной остановке, сохранение фрагмента при прерывании и сбое захвата, пассивное уведомление без прав на системные уведомления и подметание недоделанной очистки. Файлы: `apps/windows/RecApp/Contracts/WindowsDesktopContracts.h`, `Recording/V5LocalRecordingWriter.*`, `Upload/DesktopUploadQueueService.*`, `Capture/WindowsCaptureSessionController.*`, `Shell/RecordingNoticePresenter.*`, `AppMain.cpp`, тест `Tests/GrafWindowsPackageTests/ShortRecordingThresholdTests.cpp`. Порог выводится из 10-мс канонического кадра: 30 с = 3 000 кадров; выражение его в сырых отсчётах отвергало бы любую запись. Проверено в ВМ: portable 21/21 PASS, `GrafWindowsApp.exe` собирается.
- [ ] T087 [US2] Перенести жизненный цикл удаления записи F262 в Windows: удаление из кабинета, из очереди и из локального хранилища как одна операция с повторяемым результатом, без осиротевших каталогов и без воскрешения удалённой записи при восстановлении очереди. Файлы: `apps/windows/RecApp/Upload/DesktopLocalPurgeService.*`, `Upload/DesktopUploadQueueService.*`, `Web/WebViewRoutePolicy.*`, `AppMain.cpp`, тесты удаления.
- [ ] T088 [US2] Перенести сохранение сессии приложения и аккаунта F6795/F6794 в Windows: сессия и выбранный аккаунт переживают перезапуск, выход очищает ровно своё, повторный вход не создаёт вторую сессию. Файлы: `apps/windows/RecApp/AppMain.cpp`, `Upload/DesktopApiClient.*`, `Storage/AtomicFileStore.*`, тесты.
- [ ] T089 [P] [US2] Перенести управление уведомлениями F249 в Windows: пользователь может выключить уведомления, выключенное состояние переживает перезапуск и не ломает запись. Файлы: `apps/windows/RecApp/Shell/`, `AppMain.cpp`, настройки, тесты.
- [X] T085 [P] Довести оформление нативных окон до конца: заголовки окон, окно настроек и меню значка в области уведомлений совпадают с оформлением кабинета в обеих темах; живое переключение темы проверено с журналами обеих сторон. Причина расхождения раунда 33 — отключённая сеть при переключении: кабинет не сохранил настройку и не объявил тему. Доказательства: `specs/200-windows-desktop-app/validation-2026-09-17.md`, раздел раунда 34. Не снято живьём: окно записи и окно автозаписи (появляются только при записи и срабатывании автозаписи), их оформление задаётся тем же кодом.
- [X] T086 [P] Проверить живьём возврат окна из значка области уведомлений: закрытие окна скрывает его, приложение остаётся в значке, щелчок по значку возвращает то же окно (в журнале приложения `tray-open`, в перечислении окон `visible`). Значок в этой машине лежит в переполнении области уведомлений. Доказательства: `specs/200-windows-desktop-app/validation-2026-09-17.md`, раздел раунда 36.
- [ ] T090 [P] [US1] Довести настройки, токены оформления и пользовательское время до текущего macOS: единый список выбора F6793, упрощение интерфейса F255, токены F240 и пользовательское время F252. Входит в срез T081 по `apps/windows/RecApp/AppMain.cpp`; сначала расширить тесты, затем удалить статические заглушки.
- [ ] T091 [P] [US3] Перенести мост настроек встроенного кабинета F264 в Windows и сверить совместимость моста загрузки, авторизации и кабинета с master, записав matrix в `specs/200-windows-desktop-app/parity-matrix.md`. Не менять серверную бизнес-логику. Расширяет T083.
- [X] T092 [US2] Выяснить и устранить причину, по которой установленное из MSIX приложение завершается до точки входа: под идентичностью пакета процесс живёт около 54 мс и возвращает код 0, `wWinMain` не вызывается, при этом тот же файл вне пакета работает. Причина: `RecApp/GrafWindowsApp.vcxproj` задавал `WindowsPackageType=None`, то есть собирал приложение как распакованное для Windows App SDK; в образ вкомпоновывался загрузчик рантайма (`MddBootstrapAutoInitializer.obj`, импорт `Microsoft.WindowsAppRuntime.Bootstrap.dll`), который запускается из статического инициализатора до `wWinMain` и внутри пакета не может разрешить рантайм. Исправление: `WindowsPackageType` берётся из `GrafWindowsPackageType`, а `.wapproj` передаёт `MSIX` через `AdditionalProperties`; распакованная полоса остаётся на `None`. Файлы: `apps/windows/RecApp/GrafWindowsApp.vcxproj`, `Installer/GrafWindows.Package.wapproj`. Проверено в ВМ: импорта загрузчика в полезной нагрузке пакета нет, установка `STATUS: Ok`, приложение из пакета запускается и держит окно `GRAF` все 20 с наблюдения, распакованная сборка после пересборки тоже запускается. Доказательства — в `specs/200-windows-desktop-app/validation-2026-09-17.md`, раздел T092.
- [X] T093 [P] [US2] Закрыть зависимость распространяемого пакета Visual C++ в MSIX: в манифест добавлена зависимость `Microsoft.VCLibs.140.00.UWPDesktop`; до правки установленный пакет объявлял только `Microsoft.WindowsAppRuntime.2`, после — обе платформы, установка и запуск проверены. Пакет `sha256=0B1BBCB7…`. Доказательства: `specs/200-windows-desktop-app/validation-2026-09-17.md`, раздел раунда 40.

Дополнено 2026-09-18 (раунд 25): приложение больше не считает запрет доступа к
микрофону исправным состоянием. Согласие читается по имени семейства пакетов,
запись не начинается без доступа, у каждой причины отказа свой текст, а отказ
микрофона ограничивает запись вместо её обрыва. Доказательства: раздел «Раунд 25»
в `validation-2026-09-17.md`, портируемая полоса 30/30, живые снимки панели
«Запись» и системных настроек. Открыто: живое подтверждение ограниченной записи
и поведение при отказе только системного звука — нужен физический компьютер
(T071), в ВМ оба источника нерабочие.
