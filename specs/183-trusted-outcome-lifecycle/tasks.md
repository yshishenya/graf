# Tasks: Доверенные версии итогов по типам

**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), including the downstream [receipt wire contract](contracts/receipts.md), and [quickstart.md](quickstart.md). Feature 183 intentionally contains no receipt-vector artifact; Feature 195 creates the first schema-valid conformance corpus from scratch.

**Risk lane**: high-risk AI/Postgres/deletion/egress lifecycle. Domain, migration and server contract tests precede their implementation; the executable embedded-macOS parity contract is a mandatory pre-acceptance gate after the server route stabilizes and before closeout. This file does not authorize implementation, issue sync, commit or rollout.

## Phase 1: Setup and contract freeze

- [ ] T001 Add RED source/model/API contract assertions for one current revision per meeting/type, same-workspace binding even while the slot pointer is null, orthogonal result/generation/source/catalog states, no mandatory user accept surface, no second post-transcript trigger, and a closed repository query-owner inventory that rejects every unclassified `MeetingOutcomeSet`/`meeting_outcome_sets` newest-row helper or descending-first/limit/raw-SQL fallback in `apps/server/tests/contract/test_summary_type_slot_contract.py`
- [ ] T002 [P] Add RED schema/backfill/downgrade/RLS assertions for `meeting_summary_slots`, named composite meeting/empty-slot and outcome-pointer binding, one-default-slot uniqueness, deterministic legacy normalization, `verified_complete|migrated_legacy_read_only` binding class, exact legacy-proof hash and `0076_meeting_summary_slots.py` in `apps/server/tests/contract/test_summary_type_slot_migration_contract.py`. Assert that only the locked pre-migration pointer may create a grandfathered readable legacy slot, it cannot create new egress, and Feature 183 adds no receipt/fingerprint/canonical-artifact schema or successful model-generated publication transition; those migrations and positive fixtures belong to Feature 195.
- [X] T003 [P] Add reusable two-type and same-type-revision fixtures without private content in `apps/server/tests/fixtures/summary_type_slots.py`

## Phase 2: Foundational data and service layer

- [X] T004 Add `MeetingSummarySlot`, same-workspace pointer binding, current binding class/legacy-proof and meeting-default invariants in `apps/server/src/twobrain_rec_server/db/models/outcomes.py`; add the named `UniqueConstraint("id", "workspace_id", name="uq_meetings_id_workspace_id")` to `Meeting.__table_args__` in `apps/server/src/twobrain_rec_server/db/models/meeting.py` so ORM metadata and migration-created schemas enforce the same composite parent key. Reuse existing outcome content/header fields and add no receipt model/table/reservation, canonical artifact, GenerationCall ownership or provenance-fingerprint columns in Feature 183.
- [ ] T005 Create the idempotent slot/RLS/composite-FK migration, including the same named `uq_meetings_id_workspace_id` constraint, composite slot→meeting plus slot→outcome bindings and exact domain-separated grandfathered legacy proof; backfill only the locked explicit pointer/default provenance as `migrated_legacy_read_only`, keep ambiguity metadata-only and deny new egress from it in `apps/server/src/twobrain_rec_server/db/migrations/versions/0076_meeting_summary_slots.py`. Receipt owner-row columns, complete attempt/outcome provenance, GenerationCall membership, calibration registry and positive finalization constraints are one Feature 195 migration path, not a dependency of Feature 183 closeout.
- [X] T006 Register/import the new model through existing database metadata surfaces in `apps/server/src/twobrain_rec_server/db/models/__init__.py`
- [ ] T007 Add slot lookup/create/lock, persisted meeting-default consumption and one-time legacy workspace-default marking helpers that never consult viewer presentation state; route baseline readers to slots, stop automatic model-generated writes to both slot and `Meeting.current_outcome_set_id`, and leave the old pointer read-only after cutover in `apps/server/src/twobrain_rec_server/outcomes/service.py`
- [ ] T008 Add PostgreSQL migration-created and `Base.metadata.create_all()` schema tests for the exact named meeting composite unique constraint, null-slot cross-workspace denial, partial-default uniqueness/provenance, same-workspace/type outcome-pointer binding, DB-only expected-current CAS, complete-vs-grandfathered current binding classes, legacy proof/read/no-new-egress/verified-replacement behavior and migration reruns in `apps/server/tests/integration/test_meeting_summary_slots.py`. Prove that no Feature 183 schema/trigger can finalize a model-generated receipt, mark a candidate publishable or bypass the later Feature 195 entry point.

## Phase 3: User Story 1 — Fail-closed без лишнего решения (P1)

**Goal**: saved results remain readable, user accept/reject disappears, and every model-generated candidate remains unpublished until Feature 195 completes the sole entry point.

**Independent test**: a model-generated candidate missing any downstream proof cannot move a slot or finalize dispatch; no accept command exists and an old current result remains available. The first positive model-generated publication test is Feature 195 acceptance.

- [ ] T009 [P] [US1] Add RED fail-closed tests for missing canonical artifact, receipt, GenerationCall membership, calibration state, source fence, deletion fence and publication authorization in `apps/server/tests/integration/test_meeting_outcomes_generation.py`. Every case leaves slot/DispatchIntent/current result unchanged and exposes only bounded blocked/deferred/ambiguous/no-content state. Also prove generated `my_actions`/`private_self` and malformed `MeetingIntentV1`, `AudienceContextV1`, privacy, `FocusV1` or `DetailBudgetV1` controls are rejected. Feature 183 has no positive P1–P4 receipt fixtures; those reserved fixture names belong to the schema-valid corpus created by Feature 195.
- [ ] T010 [P] [US1] Add RED server contract tests proving ordinary cabinet responses expose exact requested/default slot state, calm ready/preparing/error copy with the bounded next-action enum and no reachable accept/reject action or internal candidate content in `apps/server/tests/contract/test_summary_template_ui_contract.py`. Selector behavior, transcript-language `RU`/`Regenerate` and the inert Share header host are downstream Feature 196 acceptance, not Feature 183 implementation.
- [ ] T011 [US1] Establish exactly one internal model-publication entry point in `apps/server/src/twobrain_rec_server/outcomes/ai_service.py`, stop automatic writes to `Meeting.current_outcome_set_id`/`accepted_by_user_id` and every slot, and return stable `verified_runtime_unavailable` unless the later Feature 195-owned prerequisite contract is present. Feature 183 MUST contain no branch, test flag or synthetic token that turns this denial into successful model-generated publication.
- [ ] T012 [US1] Add one private slot-CAS primitive in `apps/server/src/twobrain_rec_server/outcomes/ai_service.py`: for Feature 183 lock the meeting deletion fence then target slot and prior current, compare exact expected-current/source/access/deletion identity, atomically move only the slot or return a typed conflict, and never finalize a receipt/DispatchIntent by itself. Exercise it only with DB-only non-model fixtures. Feature 195 must first lock Feature 194's canonical-source pointer between the meeting fence and slot, then invoke this same primitive inside the larger receipt transaction; the primitive must not acquire an earlier lock after the slot, and Feature 195 must not add another publisher or CAS implementation.
- [ ] T013 [US1] Resolve browser/embedded default summary reads through the default type slot and honest no-result states in `apps/server/src/twobrain_rec_server/cabinet/rendering.py`

## Phase 4: User Story 2 — Мгновенное переключение сохранённых типов (P1)

**Goal**: each type retains its own current revision; reading an existing type performs no inference.

**Independent test**: three stored types survive repeated read/switch requests and route reloads with unchanged outcome IDs and zero dispatch intents/model calls.

- [ ] T014 [P] [US2] Add RED compatibility tests proving existing built-in/personal `template_key` values remain opaque across a v2 snapshot and saved results remain read-only after template retirement/deletion while ensure/refresh/default selection are denied, without implementing catalog UI, in `apps/server/tests/unit/test_summary_templates.py`
- [ ] T015 [P] [US2] Add RED API tests for orthogonal result/generation/source/catalog states; current-result continuity under updating/error/retired; transcript-failed vs source-empty vs no-supported-content; blocked/deferred/ambiguous retry policy; exact `SummaryTypeCatalogEntryV1` version/name/description/group/category/quick-rank/full-rank/provenance/deviation ordering; event identity sufficient for Feature 196 to update a type cache without repainting another selection; and zero inference on a ready type while AI dependencies are unavailable. Also prove generated shared-slot `my_actions`, `private_self` and every subject-dependent control are rejected and Feature 183 exposes no positive `my_actions` endpoint/control; authenticated read-time action filtering belongs to Feature 205/196, while any generated subject-scoped outcome belongs only to Feature 208. Use `apps/server/tests/integration/test_cabinet_meeting_outcomes.py`.
- [ ] T016 [US2] Add summary-type list/read/ensure schemas with separate result presence, generation attempt, source readiness/freshness, catalog availability, exact `SummaryTypeCatalogEntryV1`, the exact public `next_action`/derived `retryable` contract and meeting/type/outcome/attempt event identity. Reject `my_actions`, `private_self` and all subject identity/mapping fields from Feature 183 read/generation/ensure controls and future Receipt V1 payloads in `apps/server/src/twobrain_rec_server/api/schemas.py`; the positive authenticated read filter belongs to Feature 205/196 and generated subject-scoped schemas to Feature 208.
- [ ] T017 [US2] Add authenticated cabinet list/read/ensure routes using slot pointers and existing dispatch idempotency. Expose no positive `my_actions` route/control in Feature 183; reject generated `my_actions`/`private_self` inputs at the route boundary and leave authorization-first trusted-participant filtering to Feature 205/196 in `apps/server/src/twobrain_rec_server/api/cabinet.py`.
- [ ] T018 [US2] Retire newest-outcome fallback from normal type reads, require explicit default resolution and land slot-first/explicit-pointer dual-read in `apps/server/src/twobrain_rec_server/cabinet/egress.py` and `apps/server/src/twobrain_rec_server/cabinet/queries.py`; the one explicit-pointer compatibility path remains until T035/T036

## Phase 5: User Story 3 — Безопасное обновление одного типа (P1)

**Goal**: refresh keeps the old same-type revision current; Feature 183 proves the isolated CAS/failure contract while Feature 195 owns the first verified model-generated replacement.

**Independent test**: DB-only non-model CAS success replaces only the target slot; every model-generated, invalid or stale case keeps it; a second type remains byte-identical.

- [ ] T019 [P] [US3] Add RED same-type refresh tests for visible old revision, DB-only CAS success, model-generated fail-closed, invalid/stale/provider failure and idempotent repeat in `apps/server/tests/unit/test_summary_candidate_revisions.py`
- [ ] T020 [P] [US3] Add RED cross-type isolation tests proving simultaneous DB-only CAS operations mutate only their own slots and model-generated attempts mutate none in `apps/server/tests/integration/test_meeting_summary_slots.py`
- [ ] T021 [US3] Make expected-current comparison and supersession slot-scoped, keep outcome revision identity immutable, and remove all remaining automatic meeting-global pointer mutations in `apps/server/src/twobrain_rec_server/outcomes/ai_service.py`
- [ ] T022 [US3] Add the refresh-one-type route; remove preview/accept/reject controls and links; and deny deprecated routes to ordinary cabinet sessions in `apps/server/src/twobrain_rec_server/api/cabinet.py`, `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js` and `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_detail_content.html`
- [ ] T023 [US3] Project current content separately from generation attempt, full source readiness/freshness and catalog availability, with transcript failure/meeting source-empty distinct from type-scoped no-supported-content and retired/unavailable, in `apps/server/src/twobrain_rec_server/cabinet/rendering.py`

## Phase 6: User Story 4 — Stale/deletion/concurrency protection (P1)

**Goal**: late or stale work cannot overwrite a newer same-type result; independent slot CAS operations do not conflict across types.

**Independent test**: media/result/speaker/source/deletion changes and same-type CAS races produce zero stale publications; one winner exists per target slot.

- [ ] T024 [P] [US4] Add RED source/media/speaker/deletion/expiry, lost-response replay, concurrent first-ensure and same-type race fixtures in `apps/server/tests/unit/test_summary_candidate_revisions.py`; the source-revision fixture uses three active saved types plus retired/unsaved controls, marks every active old-source slot stale, keeps prior revisions readable, blocks new egress and proves no cross-slot mutation or retired/unsaved generation. The positive source-pointer-versus-publication lock-order fixtures belong to Features 194/195/197 and cannot be faked by Feature 183.
- [ ] T025 [P] [US4] Add RED workflow late-completion, duplicate-dispatch and Langfuse-outage regressions proving Feature 183 never converts retained work into publication, never repeats inference merely for slot reconciliation and keeps saved reads available in `apps/server/tests/integration/test_outcome_generation_workflow.py`; also prove stale-slot event identity is sufficient for Feature 197 to create one later coalesced replacement intent per active saved available type without Feature 183 dispatching those intents itself
- [ ] T026 [US4] Rebind existing source/deletion/access/expiry checks to the fail-closed entry point and private target-slot CAS primitive in `apps/server/src/twobrain_rec_server/outcomes/ai_service.py`
- [ ] T027 [US4] Preserve target `template_key`, slot and expected-current identity when submitting the existing outcome workflow without changing Temporal retry/replay policy in `apps/server/src/twobrain_rec_server/workflows/temporal_client.py`
- [ ] T028 [US4] Keep bounded stable reason codes and remove transcript/provider-body leakage from lifecycle API errors in `apps/server/src/twobrain_rec_server/api/cabinet.py`

## Phase 7: User Story 5 — Safe default-type egress compatibility (P2)

**Goal**: existing outward summary paths pin the documented default type and exact current revision and never follow later refresh silently.

**Independent test**: with several saved types, existing share/export returns the default slot's exact pinned revision; subsequent refresh does not change the existing artifact; non-current/internal/stale/default-missing states are denied without another-type fallback.

- [ ] T029 [P] [US5] Add RED share/public-link/export tests for persisted meeting-default, one-time legacy workspace resolution and marker write, viewer-personal preference exclusion, retired/non-current/source-stale/default-missing denial, transactional share-versus-refresh linearization and post-refresh stability in `apps/server/tests/integration/test_transcript_export_egress.py`
- [ ] T030 [P] [US5] Add RED shared-meeting projection tests for exact outcome-set pinning in `apps/server/tests/integration/test_recording_share_public_link.py`
- [ ] T031 [US5] Resolve and validate the exact default slot/revision in existing summary export paths in `apps/server/src/twobrain_rec_server/cabinet/exports.py`
- [ ] T032 [US5] Remove newest-row fallback and land slot-first/explicit-pointer dual-read for share/public summary projections in `apps/server/src/twobrain_rec_server/cabinet/egress.py` and `apps/server/src/twobrain_rec_server/cabinet/web_routes/browser.py`; the one explicit-pointer compatibility path remains until T035/T036
- [ ] T033 [US5] Resolve/validate the default slot and pin `template_key`/`outcome_set_id` in the same transaction that writes/activates `MeetingShareGrant.metadata_json` or `ExportPackage.manifest_json` in `apps/server/src/twobrain_rec_server/cabinet/access.py` and `apps/server/src/twobrain_rec_server/cabinet/egress.py`, then validate/read that exact pair through `apps/server/src/twobrain_rec_server/api/schemas.py` and `apps/server/src/twobrain_rec_server/api/cabinet.py` without adding arbitrary-type selection

## Phase 8: User Story 6 — Safe legacy archive migration (P2)

**Goal**: uniquely proven existing current results become slots without changing content; ambiguous legacy rows never become current through runtime guessing.

**Independent test**: all specified legacy fixtures either preserve exact current content or produce metadata-only ambiguity; migration and reconciliation reruns are idempotent.

- [ ] T034 [P] [US6] Add exhaustive integration fixtures for legacy-pointer, pointed-keyless, missing-target, cross-scope, ambiguous and deleted-meeting migration states in `apps/server/tests/integration/test_meeting_outcomes_migrations.py`
- [ ] T035 [US6] Add the mandatory post-backfill cutover verifier, metadata-only ambiguity receipt and fail-closed downgrade when slots cannot be represented by the legacy pointer in `apps/server/src/twobrain_rec_server/db/migrations/versions/0076_meeting_summary_slots.py`; strict slot-only code MUST NOT be implemented before this verifier exists and passes its fixtures
- [ ] T036 [US6] After T035 succeeds, remove the final explicit-pointer compatibility path from every runtime owner under `apps/server/src/twobrain_rec_server`; migrate the operational reconciliation in `apps/server/scripts/reconcile_initial_outcomes.py` to the T037 slot command or retire it, and replace the candidate-accept flow in `apps/server/scripts/prove_meeting_outcome_live.py` with slot-backed ensure/read proof or retire it behind a complete successor. Classify every repository-wide `current_outcome_set_id`, accept-route and newest-outcome match across `apps/server` in `specs/183-trusted-outcome-lifecycle/validation/privacy.md` against the closed allowlist of field declaration, historical migrations, deletion compatibility and explicitly named legacy fixtures; zero unallowlisted runtime/operational-script reads or writes are permitted.
- [ ] T037 [US6] Add an operator-only metadata reconciliation command with no private content in `apps/server/src/twobrain_rec_server/cli/summary_slots.py`

## Phase 9: Deletion, security and closeout

- [ ] T038 [P] Add slot purge/accounting, delete-during-CAS and model-publication-fail-closed regressions in `apps/server/tests/integration/test_meeting_outcomes_deletion.py`
- [ ] T039 Register only GRAF-controlled slot purge and deletion fences while preserving the existing retained-GenerationCall distinction without changing external retention policy in `apps/server/src/twobrain_rec_server/deletion/service.py`
- [ ] T040 [P] Add real-PostgreSQL cross-workspace/meeting/type RLS tests, including an empty/null-current slot whose `workspace_id` mismatches its meeting, in `apps/server/tests/integration/test_rls_postgres_migrations.py`
- [ ] T041 Run the focused quickstart matrix and record metadata-only evidence in `specs/183-trusted-outcome-lifecycle/validation/focused.md`
- [ ] T042 Run all existing outcomes/cabinet/share/export/deletion PostgreSQL suites and record counts in `specs/183-trusted-outcome-lifecycle/validation/regression.md`
- [ ] T043 Run the exact whole-`apps/server` and feature-spec scans from `specs/183-trusted-outcome-lifecycle/quickstart.md` for private content, local evidence paths/screenshots, user-provided record titles/participant names/transcript quotes, meeting-global pointer reads/writers, accepted-by-user publication, candidate-accept routes and newest-outcome fallback; treat the broad `MeetingOutcomeSet|meeting_outcome_sets` file/symbol inventory as authoritative, inspect and follow every query owner, imported alias, raw SQL statement and helper caller (including `created_at`/`generated_at` descending plus first/limit/max/Python-sort shapes), prove the T001 contract rejects a newly introduced unclassified query owner, classify source/scripts/tests/migrations against the closed allowlist, require zero operational-script matches after T036, use only opaque IDs for outside-git Krisp evidence, and record only aggregate/path-class results in `specs/183-trusted-outcome-lifecycle/validation/privacy.md`
- [ ] T044 [P] Extend the executable macOS shared test target with an embedded-cabinet route contract proving the same requested/default slot-backed result, honest no-result state and absence of accept/reject/internal-candidate surfaces as the browser route in `apps/macos/Shared/Tests/DesktopMeetingShellWebViewBoundaryTests.swift`. Feature 196 separately owns executable selector, Refresh, transcript-language and Share-host parity.
- [ ] T045 Run `infra/scripts/ci-local.sh --fast` and record the exact outcome in `specs/183-trusted-outcome-lifecycle/validation/closeout.md`
- [ ] T046 Update behavior, migration, UX-contract and compatibility notes under `[Unreleased]` in `CHANGELOG.md`
- [ ] T047 Run `@ponytail-review` over `apps/server/src/twobrain_rec_server/db/models/outcomes.py`, `apps/server/src/twobrain_rec_server/db/models/meeting.py`, `apps/server/src/twobrain_rec_server/outcomes/`, `apps/server/src/twobrain_rec_server/cabinet/`, `apps/server/src/twobrain_rec_server/api/`, `apps/server/tests/` and `apps/macos/Shared/Tests/DesktopMeetingShellWebViewBoundaryTests.swift`; remove any duplicated ledger, copied content or avoidable abstraction and record the metadata-only receipt in `specs/183-trusted-outcome-lifecycle/validation/closeout.md`
- [ ] T048 Reconcile SC-001–SC-012, every completed task and downstream blockers in `specs/183-trusted-outcome-lifecycle/validation/closeout.md`

## Dependencies

- T001–T008 are foundational and block every user-story implementation.
- US1 establishes only the fail-closed entry point and blocks US3/US4 until the
  private slot-CAS primitive exists. It has no successful receipt fixture.
- Positive receipt-backed publication, P1–P4/full-schema vectors and canonical/
  call/calibration race proof are Feature 195 acceptance after Feature 194 defines
  the canonical artifact; no Feature 183 task may add a synthetic bypass,
  legacy same-attempt or single-receipt producer.
- US2 establishes independent slots and can proceed beside US1 after T008, but T018 intentionally retains the one explicit-pointer compatibility path.
- US3 depends on US1+US2.
- US4 depends on US3 publication semantics.
- US5 depends on US2 current-slot reads and US3 exact revisions; T032 also intentionally retains that one compatibility path.
- US6 can proceed after the data model; T035 is the mandatory verifier and T036 is the only task that may activate strict slot-only readers after US2/US5 paths are ready.
- Closeout depends on all selected stories and their evidence.

## Parallel opportunities

- T001–T003 can be prepared in parallel.
- T009/T010, T014/T015, T019/T020, T024/T025, T029/T030 and T038/T040 touch disjoint test surfaces.
- US5 and migration fixture work for US6 can proceed in parallel after the slot model stabilizes.
- T041–T044 can run in parallel only after implementation is complete; T045 follows focused failures being resolved.

## MVP implementation strategy

1. Deliver data/slot invariants and the fail-closed publication entry point (Foundation + US1).
2. Add saved-type reads and the isolated same-type CAS contract (US2+US3).
3. Close stale/concurrency and exact egress (US4+US5).
4. Cut over legacy archive safely (US6).
5. Complete deletion/security and repository validation.

Feature 183 remains non-releasable alone: user-facing rollout waits for the dependency gates in [program-roadmap.md](program-roadmap.md).

## Requirement coverage

| Requirement/story | Tasks | Primary assertion/test surface |
|---|---|---|
| US1 | T009–T013, T044 | `test_meeting_outcomes_generation.py`, browser and executable embedded-macOS UI contracts |
| US2 | T014–T018, T044 | template compatibility and browser/embedded cabinet read/ensure tests |
| US3 | T019–T023 | candidate-revision and slot-isolation tests |
| US4 | T024–T028 | source/deletion/race/workflow tests |
| US5 | T029–T033 | default-only egress/public-link tests |
| US6 | T034–T037 | migration fixtures, cutover verifier and reconciliation command |
| Constitution/release closeout | T045–T046, T048 | required CI evidence, `[Unreleased]` behavior/migration/UX/compatibility notes and final SC/task/blocker reconciliation |
| FR-001 | T001, T002, T004–T006, T008, T020 | one registered slot/current pointer per meeting/type with same-workspace meeting binding |
| FR-002 | T003, T008, T020, T021 | cross-type byte/pointer isolation |
| FR-003 | T015, T017, T018 | ready read with zero dispatch/model call |
| FR-004 | T015, T017, T024, T025 | one equivalent active ensure and honest selected-type state |
| FR-005 | T009, T011, T024–T026 | every Feature 183 model-generated path fails closed; full automatic gates belong to Feature 195 |
| FR-006 | T010, T011, T022 | no reachable ordinary accept/reject flow |
| FR-007 | T019, T021 | immutable replacement plus atomic slot CAS |
| FR-008 | T019, T023, T024, T026 | last-known-good under invalid/failure/stale/delete/timeout/conflict |
| FR-009 | T004, T021 | immutable supersession lineage without user history UI |
| FR-010 | T019, T024, T025, T027 | same-key replay and no duplicate publication/inference |
| FR-011 | T020, T021, T024, T026 | same-type expected-current race has one winner |
| FR-012 | T020, T021, T026 | different types publish independently |
| FR-013 | T009, T012, T028 | raw/invalid/attempt state cannot become current |
| FR-014 | T001, T009, T011, T012, T021, T043 | one `ai_service.py` publisher owner, private CAS primitive, no positive model path or duplicate writer; full provenance belongs to Feature 195 |
| FR-015 | T015, T016, T020, T023 | no meeting-global selected-type mutation |
| FR-016 | T029–T033 | documented default type and exact revision only |
| FR-017 | T009, T010, T015, T016, T023 | meeting source-empty vs type-scoped no-supported-content and bounded recovery states |
| FR-018 | T017, T024, T026, T028, T038–T040 | auth/RLS/CSRF/audit/deletion fences |
| FR-019 | T002, T005, T034–T037 | deterministic legacy preservation or metadata-only ambiguity |
| FR-020 | T014, T033 | snapshot readability after template edit/delete |
| FR-021 | T023–T026, T029–T033 | stale readability, publication denial and new-egress block |
| FR-022 | T001, T002, T004, T005, T007, T008, T029–T033 | persisted meeting-default handoff, one-time legacy workspace resolution and no viewer-personal fallback |
| FR-023 | T014–T017, T029 | retired result readability with generation/default/egress denial |
| FR-024 | T001, T009, T015, T016, T023, T028 | orthogonal lifecycle vocabulary plus exact versioned catalog display/order contract |
| FR-025 | T029–T033 | one egress transaction linearization point |
| FR-026 | T009, T015–T017 | generated subject-dependent formats rejected and no positive Feature 183 `my_actions` path; authenticated read filtering deferred to Feature 205/196 and generated private outcomes to Feature 208 |
| NFR-001 | T008, T019–T021, T024, T041 | no empty interval, dual current or partial slot update |
| NFR-002 | T015, T025, T042 | saved reads survive LiteLLM/Langfuse/Temporal outage |
| NFR-003 | T028, T037, T043 | metadata-only ordinary errors/reconciliation/evidence |
| NFR-004 | T004, T007, T011, T047 | existing outcome/attempt/dispatch/ledger reuse |
| NFR-005 | T002, T004–T006, T047 | only the pointer table and required composite keys; no copied content, receipt schema or parallel ledger in Feature 183 |
| SC-001 | T015, T041 | repeated three-type switch creates zero calls |
| SC-002 | T019, T020, T024, T041 | only the target slot changes in the full failure/race matrix |
| SC-003 | T019, T023, T041 | previous current remains visible in every failed update |
| SC-004 | T009, T011, T024–T026, T041 | zero model-generated publication in Feature 183; positive full-gate proof assigned to Feature 195 |
| SC-005 | T019, T024, T025, T041 | completed replay creates zero extra publish/inference |
| SC-006 | T002, T008, T040, T041 | zero broken/cross-scope/type pointers in PostgreSQL |
| SC-007 | T002, T005, T034–T037, T041 | byte-identical proven legacy rows; ambiguous rows only reported |
| SC-008 | T015, T025, T042 | saved result readable during every AI dependency outage |
| SC-009 | T023–T026, T029–T033, T041 | stale remains labelled/readable; late candidate and new egress denied |
| SC-010 | T009, T014–T016, T028, T041 | exact independent states and safe next-action policy |
| SC-011 | T029, T030, T033, T041 | share/export-versus-refresh pins exactly one transactional revision |
| SC-012 | T009, T015–T017, T041 | shared generated personal formats always reject; Feature 183 exposes no positive `my_actions` route/control; read-time filter proof is Feature 205/196 and any generated subject-scoped proof is Feature 208 |
