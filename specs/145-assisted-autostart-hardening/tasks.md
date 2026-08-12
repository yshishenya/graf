# Tasks: Авторизация и доказательства автозаписи

**Input**: Design documents from `/specs/145-assisted-autostart-hardening/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/assisted-auto-start-policy.md`

**Tests**: Обязательны из-за high-risk capture lane. Для каждого story сначала
добавляются focused failing tests, затем минимальная реализация.

**Organization**: Задачи сгруппированы по user story и используют точные пути.

## Phase 1: Foundational policy contract

**Purpose**: Создать один fail-closed policy/acknowledgement seam, используемый
всеми detector-assisted путями.

- [X] T001 [P] [US1] Добавить failing server config/contract tests для disabled, incomplete, wrong-workspace, active и expired policy в `apps/server/tests/unit/test_config_validation.py` и `apps/server/tests/contract/test_meeting_detection_api_contract.py`
- [X] T002 [US1] Добавить fail-closed runtime fields, strict policy response schema, workspace-scoped policy projection и ETag participation в `apps/server/src/twobrain_rec_server/config.py`, `apps/server/src/twobrain_rec_server/api/schemas.py` и `apps/server/src/twobrain_rec_server/api/meeting_detection.py`
- [X] T003 [P] [US1] Добавить disabled-by-default runtime propagation и понятные production placeholders в `infra/docker-compose.yml` и `infra/env/rec.production.env.example`
- [X] T004 [P] [US1] Добавить failing Swift tests для policy decoding/expiry/cache и exact-reference acknowledgement migration в `apps/macos/Shared/Tests/MeetingTargetRegistryTests.swift` и `apps/macos/Shared/Tests/MeetingDetectionPolicyTests.swift`
- [X] T005 [US1] Реализовать policy snapshot и user+device+workspace-bound acknowledgement models, strict current-policy evaluation и backward-compatible atomic settings persistence в `apps/macos/Shared/Sources/MeetingDetection/MeetingDetectionModels.swift`, `apps/macos/Shared/Sources/MeetingDetection/MeetingTargetRegistry.swift`, `apps/macos/Shared/Sources/MeetingDetection/MeetingDetectionPolicy.swift` и `apps/macos/RecApp/Sources/MeetingDetection/MeetingDetectionSettingsStore.swift`
- [X] T006 [US1] Добавить отдельное явное разрешение актуальной policy в settings, сохранить выбранные target IDs при revoke и заменить фиктивный workspace gate в `apps/macos/RecApp/Sources/MeetingDetection/MeetingDetectionSettingsView.swift` и `apps/macos/RecApp/App/TwoBrainRecApp.swift`

**Checkpoint**: Без active scoped policy и exact acknowledgement detector может
определять встречу, но prompt countdown и saved-target start недоступны.

---

## Phase 2: User Story 2 — truthful start evidence (Priority: P1)

**Goal**: Button, timeout и saved-target start имеют разные правдивые причины и
approval/initiator semantics.

**Independent Test**: Три synthetic start decisions дают три стабильных reason
codes; timeout/saved-target не используют button confirmation или `.user`.

- [X] T007 [P] [US2] Добавить failing tests трёх start reasons, approval modes, policy snapshot refs и evidence initiators в `apps/macos/Shared/Tests/SystemAudioPermissionUXTests.swift`, `apps/macos/Shared/Tests/CaptureScopeApprovalTests.swift` и `apps/macos/Shared/Tests/RecordingEvidenceV5Tests.swift`
- [X] T008 [US2] Добавить единый detector-assisted decision, `priorUserAuthorization` approval, automated evidence initiator и явный policy snapshot input в `apps/macos/Shared/Sources/Models/SystemAudioCaptureCoreModels.swift`, `apps/macos/Shared/Sources/Models/AudioStates.swift`, `apps/macos/RecApp/Sources/Capture/CaptureScopeApprovalService.swift`, `apps/macos/RecApp/Sources/Capture/CaptureSessionController.swift` и `apps/macos/RecApp/Sources/Capture/RecordingEvidenceService.swift`
- [X] T009 [US2] Передавать `prompt_button`, `prompt_timeout` и `saved_target_policy` через общий start path и записывать metadata-only policy/ack/notice/route evidence в `apps/macos/RecApp/App/TwoBrainRecApp.swift`

**Checkpoint**: По одному session snapshot можно отличить три причины старта без
meeting content и без ложного user attribution.

---

## Phase 3: User Story 3 — current gates and countdown safety (Priority: P1)

**Goal**: Все изменяемые gates повторно проверяются перед стартом, countdown
разрешается один раз и остаётся доступным.

**Independent Test**: На 7.999 s старта нет; на 8.000 s safe path стартует один
раз; storage/policy/permission/target/active-session/indicator/Stop changes блокируют.

- [X] T010 [P] [US3] Добавить failing storage probe tests для healthy, low reserve, over-budget и measurement failure в `apps/macos/Shared/Tests/LocalBufferServiceTests.swift`
- [X] T011 [US3] Реализовать проверку фактического размера локальной upload queue и нативной free-capacity поверх `LocalBufferService.defaultPolicy` в `apps/macos/RecApp/Sources/Buffering/LocalBufferService.swift`
- [X] T012 [US3] Добавить current target activity query и единый immediate pre-start re-check policy/ack/target/permissions/storage/session/indicator/Stop в `apps/macos/RecApp/Sources/MeetingDetection/MacOSMeetingActivityDetector.swift` и `apps/macos/RecApp/App/TwoBrainRecApp.swift`
- [X] T013 [P] [US3] Добавить pure countdown state tests для 7.999/8.000 s, duplicate resolution, Start, Skip, disappearance и revoke в `apps/macos/Shared/Tests/MeetingDetectionCountdownTests.swift`
- [X] T014 [US3] Реализовать single-resolution countdown state и подключить точную timeout reason, видимые секунды и accessibility value в `apps/macos/Shared/Sources/MeetingDetection/MeetingDetectionPolicy.swift` и `apps/macos/RecApp/App/TwoBrainRecApp.swift`

**Checkpoint**: Countdown сохраняет Feature-124 UX, но ни один stale/racing path
не может начать вторую или уже запрещённую запись.

---

## Phase 4: User Story 4 — regression protection (Priority: P2)

**Goal**: Поведение защищено исполняемыми tests и release evidence.

**Independent Test**: Focused suites падают при снятии policy/ack/storage re-check,
смешивании reason codes или расширении eligibility.

- [X] T015 [P] [US4] Расширить behavioral detector tests для unknown, browser/manual-only, diagnostic-only, suppressed и saved-target authorization paths в `apps/macos/Shared/Tests/MeetingDetectionPolicyTests.swift`
- [X] T016 [P] [US4] Обновить русский behavior/release status без обещания deployment в `CHANGELOG.md` и `docs/current-product-status.md`
- [X] T017 [US4] Выполнить quickstart focused suites и `infra/scripts/ci-local.sh`, записать команды, результаты, ограничения ручного smoke и no-deploy verdict в `specs/145-assisted-autostart-hardening/validation/implementation-evidence.md`

---

## Dependencies & Execution Order

- T001 и T004 сначала фиксируют ожидаемый fail-closed contract.
- T002 зависит от T001; T005 зависит от T004; T006 зависит от T002 и T005.
- T007 выполняется после T006 и до T008–T009.
- T010 и T013 можно выполнять параллельно после policy foundation.
- T011 зависит от T010; T012 зависит от T006, T009 и T011; T014 зависит от T013.
- T015–T017 выполняются после T012 и T014.

## Parallel Opportunities

- Server tasks T001–T003 и Swift model tests T004 можно выполнять параллельно.
- T010 и T013 независимы.
- T015 и T016 независимы после реализации.

## Implementation Strategy

1. Сначала policy contract и migration-safe acknowledgement.
2. Затем truthful reason/evidence через общий start path.
3. Затем real storage, target activity и deterministic countdown.
4. В конце regression suites, docs и full local CI.

Не создавать новую БД, endpoint, audio engine, detector heuristic или dependency.
Production policy остаётся выключенной до отдельного release/deploy решения.
