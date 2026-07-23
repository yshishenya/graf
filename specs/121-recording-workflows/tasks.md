# Tasks: Complete Recording Workflows

**Input**: Design documents from `specs/121-recording-workflows/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/recording-workflow-contract.md`, `quickstart.md`

**Tests**: Required. This is a high-risk capture/privacy/auth/sharing/deletion feature; every story starts with the smallest focused tests that prove its trust boundary.

**Organization**: Tasks are grouped by independently testable user story. Do not begin implementation until the selected visual direction is recorded and `$speckit-analyze` has no CRITICAL blockers.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different files and has no incomplete dependency.
- **[Story]**: Maps to the user story in `spec.md`.
- Check a task `[X]` only after its focused validation passes and evidence is recorded.

## Phase 1: Planning And Prototype Gate

**Purpose**: Lock dependencies and selected clean-room expression before UI implementation.

- [X] T001 Create the connected 12-state prototype required by `specs/121-recording-workflows/ux-ia.md`, obtain user approval, and record the selected direction plus artifact path(s) in `specs/121-recording-workflows/research.md`
- [X] T002 Preserve this planning package, fast-forward the feature branch to `origin/master` at `43f7b09e`, refresh the managed Spec Kit plan pointer, and re-verify feature 106 open installed-app T063 plus feature 120 contracts, merged embedded-download T060, controlled preview, draft package `v2026.07.22.1`, and open general-release T059 in `specs/121-recording-workflows/plan.md`
- [X] T003 [P] Add 12-state prototype synthetic data, one-primary-action assertions, and forbidden-content rules to `specs/121-recording-workflows/quickstart.md`
- [X] T004 Re-run read-only `$speckit-analyze` after constitution v4.0.0 plaintext-observability redesign over all feature artifacts and checklists; require CRITICAL/HIGH/MEDIUM/LOW `0/0/0/0`
- [X] T005 Run `$speckit-taskstoissues` after T004, update existing canonical Russian GitHub issues without duplicates, and pass the repository-wide issue validator

---

## Phase 2: Foundational Data, Policy, And Lifecycle

**Purpose**: Additive server truth required by templates and complete sharing.

**⚠️ CRITICAL**: Complete this phase before US5/US6 server implementation. Capture-only US1/US2 tests may start in parallel after T001–T004.

- [X] T006 [P] Add failing model and migration contract tests for templates, outcomes, retained plaintext Generation Call content/durable pending delivery/workspace-and-opaque correlation after parent deletion, prompt/config/schema/trace/plaintext-chunk provenance, operator-retained observability, deployment-global Prompt Optimization Runs/call ledger/checkpoints, grants, invitations, compatibility, and downgrade in `apps/server/tests/contract/test_recording_workflow_migration_contract.py`
- [X] T007 [P] Add failing disposable PostgreSQL/RLS tests for tenant template/outcome/grant/invitation/token isolation plus privileged-role-only denial tests for the deployment-global optimizer control plane in `apps/server/tests/integration/test_recording_workflow_rls.py`
- [X] T008 Extend meeting/outcome models with retained plaintext Generation Call request/transcript/raw-response/validated-result content, required retained workspace plus stable opaque meeting/candidate correlations, authoritative per-call `pending|confirmed` observation delivery with a read-time attempt aggregate, exact-or-unknown usage/cost provenance, and Temporal transcript hash/chunk provenance; keep optimizer deployment-global and access/invitations tenant-scoped in `apps/server/src/twobrain_rec_server/db/models/meeting.py`, `apps/server/src/twobrain_rec_server/db/models/outcomes.py`, and `apps/server/src/twobrain_rec_server/db/models/meeting_access.py`
- [X] T009 Add rollback-safe migration/RLS for retained plaintext Generation Call content/delivery fields, no-cascade opaque parent correlations, worker/operator-only post-delete lookup by workspace/opaque ID, plaintext chunk provenance, and privileged-role-only optimizer metadata in `apps/server/src/twobrain_rec_server/db/migrations/versions/0031_recording_workflow_templates_sharing.py`
- [X] T010 Register new model exports without parallel domain objects in `apps/server/src/twobrain_rec_server/db/models/__init__.py`
- [X] T011 [P] Extend bounded cabinet API enums and schemas for templates, candidates, audiences, invitations, and capabilities; keep optimizer control schemas out of ordinary cabinet APIs in `apps/server/src/twobrain_rec_server/api/schemas.py`
- [X] T012 [P] Extend metadata-only audit allowlists for template/summary/prompt-optimization/promotion/rollback/share/invitation/link events in `apps/server/src/twobrain_rec_server/processing/audit.py` and keep authorization-denial metadata bounded in `apps/server/src/twobrain_rec_server/cabinet/access.py`
- [X] T013 Register outcome attempts, retained Generation Call rows, Temporal History and Langfuse trace IDs as disclosed non-deletion observability copies, plus synthetic optimizer artifacts, grants, invitations, tokens, and temporaries in lifecycle accounting in `apps/server/src/twobrain_rec_server/deletion/report.py`, `apps/server/src/twobrain_rec_server/deletion/service.py`, and `apps/server/src/twobrain_rec_server/cli/prompt_optimization.py`
- [X] T014 Make T006 and T007 pass, including legacy rows and downgrade/rollback evidence, and record counts in `specs/121-recording-workflows/quickstart.md`

**Checkpoint**: Additive tenant/lifecycle truth is available; no user-facing route is enabled yet.

---

## Phase 3: User Story 1 - Start A Trustworthy Recording (Priority: P1) 🎯 MVP

**Goal**: Present one clear permission/readiness/detect-and-ask/start flow over the existing native capture engine.

**Independent Test**: Complete quickstart scenarios 1–2 without network and prove one deliberate recording identity.

### Tests For User Story 1

- [X] T015 [P] [US1] Add failing readiness, silence-versus-unavailable, duplicate Start, and Feature-121 baseline detect-and-ask tests in `apps/macos/Shared/Tests/CaptureControlV5Tests.swift`; the no-countdown assertion is historical and superseded by Feature 124.
- [X] T016 [P] [US1] Add failing permission recovery and Russian accessibility tests in `apps/macos/Shared/Tests/SystemAudioPermissionUXTests.swift` and `apps/macos/Shared/Tests/AppControlAccessibilityTests.swift`
- [X] T017 [P] [US1] Add failing meeting-detection baseline suppression tests in `apps/macos/Shared/Tests/MeetingDetectionPolicyTests.swift`; Feature 124 owns restored target-scoped auto-record behavior.

### Implementation For User Story 1

- [X] T018 [US1] Project one current readiness state/primary action and quiet healthy source summary into `apps/macos/RecApp/Sources/Capture/CaptureControlViewCore.swift`
- [X] T019 [US1] Reuse existing permission services to present separate microphone and Screen/System Audio recovery actions in `apps/macos/RecApp/Sources/Capture/DesktopPermissionOnboardingView.swift`
- [X] T020 [US1] Keep repeated Start idempotent and remove any second active Start affordance. The historical replacement of the eight-second auto-start/countdown plus in-prompt auto-record toggle with Start/Not now is superseded for verified targets by Feature 124, which restores that contract in `apps/macos/RecApp/App/TwoBrainRecApp.swift`.
- [X] T021 [US1] Make T015–T017 pass and record quickstart scenarios 1–2 in `specs/121-recording-workflows/quickstart.md`

**Checkpoint**: Manual Start and the Feature-121 detect-and-ask baseline are
independently usable; Feature 124 separately owns the restored target-scoped
auto-record path, and no new audio engine exists.

---

## Phase 4: User Story 2 - Control And Recover An Active Recording (Priority: P1)

**Goal**: Keep consistent Pause/Resume/Stop, source degradation, and crash-safe custody across native surfaces.

**Independent Test**: Complete quickstart scenarios 3–5 and preserve every durable synthetic recording.

### Tests For User Story 2

- [X] T022 [P] [US2] Add failing active/paused/source-degraded projection tests in `apps/macos/Shared/Tests/CaptureIndicatorTests.swift`
- [X] T023 [P] [US2] Add failing one-action Stop, keyboard reachability, and plain-Escape-does-not-stop tests in `apps/macos/Shared/Tests/AppControlAccessibilityTests.swift`
- [X] T024 [P] [US2] Add failing crash/finalize/upload reconciliation and last-usable-copy tests in `apps/macos/Shared/Tests/DesktopUploadQueueV5Tests.swift`
- [X] T025 [P] [US2] Add failing v5 pause/privacy/source-degradation manifest tests in `apps/macos/Shared/Tests/CanonicalRecordingManifestTests.swift`

### Implementation For User Story 2

- [X] T026 [US2] Reuse one calm state projection for titlebar/main capture strip—text status, timer, one primary action, one secondary action—in `apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift`
- [X] T027 [US2] Keep menu-bar active/paused state and one-action Stop consistent, and remove the unsafe plain-Escape Stop shortcut in `apps/macos/RecApp/Sources/Capture/CaptureStatusItem.swift`
- [X] T028 [US2] Surface degraded source and bounded recovery without claiming seamless hot-switch in `apps/macos/RecApp/Sources/Capture/CaptureControlViewCore.swift`
- [X] T029 [US2] Preserve existing finalization/reconcile/purge authority while exposing actionable recovery state in `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`
- [X] T030 [US2] Make T022–T025 pass and record quickstart scenarios 3–5 in `specs/121-recording-workflows/quickstart.md`

**Checkpoint**: Active privacy control and local custody are independently complete; browser routes cannot hide Stop.

---

## Phase 5: User Story 3 - Follow Local Custody, Upload, And Processing (Priority: P1)

**Goal**: Show one artifact-specific lifecycle from local custody through upload and processing without a second queue.

**Independent Test**: Complete quickstart scenarios 5–6 across saved, queued, retrying, processing, partial, ready, and failed states.

### Tests For User Story 3

- [X] T031 [P] [US3] Add failing artifact-independent lifecycle projection tests in `apps/server/tests/unit/test_recording_workflow_view_model.py`
- [X] T032 [P] [US3] Add failing native local/server lifecycle projection tests in `apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift`

### Implementation For User Story 3

- [X] T033 [US3] Compose capture/upload/processing/artifact states without a second queue in `apps/server/src/twobrain_rec_server/cabinet/queries.py` and `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [X] T034 [US3] Make T031–T032 pass and record quickstart scenarios 5–6 in `specs/121-recording-workflows/quickstart.md`

**Checkpoint**: Custody/processing status is independently complete and does not duplicate queue authority.

---

## Phase 6: User Story 4 - Review One Complete Meeting Workspace (Priority: P1)

**Goal**: Keep synchronized playback/transcript/speaker review and the same authorized state in browser and embedded desktop.

**Independent Test**: Complete quickstart scenario 7 across ready/partial/failed/deleting/denied states.

### Tests For User Story 4

- [X] T035 [P] [US4] Add failing browser/embedded parity, exactly-two-content-tabs/no-permanent-right-rail, and denied-content contract tests in `apps/server/tests/contract/test_recording_workflow_review_contract.py`
- [X] T036 [P] [US4] Extend playback/timeline/speaker regression fixtures in `apps/server/tests/contract/test_cabinet_playback_contract.py`

### Implementation For User Story 4

- [X] T037 [US4] Render a calm meeting detail with `Итоги`/`Расшифровка`, persistent player, one human status, Share, and More while preserving playback/transcript/speaker authority in `apps/server/src/twobrain_rec_server/cabinet/rendering.py`, `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_detail_content.html`, and `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`
- [X] T038 [US4] Make T035–T036 pass and record quickstart scenario 7 in `specs/121-recording-workflows/quickstart.md`

**Checkpoint**: Review is independently complete with existing playback/speaker behavior and no cross-surface content leak.

---

## Phase 7: User Story 5 - Generate Notes From A Template (Priority: P1)

**Goal**: Add immutable GRAF built-ins, personal structured templates, candidate generation, and explicit accepted-revision replacement.

**Independent Test**: Complete quickstart scenarios 8–9, including stale edit/accept and failed generation.

### Tests For User Story 5

- [X] T039 [P] [US5] Add failing built-in/personal template, direct `Авто`, separate self-contained allowlisted Langfuse prompt per built-in plus one custom prompt, exact closed outcome/reflection v1 and retained-v1/new-v2 judge Config profiles, bounded outcome `category_states`+items consistency, exact GEPA placeholders/fence and judge variables, size/depth/count and remote-`$ref` rejection, explicit request projection/no-`**config`, promoted snapshot/hash pinning, verified-export fallback, route capability, prompt-injection, and version tests in `apps/server/tests/unit/test_summary_templates.py` and `apps/server/tests/unit/test_outcome_prompts.py`
- [X] T040 [P] [US5] Add failing idempotency, prompt pinning, exact plaintext transcript snapshot/hash/chunks, serialized size/restart/replay, transcript-equality race, crash before/after retained Generation Call persistence, ambiguous egress, sole-publisher durable pending delivery through outage/deletion without model replay, accept/reject, and conflict tests in `apps/server/tests/unit/test_summary_candidate_revisions.py` and `apps/server/tests/integration/test_outcome_generation_workflow.py`
- [X] T041 [P] [US5] Add failing template/candidate API, queued-row reconciliation, and authorization tests in `apps/server/tests/contract/test_summary_template_contract.py` and `apps/server/tests/integration/test_outcome_generation_dispatch.py`
- [X] T042 [P] [US5] Add failing LiteLLM/Langfuse exact-schema/full-request/transcript/raw-response/validated-result, sole generation publisher/original timestamps, private-project/no-public-trace configuration, prompt-link/selected-actual-model/exact-or-unknown-token-cost/environment/session/tag, fail-open durable pending delivery, and no-model-replay tests plus retained plaintext Generation Call parent-deletion survival and Temporal plaintext transcript History chunk/hash/order/pre/post-serialization-size/oversize tests in `apps/server/tests/unit/test_litellm_gateway.py`, `apps/server/tests/unit/test_langfuse_observability.py`, `apps/server/tests/contract/test_langfuse_runtime_contract.py`, and `apps/server/tests/contract/test_temporal_plaintext_history_contract.py`
- [X] T043 [P] [US5] Add failing `Авто`/maximum-four/`Все форматы` selector, Settings management, preserved-candidate, and focus tests in `apps/server/tests/contract/test_summary_template_ui_contract.py`

### Implementation For User Story 5

- [X] T044 [US5] Pin current stable `temporalio[opentelemetry]==1.30.0`, `opentelemetry-sdk==1.44.0`, existing `httpx==0.28.1`, and `langfuse==4.14.1`; add LiteLLM/Langfuse runtime secrets, configured Langfuse environment, plaintext chunk/history ceilings, and worker mounts without Feature-121 codec/AES keys, key management, or a new service in `apps/server/pyproject.toml`, `apps/server/constraints.txt`, `apps/server/src/twobrain_rec_server/config.py`, `infra/docker-compose.yml`, `infra/docker-compose.dev.yml`, and `infra/env/rec.production.env.example`
- [X] T045 [US5] Implement original seeded definitions, direct conservative `Авто`, personal template validation/versioning, allowlisted mapping to separate self-contained built-in Langfuse prompts plus one custom prompt, exact closed v1 Config validators and explicit LiteLLM request projection, explicit `production` resolution, atomically persisted exact prompt/config snapshot/hash, and integrity-checked promoted-version export fallback in `apps/server/src/twobrain_rec_server/outcomes/templates.py` and `apps/server/src/twobrain_rec_server/outcomes/prompts.py`
- [X] T046 [US5] Implement Langfuse v4 with `publish-observability` as the sole exact generation owner per completed response using original timestamps, nested full-content workflow observations, deterministic observation IDs, propagated environment/user/session/tags, activity attempts, prompt linkage, selected/actual model provenance, exact-returned-or-unknown token usage, exact-returned-or-Langfuse-calculated-or-unknown cost, explicit field selection without masking, and no unrelated global HTTP/SQL tracing in `apps/server/src/twobrain_rec_server/observability/langfuse.py` and `apps/server/src/twobrain_rec_server/workflows/temporal_client.py`
- [X] T047 [US5] Implement Generation Call reservation/ambiguous state, atomic retained plaintext request/transcript/raw-response/validated-result persistence before response acknowledgement, retained workspace/opaque correlations, exact hashes, zero-retry LiteLLM call/strict validation, ready-candidate publication independent of tracing, and durable `pending` Langfuse retry until confirmation without clearing content, stopping on meeting deletion, or repeating inference in `apps/server/src/twobrain_rec_server/outcomes/generator.py` and the dedicated Feature-121 orchestration boundary `apps/server/src/twobrain_rec_server/outcomes/ai_service.py`; preserve the existing non-AI projection owner in `apps/server/src/twobrain_rec_server/outcomes/service.py`
- [X] T048 [US5] Implement 192-KiB plaintext transcript snapshot activities through the default Temporal converter plus whole-set count/order/duplicate/UTF-8/final-hash validation, 256-KiB serialized payload and 8-MiB snapshot ceilings, retained History, and no Feature-121 PayloadCodec/encryption/key/Codec API in `apps/server/src/twobrain_rec_server/workflows/outcome_generation_workflow.py`, `apps/server/src/twobrain_rec_server/workflows/temporal_client.py`, and `apps/server/src/twobrain_rec_server/workflows/worker.py`
- [X] T049 [US5] Implement simple candidate-ready/failed projection, idempotent commands, plaintext transcript oversize/snapshot-invalid problem details, and no observability settings or infrastructure states in `apps/server/src/twobrain_rec_server/api/cabinet.py`, `apps/server/src/twobrain_rec_server/api/schemas.py`, `apps/server/src/twobrain_rec_server/cabinet/view_models.py`, and `apps/server/src/twobrain_rec_server/cabinet/review_policy_rendering.py`
- [X] T050 [US5] Create/promote the `graf/meeting-outcome/<built-in-key>` prompts plus `custom`; prove configured private Langfuse destination/environment with no public trace publishing, full plaintext observation content and attributes, fail-open durable pending delivery, LiteLLM capability, retained Generation Call content, plaintext transcript in Temporal History/size ceilings, make T039–T043 pass, and record quickstart scenarios 8–9 and 15 in `specs/121-recording-workflows/quickstart.md`
- [X] T051 [P] [US5] Add failing deployment-global optimizer persistence, privilege denial, pinned reflection/judges, synthetic-only manifests, full plaintext optimization History/Langfuse observations, crash/failover/fencing/deadline/budget/cancel, stale-source, held-out publication, serialized promotion/conflict, and separate rollback tests in `apps/server/tests/unit/test_prompt_optimization.py` and `apps/server/tests/integration/test_prompt_optimization_workflow.py`
- [X] T052 [P] [US5] Add failing GEPA adapter tests for shared inference/validation, durable-success reuse/fencing/ambiguous charging, checkpoint restore, callback isolation, immutable synthetic splits, local hard gates, calibrated judges, complete plaintext task/reflection/judge observation and History content, config equality, and zero auto-promotion in `apps/server/tests/unit/test_gepa_prompt_optimizer.py` and `apps/server/tests/contract/test_prompt_optimization_contract.py`
- [X] T053 [US5] Add `gepa==0.1.4` only to the optional evaluation dependency group without DSPy/full extras and refresh the dependency lock in `apps/server/pyproject.toml` and `apps/server/constraints.txt`
- [X] T054 [US5] Create candidate reflection and three judge prompts; gate them on parser/preservation/anti-copy/cost or frozen human-labelled calibration/invalid-output/agreement/operator approval, then implement the thin adapter with shared checkpoints, fenced ledger, budget/held-out isolation, exact synthetic model-call generations, and aggregate-only surrounding callbacks in `apps/server/src/twobrain_rec_server/outcomes/prompt_optimization.py`
- [X] T055 [US5] Implement and register deployment-operator-triggered `PromptOptimizationWorkflow` plus separate `PromptRollbackWorkflow` with deterministic IDs/linked traces, pinned contract, dedicated concurrency-one GEPA activity, heartbeat/failover/resume, immutable deadline and fenced reservations, observed-call-only generations, held-out-before-publication, exact numeric candidate with no manual candidate/staging/production label, expiring opaque audit-action Temporal Updates whose activity rechecks operator authorization, per-prompt serialization/expected-source recheck/label update/cache-clear/post-verification conflict detection, protected-label sole-credential gate, and rollback in `apps/server/src/twobrain_rec_server/workflows/prompt_optimization_workflow.py`, `apps/server/src/twobrain_rec_server/workflows/prompt_rollback_workflow.py`, `apps/server/src/twobrain_rec_server/workflows/temporal_client.py`, and `apps/server/src/twobrain_rec_server/workflows/worker.py`
- [X] T056 [US5] Add the least-privilege deployment-operator CLI for starting, inspecting, approving, rejecting, expiring, rolling back, and purging only GRAF-owned synthetic optimization rows/call-ledger rows/checkpoints while retaining Langfuse observations and Temporal History; reuse metadata-only audit primitives and expose no cabinet/workspace-admin route or dataset/prompt content in `apps/server/src/twobrain_rec_server/cli/prompt_optimization.py` and `apps/server/src/twobrain_rec_server/processing/audit.py`
- [X] T057 [US5] Run one synthetic optimization across two workers with forced crash and gated reflection/judge promotion; verify checkpoint/fencing/reuse/ambiguous accounting/deadline/config/held-out/promotion/rollback plus complete plaintext task/reflection/judge content in Langfuse and Temporal History, stable-interceptor limitation, and no JEPA/DSPy dependency; record scenario 16 evidence in `specs/121-recording-workflows/quickstart.md`

**Checkpoint**: Template generation is independently useful and cannot silently replace accepted notes.

---

## Phase 8: User Story 6 - Share The Minimum Necessary Content (Priority: P1)

**Goal**: Complete internal sharing first, then gated workspace/team/link/external invitation flows with narrow projections and immediate revocation.

**Independent Test**: Complete quickstart scenarios 10–12; keep public/external runtime disabled unless its focused gate is active.

### Tests For User Story 6

- [X] T058 [P] [US6] Add failing audience/content/download/export policy and effective-access tests in `apps/server/tests/unit/test_recording_workflow_access.py`
- [X] T059 [P] [US6] Extend internal grant, wrong-user, revoke, and summary-only direct-route tests in `apps/server/tests/contract/test_access_sharing_downloads_contract.py`
- [X] T060 [P] [US6] Add failing link hash/expiry/rotation/revoke/rate-limit/narrow-projection tests in `apps/server/tests/contract/test_recording_share_link_contract.py`
- [X] T061 [P] [US6] Add failing invitation normalization/encryption, deterministic Temporal delivery workflow, duplicate/retry/restart/cancel, accept/revoke, and enumeration tests in `apps/server/tests/contract/test_recording_share_invitation_contract.py` and `apps/server/tests/integration/test_invitation_delivery_workflow.py`
- [X] T062 [P] [US6] Add failing simple-first Share, progressive content/audience disclosure, no role/capability matrix, recipient-bound Copy link, revoke, and focus tests in `apps/server/tests/contract/test_recording_share_ui_contract.py`

### Implementation For User Story 6

- [X] T063 [US6] Extend existing grant policy for audience/content/capabilities while preserving recipient-token behavior in `apps/server/src/twobrain_rec_server/cabinet/access.py`
- [X] T064 [US6] Extend share/grant/revoke/rotate and recipient search APIs with deletion-first authorization in `apps/server/src/twobrain_rec_server/api/cabinet.py`
- [X] T065 [US6] Implement rate-limited hashed link resolution and summary-only narrow projection in `apps/server/src/twobrain_rec_server/cabinet/access.py` and `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [X] T066 [US6] Implement the bounded pending invitation lifecycle by extending the existing cabinet access service and register one deterministic Temporal delivery workflow/activity in the existing worker in `apps/server/src/twobrain_rec_server/cabinet/access.py`, `apps/server/src/twobrain_rec_server/workflows/invitation_delivery_workflow.py`, `apps/server/src/twobrain_rec_server/workflows/temporal_client.py`, and `apps/server/src/twobrain_rec_server/workflows/worker.py`
- [X] T067 [US6] Add runtime-disabled-by-default invitation/link configuration and safety validation in `apps/server/src/twobrain_rec_server/config.py`
- [X] T068 [US6] Render person/email + Invite, current viewers/revoke, collapsed `Что увидят`, recipient-bound Copy link, and policy-gated broader access without first-screen role/download/export controls in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/meeting_share.html`
- [X] T069 [US6] Wire progressive HTML/HTMX Share routes and generic safe errors in `apps/server/src/twobrain_rec_server/cabinet/web_routes/browser.py` and `apps/server/src/twobrain_rec_server/cabinet/review_policy_rendering.py`
- [X] T070 [US6] Add selected-direction progressive-disclosure styling and keyboard/focus behavior without cockpit panels using existing tokens in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css` and `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`
- [X] T071 [US6] Make T058–T062 pass and record quickstart scenarios 10–12 in `specs/121-recording-workflows/quickstart.md`

**Checkpoint**: Internal sharing is independently complete; public/external remain fail-closed until their focused gates pass.

---

## Phase 9: User Story 7 - Export Or Delete With Lifecycle Truth (Priority: P2)

**Goal**: Activate meeting-detail export/download/delete flows using existing authorities and deletion-first races.

**Independent Test**: Complete quickstart scenario 13 without a parallel formatter or deletion worker.

### Tests For User Story 7

- [X] T072 [P] [US7] Add failing feature-120 availability composition and no-parallel-export tests in `apps/server/tests/contract/test_recording_workflow_export_contract.py`
- [X] T073 [P] [US7] Add failing generation/publication/acceptance plus template/share/invite/link/export deletion-race tests that cancel pre-egress work, block candidate publication/acceptance, preserve Generation Call rows after meeting/candidate purge, and continue sole-publisher Langfuse delivery for completed rows while retaining Temporal observability in `apps/server/tests/integration/test_recording_workflow_deletion_races.py`
- [X] T074 [P] [US7] Extend bounded deletion copy/report tests to name the retained plaintext Generation Call ledger, Langfuse observations, and Temporal History without treating them as failed purge; keep ordinary evidence free of meeting content in `apps/server/tests/contract/test_deletion_no_secret_leakage.py`
- [X] T075 [P] [US7] Add failing More-menu export/download/delete visibility, retained-observability disclosure, modal-focus, and capability-state tests in `apps/server/tests/contract/test_recording_governance_ui_contract.py`

### Implementation For User Story 7

- [X] T076 [US7] Compose canonical feature-120 export availability and existing audio/package actions in `apps/server/src/twobrain_rec_server/cabinet/egress.py` and `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [X] T077 [US7] Replace disabled governance panels with a contextual More menu and focused export/download/delete fragments in `apps/server/src/twobrain_rec_server/cabinet/review_policy_rendering.py` and `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/meeting_governance.html`
- [X] T078 [US7] Make deletion block new inference/publication/acceptance, cancel pre-egress Temporal work, cancel grants/invites/links/pending egress, purge normal GRAF meeting artifacts, preserve retained Generation Call rows across parent purge, continue their pending Langfuse delivery until confirmed, and retain Temporal History with truthful copy/report text in `apps/server/src/twobrain_rec_server/deletion/service.py`
- [X] T079 [US7] Make T072–T075 pass and record quickstart scenarios 13 and 15 retained-observability evidence in `specs/121-recording-workflows/quickstart.md`

**Checkpoint**: Export and deletion are independently complete with existing sources of truth.

---

## Phase 10: User Story 8 - Accessible Russian Cross-Surface Workflow (Priority: P2)

**Goal**: Prove the selected interface across keyboard, VoiceOver, responsive, embedded, theme, and localization states.

**Independent Test**: Complete quickstart scenario 14 end to end with synthetic data.

### Tests For User Story 8

- [X] T080 [P] [US8] Add failing modal/listbox/exactly-two-tab/live-region/focus-return/one-primary-action fixture tests in `apps/server/tests/contract/test_recording_workflow_accessibility.py`
- [X] T081 [P] [US8] Add failing Russian/debug-copy and forbidden-competitor-expression checks in `apps/server/tests/contract/test_recording_workflow_cleanroom.py`
- [X] T082 [P] [US8] Extend native narrow-window, keyboard, increased-contrast, and reduced-motion tests in `apps/macos/Shared/Tests/AppControlAccessibilityTests.swift`

### Implementation For User Story 8

- [X] T083 [US8] Add shared dialog/popover focus utilities only where existing cabinet code cannot cover the contract in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`
- [X] T084 [US8] Finish responsive, dark/light, reduced-motion, increased-contrast, and visible-focus rules in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`
- [X] T085 [US8] Normalize Russian labels and keep UI locale, transcript language, and summary output language distinct in `apps/server/src/twobrain_rec_server/cabinet/rendering_shared.py` and `apps/macos/RecApp/Sources/Capture/CaptureControlViewCore.swift`
- [X] T086 [US8] Make T080–T082 pass and record the connected 12-state keyboard/VoiceOver/viewport/theme evidence for quickstart scenario 14 in `specs/121-recording-workflows/quickstart.md`

**Checkpoint**: The complete workflow is operable without pointer precision, color, motion, or English/debug copy.

---

## Phase 11: Validation, Review, Release Boundary, And Documentation

**Purpose**: Prove the integrated result without crossing commit/release/deploy approval gates.

- [X] T087 [P] Run the focused macOS suite and contract validator from `specs/121-recording-workflows/quickstart.md`
- [X] T088 [P] Run focused server unit/contract/integration and disposable PostgreSQL/RLS suites from `specs/121-recording-workflows/quickstart.md`
- [X] T089 [P] Run content-location scans proving complete plaintext meeting/model content in Langfuse AI observations and retained Generation Call rows plus the complete plaintext canonical transcript in Temporal History; prove zero raw audio/runtime credentials or meeting content in ordinary logs/screenshots/audit/diagnostics/committed evidence; record only metadata-safe evidence in `specs/121-recording-workflows/quickstart.md`
- [X] T090 Run the canonical repository gate `infra/scripts/ci-local.sh` and record exact counts/result in `specs/121-recording-workflows/quickstart.md`
- [X] T091 Run independent review of token/invitation/RLS/CSRF/rate-limit plus private Langfuse v4 full-content trace shape/sole generation publisher/durable pending fail-open delivery and Temporal plaintext transcript chunk/hash/size/retention boundaries; verify Generation Call parent-deletion survival, no Feature-121 codec/key/delete subsystem, and GEPA lifecycle/purge/deletion races in `specs/121-recording-workflows/quickstart.md`
- [X] T092 Run `@ponytail-review` and remove unnecessary new abstractions/dependencies while preserving trust, accessibility, and tests; record outcome in `specs/121-recording-workflows/quickstart.md`
- [X] T093 Reconcile constitution v4.0.0, `spec.md`, `plan.md`, `research.md`, data model, contracts, tasks, all content-boundary checklists, GitHub issues, and validation evidence in `specs/121-recording-workflows/quickstart.md`
- [X] T094 Update behavior/architecture/UX/QA status in `CHANGELOG.md` and `docs/current-product-status.md`
- [X] T095 Stop for explicit user approval before commit, push, PR, deploy, release, or installed-app replacement
- [X] T096 [P0] [US5] Restore the canonical accepted-summary pointer for legacy and newly generated baseline outcomes, make published review/share/export content read only that pointer while preserving non-publishable processing/failure truth, and add migration/runtime/UI-to-API-to-Temporal regression coverage in `apps/server/src/twobrain_rec_server/db/migrations/versions/0032_backfill_current_outcome_set.py`, `apps/server/src/twobrain_rec_server/outcomes/service.py`, `apps/server/src/twobrain_rec_server/cabinet/egress.py`, `apps/server/src/twobrain_rec_server/cabinet/queries.py`, `apps/server/tests/contract/test_current_outcome_set_backfill_contract.py`, `apps/server/tests/contract/test_summary_template_ui_contract.py`, `apps/server/tests/integration/test_cabinet_meeting_outcomes.py`, `apps/server/tests/integration/test_meeting_outcomes_generation.py`, `apps/server/tests/integration/test_transcript_export_egress.py`, and `apps/server/tests/unit/test_summary_candidate_revisions.py`

- [X] T097 [P0] [US5] Make outcome-generation workflow result annotations compatible with Temporal's default converter (including replay of already-completed child histories), keep Langfuse span filtering sandbox-safe, and add an SDK-level child-completion regression test in `apps/server/src/twobrain_rec_server/workflows/outcome_generation_workflow.py`, `apps/server/src/twobrain_rec_server/observability/langfuse.py`, `apps/server/tests/integration/test_outcome_generation_workflow.py`, and `apps/server/tests/contract/test_langfuse_runtime_contract.py`.
- [X] T098 [P1] [US5] Make owner candidate recovery server-authoritative and explain bounded failure reasons: add owner-only candidate listing/preview projection, retryability/next-action fields, selected-format pending UI, reload/new-device recovery, and preserve accepted/share truth in `apps/server/src/twobrain_rec_server/api/schemas.py`, `apps/server/src/twobrain_rec_server/api/cabinet.py`, `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`, `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_detail_content.html`, and focused cabinet contracts.
- [X] T099 [P1] [US5] Reconcile candidate regeneration business rules and UX scenario matrix (initial policy-owned Auto attempt, explicit later regeneration, source/prompt/config changes, candidate history, stale/deletion/ambiguous outcomes) in `specs/121-recording-workflows/spec.md`, `specs/121-recording-workflows/data-model.md`, and `specs/121-recording-workflows/ux-ia.md`, with quickstart evidence and no transcript-bearing committed fixtures.
- [X] T100 [P0] [US5] Recover the known production outcome workflow without replaying inference, run focused and canonical CI, deploy the forward-compatible worker, and record metadata-only Temporal/Langfuse/Generation-Call smoke evidence plus CalVer release/rollback readiness in `specs/121-recording-workflows/quickstart.md`, `docs/current-product-status.md`, and `CHANGELOG.md`.

---

## Dependencies And Execution Order

### Phase Dependencies

- Phase 1 is the product/prototype gate.
- Phase 2 is foundational for US5/US6 and may proceed in parallel with capture tests only after T001–T004.
- US1 and US2 reuse existing native capture and can be delivered independently.
- US3 reuses current review/playback and can proceed after its tests and selected prototype.
- US5 depends on Phase 2 outcome/template fields.
- US6 depends on Phase 2 grant/invitation fields; internal sharing must pass before public/external gates are enabled.
- US7 depends on feature 120 acceptance plus US5/US6 lifecycle hooks.
- US8 follows the selected UI for desired stories and remains required before integrated validation.
- Phase 11 follows all desired stories and does not authorize release actions.

### User Story Dependencies

- **US1**: Independent after prototype/analysis gate.
- **US2**: Independent after prototype/analysis gate; reuses current capture/queue.
- **US3**: Independent after prototype/analysis gate; reuses current server review.
- **US4**: Independent after prototype/analysis gate; reuses current playback, transcript, speaker, and access authorities.
- **US5**: Depends on foundational template/outcome migration.
- **US6**: Depends on foundational access/invitation migration.
- **US7**: Depends on feature 120 and lifecycle hooks from US5/US6.
- **US8**: Applies to whichever stories are implemented and cannot be skipped for release.

## Parallel Opportunities

- T006/T007, T011/T012, and most story test files marked `[P]` can run in parallel.
- Native US1/US2 tests can run while foundational server models are implemented.
- US3 review tests can run while template and sharing services are built.
- Within US5/US6, service/API and HTML work begins only after the failing contracts exist and model/migration tests pass.
- Security, accessibility, and forbidden-content reviews use separate evidence and can run in parallel before final CI.

## Implementation Strategy

### First Independently Shippable Increment

1. Complete prototype/analysis and foundational compatibility gates.
2. Deliver US1 + US2 native capture-state completeness without changing audio engine/package.
3. Validate Stop, degraded state, offline custody, and crash recovery.
4. Stop for review before server policy expansion.

### Post-Meeting Increment

1. Deliver US3 review convergence.
2. Deliver US5 template candidates/revisions.
3. Deliver internal-user portion of US6.
4. Keep public/external flags off until their security/delivery gates pass.

### Governance Increment

1. Reconcile/consume feature 120.
2. Activate US7 export/delete composition.
3. Finish US8 cross-surface accessibility and Phase 11 validation.

## Notes

- Reuse before writing; production adds only pinned Langfuse/OpenTelemetry
  support around the existing Temporal/httpx boundary. GEPA is an optional
  offline evaluation dependency; DSPy, LiteLLM SDK, and OpenAI SDK are not
  added to the production worker.
- Tests precede implementation for every non-trivial state, parser, policy, and race.
- Do not mark `[X]` from code inspection alone; focused validation evidence is required.
- Do not commit, push, open a PR, deploy, release, or install without the explicit gates in T095.
