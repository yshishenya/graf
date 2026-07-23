# Tasks: Meeting Content Regeneration Lifecycle

**Input**: Design documents from `/specs/124-content-regeneration-lifecycle/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`,
`contracts/`, `quickstart.md`, and the constitution.

**Tests**: High-risk implementation. Tests are written before or alongside each
story and use synthetic/metadata-only fixtures.

**Organization**: Dependency ordered, but each user-story phase has an
independent acceptance target after the foundational schema/fence work.

## Phase 1: Setup and guardrails

- [ ] T001 Record Feature 124 lane, scope, and no-native-capture boundary in `specs/124-content-regeneration-lifecycle/plan.md`.
- [ ] T002 Add the Feature 124 plan pointer in `AGENTS.md` and verify `.specify/feature.json` points to `specs/124-content-regeneration-lifecycle`.
- [ ] T003 [P] Add metadata-only evidence rules and release stop conditions to `specs/124-content-regeneration-lifecycle/quickstart.md`.
- [ ] T004 [P] Add migration/rollback assumptions to `specs/124-content-regeneration-lifecycle/research.md`.
- [ ] T005 Run prerequisite and placeholder checks from `specs/124-content-regeneration-lifecycle/quickstart.md`.

## Phase 2: Foundational lineage and fences

**Purpose**: These tasks block every user story. They introduce no silent
replacement and preserve compatibility with legacy rows during migration.

- [ ] T006 [P] Add failing schema contract tests for revision-scoped workflow/job/result uniqueness in `apps/server/tests/contract/test_processing_lineage_contract.py`.
- [ ] T007 [P] Add failing RLS table/column coverage checks for new lineage and dispatch entities in `apps/server/tests/contract/test_rls_validation.py`.
- [ ] T008 Add the expand migration for processing lineage, source/result fingerprints, deletion epochs and dispatch intents in `apps/server/src/twobrain_rec_server/db/migrations/versions/00xx_content_regeneration_lifecycle.py`.
- [ ] T009 Update model identities and relationships for media revisions, processing runs/jobs/results and dispatch intents in `apps/server/src/twobrain_rec_server/db/models/ingest.py` and `apps/server/src/twobrain_rec_server/db/models/processing.py`.
- [ ] T010 Add the candidate/current/deletion retention fields and controlled generation-call policy in `apps/server/src/twobrain_rec_server/db/models/outcomes.py` and `apps/server/src/twobrain_rec_server/db/models/deletion.py`.
- [ ] T011 Update the RLS validation inventory and production revision gate in `apps/server/src/twobrain_rec_server/db/rls_validation.py`.
- [ ] T012 [P] Add domain enums and safe reason codes for dispatch, candidate expiry, stale source and deletion fencing in `apps/server/src/twobrain_rec_server/domain/statuses.py` and `apps/server/src/twobrain_rec_server/processing/reasons.py`.
- [ ] T013 Implement source/deletion fence helpers with metadata-only audit events in `apps/server/src/twobrain_rec_server/processing/fences.py`.
- [ ] T014 Add migration backfill/reconciliation command behavior for legacy meeting-wide rows in `apps/server/src/twobrain_rec_server/processing/store.py`.
- [ ] T015 Add unit tests for fence monotonicity, legacy backfill and workspace isolation in `apps/server/tests/unit/test_processing_fences.py`.
- [ ] T016 Run migration, RLS and focused model tests; record evidence in `specs/124-content-regeneration-lifecycle/quickstart.md`.

## Phase 3: User Story 1 - First trustworthy result (P1)

**Independent test**: A terminal source produces one idempotent baseline and
never mutates a previous result after refresh, duplicate request or worker
restart.

- [ ] T017 [P] [US1] Add failing tests for immutable import, same-hash dedupe and changed-hash new result in `apps/server/tests/unit/test_processing_store.py`.
- [ ] T018 [P] [US1] Add integration coverage for duplicate baseline requests and provider retry classification in `apps/server/tests/integration/test_processing_baseline.py`.
- [ ] T019 [US1] Remove in-place segment/result rewrite and persist immutable result identities in `apps/server/src/twobrain_rec_server/processing/store.py`.
- [ ] T020 [US1] Make processing source selection and aggregate status revision-scoped in `apps/server/src/twobrain_rec_server/processing/store.py` and `apps/server/src/twobrain_rec_server/cabinet/queries.py`.
- [ ] T021 [US1] Add normalized source/result fingerprint validation before and after provider import in `apps/server/src/twobrain_rec_server/processing/submit.py`.
- [ ] T022 [US1] Implement one baseline candidate key and bounded automatic retry policy in `apps/server/src/twobrain_rec_server/outcomes/service.py` and `apps/server/src/twobrain_rec_server/outcomes/store.py`.
- [ ] T023 [US1] Prevent baseline generation when transcript/input/deletion/policy gates fail in `apps/server/src/twobrain_rec_server/outcomes/service.py`.
- [ ] T024 [US1] Add worker restart and duplicate dispatch integration tests in `apps/server/tests/integration/test_processing_workflow_recovery.py`.
- [ ] T025 [US1] Validate User Story 1 with the A/B scenarios in `specs/124-content-regeneration-lifecycle/quickstart.md`.

## Phase 4: User Story 2 - Manual candidate, preview and accept (P1)

**Independent test**: Owner can choose a format, review a candidate, keep the
current result or accept atomically; shared viewers never see the candidate.

- [ ] T026 [P] [US2] Add failing API/schema tests for candidate provenance and owner-only preview in `apps/server/tests/contract/test_cabinet_candidate_preview_contract.py`.
- [ ] T027 [P] [US2] Add failing accept/reject/supersede tests in `apps/server/tests/unit/test_outcomes_service.py`.
- [ ] T028 [US2] Make candidate creation pin source/result/template/generator/config and explicit request intent in `apps/server/src/twobrain_rec_server/outcomes/service.py` and `apps/server/src/twobrain_rec_server/outcomes/store.py`.
- [ ] T029 [US2] Add owner-only candidate preview projection and safe provenance fields in `apps/server/src/twobrain_rec_server/api/cabinet.py` and `apps/server/src/twobrain_rec_server/api/schemas.py`.
- [ ] T030 [US2] Enforce authoritative current pointer selection for detail, export, share and public projections in `apps/server/src/twobrain_rec_server/cabinet/queries.py`, `apps/server/src/twobrain_rec_server/cabinet/exports.py`, and `apps/server/src/twobrain_rec_server/api/cabinet.py`.
- [ ] T031 [US2] Implement optimistic source/current/deletion fence and atomic accept/supersede in `apps/server/src/twobrain_rec_server/outcomes/ai_service.py` and `apps/server/src/twobrain_rec_server/outcomes/service.py`.
- [ ] T032 [US2] Keep reject/dismiss/failed candidates from mutating current and retain safe lineage in `apps/server/src/twobrain_rec_server/outcomes/store.py`.
- [ ] T033 [US2] Add shared-viewer and export-current-only integration tests in `apps/server/tests/integration/test_cabinet_summary_candidates.py` and `apps/server/tests/integration/test_cabinet_exports.py`.
- [ ] T034 [US2] Validate owner preview/accept scenarios in `specs/124-content-regeneration-lifecycle/quickstart.md`.

## Phase 5: User Story 3 - Concurrency and stale candidate safety (P1)

**Independent test**: Concurrent requests, changed source and late callbacks
produce deterministic dedupe/conflict behavior with no stale mutation.

- [ ] T035 [P] [US3] Add concurrent candidate/accept tests with two sessions in `apps/server/tests/integration/test_outcome_concurrency.py`.
- [ ] T036 [P] [US3] Add late callback and stale aggregate tests in `apps/server/tests/integration/test_processing_stale_callbacks.py`.
- [ ] T037 [US3] Replace meeting-wide fallback lookup with revision-scoped locked lookup in `apps/server/src/twobrain_rec_server/processing/store.py`.
- [ ] T038 [US3] Add database-level active-run/job/candidate uniqueness and conflict translation in `apps/server/src/twobrain_rec_server/db/models/processing.py`, `apps/server/src/twobrain_rec_server/db/models/outcomes.py`, and `apps/server/src/twobrain_rec_server/outcomes/service.py`.
- [ ] T039 [US3] Recheck source result hash after provider egress and before candidate persistence in `apps/server/src/twobrain_rec_server/outcomes/ai_service.py`.
- [ ] T040 [US3] Fence old workflow callbacks from meeting aggregate/current result updates in `apps/server/src/twobrain_rec_server/workflows/worker.py` and `apps/server/src/twobrain_rec_server/processing/submit.py`.
- [ ] T041 [US3] Add deterministic 409/API problem copy and safe no-mutation tests in `apps/server/tests/contract/test_cabinet_candidate_preview_contract.py`.

## Phase 6: User Story 4 - New source and reprocess versions (P1)

**Independent test**: New media revision creates independent processing and
outcome lineage; old accepted/current content remains until explicit accept.

- [ ] T042 [P] [US4] Add media revision/reprocess integration fixtures in `apps/server/tests/integration/test_media_revision_reprocess.py`.
- [ ] T043 [P] [US4] Add result lineage/export snapshot tests in `apps/server/tests/integration/test_processing_result_lineage.py`.
- [ ] T044 [US4] Implement revision-scoped workflow/job creation without legacy fallback in `apps/server/src/twobrain_rec_server/processing/store.py`.
- [ ] T045 [US4] Update processing workflow payloads and external job callbacks with revision/result fences in `apps/server/src/twobrain_rec_server/workflows/processing_workflow.py` and `apps/server/src/twobrain_rec_server/workflows/worker.py`.
- [ ] T046 [US4] Create a new candidate for eligible new source results without changing current in `apps/server/src/twobrain_rec_server/outcomes/service.py`.
- [ ] T047 [US4] Ensure list/detail/export query only the selected current pointer while exposing safe new-variant state to owner in `apps/server/src/twobrain_rec_server/cabinet/queries.py` and `apps/server/src/twobrain_rec_server/cabinet/rendering.py`.
- [ ] T048 [US4] Add explicit reprocess request authorization and idempotency handling in `apps/server/src/twobrain_rec_server/api/processing.py` and `apps/server/src/twobrain_rec_server/api/cabinet.py`.
- [ ] T049 [US4] Validate the source/reprocess scenarios in `specs/124-content-regeneration-lifecycle/quickstart.md`.

## Phase 7: User Story 5 - Template and generator provenance (P1)

**Independent test**: Template edits and generator changes create new lineage
without rewriting historical accepted outputs.

- [ ] T050 [P] [US5] Add immutable template version tests in `apps/server/tests/unit/test_summary_templates.py`.
- [ ] T051 [P] [US5] Add provenance/export fixture tests in `apps/server/tests/integration/test_outcome_provenance.py`.
- [ ] T052 [US5] Enforce immutable personal/built-in template version creation in `apps/server/src/twobrain_rec_server/api/cabinet.py` and `apps/server/src/twobrain_rec_server/db/models/outcomes.py`.
- [ ] T053 [US5] Store safe generator/config/prompt/model fingerprints without secrets in `apps/server/src/twobrain_rec_server/outcomes/ai_service.py` and `apps/server/src/twobrain_rec_server/outcomes/store.py`.
- [ ] T054 [US5] Make historical rendering resolve pinned template/provenance and exclude archived versions only from new requests in `apps/server/src/twobrain_rec_server/cabinet/rendering.py` and `apps/server/src/twobrain_rec_server/outcomes/service.py`.
- [ ] T055 [US5] Validate provenance and template scenarios in `specs/124-content-regeneration-lifecycle/quickstart.md`.

## Phase 8: User Story 6 - Deletion, retention and trust boundaries (P1)

**Independent test**: Deletion wins every processing/generation/accept race and
controlled content does not reappear or remain misclassified.

- [ ] T056 [P] [US6] Add delete-vs-import/generation/accept race tests in `apps/server/tests/integration/test_deletion_generation_races.py`.
- [ ] T057 [P] [US6] Add generation-call retained-observability classification tests (including the prohibition on metadata-only mislabeling) in `apps/server/tests/unit/test_deletion_service.py`.
- [ ] T058 [P] [US6] Add object purge journal/reconciliation tests in `apps/server/tests/integration/test_deletion_storage_reconciliation.py`.
- [ ] T059 [US6] Add deletion epoch checks before/after processing and generation egress in `apps/server/src/twobrain_rec_server/processing/fences.py`, `apps/server/src/twobrain_rec_server/processing/submit.py`, and `apps/server/src/twobrain_rec_server/outcomes/ai_service.py`.
- [ ] T060 [US6] Preserve completed GenerationCall/Langfuse/Temporal content under the approved observability retention policy, purge only GRAF-controlled meeting copies, and update artifact/report states in `apps/server/src/twobrain_rec_server/deletion/service.py` and `apps/server/src/twobrain_rec_server/db/models/outcomes.py`.
- [ ] T061 [US6] Add durable per-object deletion journal and retry reconciliation in `apps/server/src/twobrain_rec_server/deletion/service.py` and `apps/server/src/twobrain_rec_server/db/models/deletion.py`.
- [ ] T062 [US6] Cancel/block active processing and candidate dispatch on deletion/retention transitions in `apps/server/src/twobrain_rec_server/deletion/service.py` and `apps/server/src/twobrain_rec_server/ingest/processing_dispatch.py`.
- [ ] T063 [US6] Align deletion report copy with controlled purge, retained plaintext observability, metadata-only audit, and external retention boundaries in `apps/server/src/twobrain_rec_server/cabinet/deletion_rendering.py` and `apps/server/src/twobrain_rec_server/deletion/service.py`.
- [ ] T064 [US6] Validate deletion/retention scenarios in `specs/124-content-regeneration-lifecycle/quickstart.md`.

## Phase 9: User Story 7 - Durable recovery and cabinet UX (P2)

**Independent test**: UI communicates named candidate state, previews safely,
pauses/backoffs polling and offers recovery without cancelling durable work.

- [ ] T065 [US7] Add static/runtime harness tests for candidate copy, preview, conflict refresh and hidden-tab polling in `apps/server/tests/contract/test_cabinet_candidate_preview_contract.py` and `apps/server/tests/contract/test_cabinet_static_assets_contract.py`.
- [ ] T066 [P] [US7] Add dispatch outage/reconciler tests in `apps/server/tests/integration/test_generation_dispatch_reconciliation.py`.
- [ ] T067 [US7] Implement durable candidate dispatch intent and reconciler in `apps/server/src/twobrain_rec_server/outcomes/service.py`, `apps/server/src/twobrain_rec_server/workflows/worker.py`, and `apps/server/src/twobrain_rec_server/ingest/processing_dispatch.py`.
- [ ] T068 [US7] Add candidate preview and named provenance to owner detail rendering in `apps/server/src/twobrain_rec_server/cabinet/rendering.py` and `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_detail_content.html`.
- [ ] T069 [US7] Add format-specific status, explicit `Обновить` conflict action and `Повторить` recovery in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`.
- [ ] T070 [US7] Bound/back off candidate polling, pause hidden tabs and prune safe session state in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`.
- [ ] T071 [US7] Update candidate styles, focus, reduced-motion and high-contrast states in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`.
- [ ] T072 [US7] Ensure browser/embedded/shared owner parity in `apps/server/src/twobrain_rec_server/cabinet/web_routes/browser.py`, `apps/server/src/twobrain_rec_server/cabinet/web_routes/desktop.py`, and `apps/server/src/twobrain_rec_server/cabinet/web_routes/support.py`.
- [ ] T073 [US7] Validate candidate UX and recovery scenarios in `specs/124-content-regeneration-lifecycle/quickstart.md`.

## Phase 10: Cross-cutting validation and release readiness

- [ ] T074 Run focused unit/contract/integration suites and record exact counts in `specs/124-content-regeneration-lifecycle/quickstart.md`.
- [ ] T075 Run migration/RLS/secret/privacy evidence scans and record pass/fail in `specs/124-content-regeneration-lifecycle/quickstart.md`.
- [ ] T076 Run `infra/scripts/ci-local.sh` and fix all failures before review in `specs/124-content-regeneration-lifecycle/quickstart.md`.
- [ ] T077 Run `$ponytail-review` and simplify unnecessary code without weakening fences or evidence in `specs/124-content-regeneration-lifecycle/plan.md`.
- [ ] T078 Run complete Arc review against the merge base and fix every actionable finding in the implementation files named by the review.
- [ ] T079 Repeat focused/full validation and Arc until the exact diff is clean; append each correction loop to `specs/124-content-regeneration-lifecycle/quickstart.md`.
- [ ] T080 Prepare Russian CHANGELOG/release notes and CalVer with `./scripts/prepare-release.sh YYYY.MM.DD.N` in `CHANGELOG.md` and `docs/releases/`.
- [ ] T081 Run `infra/scripts/cd-remote.sh --dry-run --branch 124-content-regeneration-lifecycle` and record the result in `specs/124-content-regeneration-lifecycle/quickstart.md`.
- [ ] T082 After explicit approval, execute production rollout, smoke, rollback readiness and installed-app/server version verification using `infra/scripts/cd-remote.sh --execute --branch 124-content-regeneration-lifecycle`.
- [ ] T083 Close PR/issues with Russian evidence, migration impact, known limitations and exact release/deploy identifiers in `CHANGELOG.md` and the GitHub PR.

## Dependencies and execution order

```text
Setup → Foundational lineage/fences
      → US1 baseline processing
      → US2 candidate/current contract
      → US3 concurrency fences
      → US4 reprocess revisions
      → US5 provenance
      → US6 deletion/retention
      → US7 dispatch recovery + UX
      → full validation/review/release
```

US1 blocks US2; US2 and the foundational fences block US3–US6. US7 can begin
after candidate contracts and dispatch records exist. No production deploy is
allowed before T079 is clean and all release gates are evidenced.

## Parallel opportunities

- T006–T007; T012; T017–T018; T026–T027; T035–T036; T042–T043; T050–T051;
  T056–T058; T065–T066 can run in parallel when their prerequisites are met.
- Documentation/evidence tasks T003–T005, T016, T025, T034, T049, T055 and T064
  can be updated in parallel with their focused validation.

## Implementation strategy

1. MVP safety slice: foundational lineage/fences + US1 + US2 + US3. This makes
   current truth and stale-accept safety correct before adding reprocess UI.
2. Add US4/US5 lineage and provenance with migration/backfill evidence.
3. Add US6 deletion/retention and storage reconciliation before production use.
4. Add US7 preview/recovery UX after the server contract is stable.
5. Finish with full CI, Arc/ponytail loops, release prep, dry-run, explicit
   production rollout and closeout.
