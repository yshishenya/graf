# Tasks: Глобальный автозапуск и безопасные defaults

**Input**: Design documents from `/specs/194-global-auto-start-defaults/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`,
`contracts/global-auto-start-policy.md`, `quickstart.md`, and completed safety
checklists.

**Tests**: Обязательны до реализации из-за high-risk capture/policy/UX lane.

## Phase 1: Explicit global policy (US1)

**Goal**: Publish policy to every authenticated workspace only when the operator
explicitly selects and approves global scope.

- [X] T001 [P] [US1] Add config unit tests for disabled, scoped, approved global,
  missing approval and ambiguous global/workspace combinations in
  `apps/server/tests/unit/test_config_validation.py`.
- [X] T002 [P] [US1] Add API contract tests for global scope, opaque reference
  bindings and backward-compatible scoped mode in
  `apps/server/tests/contract/test_meeting_detection_api_contract.py`.
- [X] T003 [US1] Add explicit global-scope settings, strict validation and env
  aliases in `apps/server/src/twobrain_rec_server/config.py`.
- [X] T004 [US1] Extend the policy schema and projection with validated `scope`
  and global policy reference semantics in
  `apps/server/src/twobrain_rec_server/api/schemas.py` and
  `apps/server/src/twobrain_rec_server/api/meeting_detection.py`.
- [X] T005 [US1] Pass global policy variables through `infra/docker-compose.yml`
  and document fail-closed internal-only defaults in
  `infra/env/rec.production.env.example`.

**Checkpoint**: Scoped behavior remains unchanged; approved global behavior is
covered by server tests and Compose renders without wildcard inference.

## Phase 2: Fresh-install defaults (US2)

**Goal**: New installations detect meetings and select every verified native
prompt-capable target without overwriting existing user settings.

- [X] T006 [P] [US2] Add settings store tests for missing-file defaults, legacy
  marker migration, target filtering and idempotent user edits in
  `apps/macos/Shared/Tests/MeetingDetectionPolicyTests.swift`.
- [X] T007 [US2] Add backward-compatible Codable marker and atomic
  `applyFirstInstallDefaults(targetIDs:)` to
  `apps/macos/RecApp/Sources/MeetingDetection/MeetingDetectionSettingsStore.swift`.
- [X] T008 [US2] Apply defaults exactly when the first valid registry resolves in
  `apps/macos/RecApp/App/TwoBrainRecApp.swift`, preserving selected targets and
  emitting only bounded metadata diagnostics.
- [X] T009 [P] [US2] Validate policy scope and legacy cached policy decoding in
  `apps/macos/Shared/Sources/MeetingDetection/MeetingTargetRegistry.swift` and
  `apps/macos/Shared/Sources/MeetingDetection/MeetingDetectionModels.swift`.

**Checkpoint**: Clean settings select only verified native targets; old settings
remain unchanged after registry refresh or app update.

## Phase 3: Prompt-first default UX (US3)

**Goal**: A fresh install shows the existing prompt by default, while preserving
truthful no-acknowledgement behavior and current automatic-start gates.

- [X] T010 [P] [US3] Add policy tests for prompt output without acknowledgement,
  explicit button start, Skip/timeout suppression and saved-target fail-closed
  behavior in `apps/macos/Shared/Tests/MeetingDetectionPolicyTests.swift`.
- [X] T011 [US3] Add an `assistedAutoStartAuthorized` snapshot input so selected
  targets downgrade to prompt until the current acknowledgement exists in
  `apps/macos/Shared/Sources/MeetingDetection/MeetingDetectionPolicy.swift` and
  `apps/macos/RecApp/Sources/MeetingDetection/MacOSMeetingActivityDetector.swift`.
- [X] T012 [US3] Separate prompt detection/readiness from final automatic-start
  authorization, allow prompt-button current manual start without persisted ack,
  and keep timeout/saved-target rechecks in `apps/macos/RecApp/App/TwoBrainRecApp.swift`.
- [X] T013 [US3] Make prompt copy and countdown accessibility truthful for
  no-acknowledgement state, and persist acknowledgement only for explicit
  «Всегда писать это приложение» action in `apps/macos/RecApp/App/TwoBrainRecApp.swift`.

**Checkpoint**: New install gets a visible prompt; no hidden or automatic start
occurs before explicit opt-in, and existing Feature 193 timeout path is unchanged
after opt-in.

## Phase 4: Validation and documentation

- [X] T014 [P] [US3] Update Swift source-contract and focused UX assertions for
  default prompt behavior in `apps/macos/Shared/Tests/CaptureControlV5Tests.swift`
  and relevant meeting detection tests.
- [X] T015 [P] Update Russian changelog and product status with the default prompt
  and global-scope boundaries in `CHANGELOG.md` and `docs/current-product-status.md`.
- [X] T016 [US1] Run server focused tests, Swift focused suites, Compose config
  validation, metadata/evidence scan and the quickstart scenarios; record results
  in `specs/194-global-auto-start-defaults/validation/implementation-evidence.md`.
- [X] T017 [US3] Build a separate GRAF Dev app and perform synthetic first-run
  prompt/default smoke without replacing `/Applications/GRAF.app`.

## Dependencies & Execution Order

- T001–T002 before T003–T005.
- T006 and T009 before T007–T008.
- T010 before T011–T013.
- T014–T017 after all behavior tasks; T016 is final validation.

## Parallel Opportunities

- T001/T002, T006/T009, and T014/T015 touch independent files and may be worked
  in parallel, but this checkout executes them sequentially for reviewability.

## Implementation Strategy

1. Lock the server scope contract and fail-closed validation.
2. Add idempotent clean-install defaults.
3. Route unacknowledged selected targets to the existing prompt, not hidden
   automatic capture; keep final gates unchanged.
4. Validate the exact fresh-install and opt-in paths with synthetic evidence.
