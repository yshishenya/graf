# Tasks: Canonical Transcript And Summary Export

**Input**: [spec.md](./spec.md), [plan.md](./plan.md),
[research.md](./research.md), [data-model.md](./data-model.md),
[contracts/](./contracts/), and [quickstart.md](./quickstart.md)

**Risk / validation lane**: `high-risk-feature`. Tests are required because the
slice changes meeting-content egress, revision truth, policy, audit, deletion,
shared transcript semantics, and accessibility.

**Source of truth**: This file governs implementation. Mark a task `[X]` only
after its stated behavior and focused validation pass. GitHub issues mirror
these tasks after clean analyze; they do not replace this file.

## Phase 1: Setup

- [X] T001 Add the bounded `openpyxl` XLSX writer dependency and refresh the lock/constraints output in `apps/server/pyproject.toml`, `apps/server/uv.lock`, and `apps/server/constraints.txt`
- [X] T002 Add shared synthetic export fixture builders for gap/revision/policy matrices in `apps/server/tests/fixtures/cabinet_exports.py`
- [X] T003 Register the fixture module without production-content leakage in `apps/server/tests/conftest.py`

---

## Phase 2: Foundational Snapshot And Egress (Blocking)

**Goal**: One revision-pinned provider-neutral snapshot and one reused
authorization/audit boundary exist before any format or UI story is implemented.

- [X] T004 Add failing canonical contract cases for stable speaker key, attribution state, selected result, source ids, unknown singleton, overlap, and raw compatibility in `apps/server/tests/contract/test_transcript_turn_contract.py` (FR-001–FR-007, FR-064)
- [X] T005 Add failing 0.9/1.0/1.1/3/51/138 gap, A→B→A, source, overlap, invalid, empty, and unknown derivation cases in `apps/server/tests/unit/test_cabinet_view_models.py` (FR-003–FR-004, SC-001)
- [X] T006 Harden the existing server canonical-turn schema without changing raw segment consumers in `apps/server/src/twobrain_rec_server/api/schemas.py` (FR-002–FR-005, FR-064)
- [X] T007 Harden the shared feature 113 derivation and remove confirmed-identity inference from missing speaker evidence in `apps/server/src/twobrain_rec_server/cabinet/view_models.py` (FR-003–FR-004, FR-016)
- [X] T008 Add frozen export selection, snapshot, raw row, canonical turn, summary projection, filename, and serializer-dispatch types in `apps/server/src/twobrain_rec_server/cabinet/exports.py` (FR-001–FR-007, FR-050)
- [X] T009 Add failing snapshot tests for current selected result/outcome, full raw fidelity, deterministic identity, provider-neutral input, and no regeneration/provider call in `apps/server/tests/unit/test_transcript_exports.py` (FR-001–FR-007, FR-020, SC-010–SC-011)
- [X] T010 Build the snapshot from existing raw transcript/diarization rows, meeting speaker names, and stored outcome rows in `apps/server/src/twobrain_rec_server/cabinet/exports.py` (FR-001–FR-007, FR-020–FR-025)
- [X] T011 Extend export request/capability response allowlists and safe revision/readiness schemas in `apps/server/src/twobrain_rec_server/api/schemas.py` (FR-031–FR-037, FR-060–FR-066)
- [X] T012 Add failing metadata-only audit sanitizer cases for scope, format, pinned revisions, renderer version, outcome, and byte length in `apps/server/tests/unit/test_artifact_egress_audit.py` (FR-055, FR-062–FR-063)
- [X] T013 Reuse and narrowly extend feature 017 policy/audit/deletion helpers for on-demand canonical content export without a controlled persisted copy in `apps/server/src/twobrain_rec_server/cabinet/egress.py` (FR-051–FR-052, FR-060–FR-063)

**Checkpoint**: One snapshot feeds all later serializers; unknown rows are
present but non-mergeable; no export bytes can bypass current policy/audit.

---

## Phase 3: User Story 1 — Readable Transcript (Priority: P1)

**Goal**: Authorized reviewers download deterministic human-readable TXT/MD
from canonical turns, with readable grouping and no fabricated silence.

**Independent test**: Export the gap/A→B→A/unknown/renamed-speaker fixture as
TXT and MD and compare child timing/text/order to the snapshot.

- [X] T014 [P] [US1] Add failing TXT/MD serializer cases for Russian text, child timestamps, display grouping, long gaps, unknown labels, Markdown/HTML escaping, and >1-hour timing in `apps/server/tests/unit/test_transcript_exports.py` (FR-010–FR-011, FR-016–FR-017, SC-005)
- [X] T015 [US1] Implement shared human display grouping and timestamp/escaping helpers in `apps/server/src/twobrain_rec_server/cabinet/exports.py` (FR-004, FR-016–FR-017)
- [X] T016 [US1] Implement deterministic UTF-8 TXT and CommonMark-safe MD transcript serializers in `apps/server/src/twobrain_rec_server/cabinet/exports.py` (FR-010–FR-011, SC-002)
- [X] T017 [P] [US1] Add failing additive canonical file-route and legacy raw/plain compatibility cases in `apps/server/tests/contract/test_transcript_export_contract.py` (FR-060, FR-064–FR-066)
- [X] T018 [US1] Add metadata-only capability and canonical file routes while preserving existing download/package routes in `apps/server/src/twobrain_rec_server/api/cabinet.py` (FR-030–FR-037, FR-064–FR-066)
- [X] T019 [US1] Add end-to-end authorized TXT/MD response, filename, MIME, byte length, audit, and no-pause checks in `apps/server/tests/integration/test_transcript_export_egress.py` (SC-002, SC-004, SC-009)

**Checkpoint**: US1 is independently usable without CSV/XLSX/JSON/SRT or
summary export.

---

## Phase 4: User Story 2 — Structured Transcript Data (Priority: P1)

**Goal**: CSV, XLSX, and JSON preserve one canonical turn per row/object plus
stable revision/provenance and safe raw fidelity.

**Independent test**: Parse all three outputs and compare order, text, timing,
speaker state, source role/ids, revisions, and provider-neutral semantics to one
snapshot.

- [X] T020 [P] [US2] Add failing CSV cases for stable columns, CRLF/BOM/quoting, Russian newlines, source ids, and inert formula-prefix cells in `apps/server/tests/unit/test_transcript_exports.py` (FR-012, FR-055)
- [X] T021 [P] [US2] Add failing JSON cases for versioned deterministic envelope, raw fidelity, canonical turns, revisions, provenance, invalid/source-only rows, and secret-field exclusion in `apps/server/tests/unit/test_transcript_exports.py` (FR-014, SC-001/SC-003/SC-004)
- [X] T022 [P] [US2] Add failing XLSX parse cases for exact sheet/order/columns, typed literal cells, wrap/filter/freeze behavior, no formulas/macros/links, and semantic determinism in `apps/server/tests/unit/test_transcript_exports.py` (FR-013, FR-055)
- [X] T023 [US2] Implement stdlib CSV serialization with stable columns and formula-neutralized untrusted text in `apps/server/src/twobrain_rec_server/cabinet/exports.py` (FR-012)
- [X] T024 [US2] Implement sorted-key versioned provider-neutral JSON serialization with complete selected-result raw fidelity in `apps/server/src/twobrain_rec_server/cabinet/exports.py` (FR-014)
- [X] T025 [US2] Implement write-only four-sheet XLSX serialization using literal cells and bounded styles in `apps/server/src/twobrain_rec_server/cabinet/exports.py` (FR-013)
- [X] T026 [US2] Add cross-format semantic comparison and provider-adapter equivalence coverage in `apps/server/tests/unit/test_transcript_exports.py` (SC-003/SC-004/SC-011)
- [X] T027 [US2] Add authorized CSV/XLSX/JSON download and unsupported format/scope integration cases in `apps/server/tests/integration/test_transcript_export_egress.py` (FR-060–FR-066)

**Checkpoint**: US2 yields machine-safe migration/analysis formats without
using UI groups or provider fields.

---

## Phase 5: User Story 3 — SRT Captions (Priority: P1)

**Goal**: One valid canonical turn becomes one accurately timed SRT cue; silence
is empty time and overlap is not falsified.

**Independent test**: Parse SRT from speaker-change/overlap/long-gap/unknown/
greater-than-one-hour fixtures and compare cues to eligible turns.

- [X] T028 [P] [US3] Add failing SRT parser/serializer cases for counter syntax, millisecond timing, speaker option, overlap, invalid-row omission, unknown label, >1-hour time, and no pause cue in `apps/server/tests/unit/test_transcript_exports.py` (FR-015–FR-018)
- [X] T029 [US3] Implement literal-text one-turn-per-cue SRT serialization without timing shifts or summary support in `apps/server/src/twobrain_rec_server/cabinet/exports.py` (FR-015–FR-018)
- [X] T030 [US3] Add SRT route compatibility, MIME/filename, unsupported summary/combined selection, and audit cases in `apps/server/tests/integration/test_transcript_export_egress.py` (FR-018, FR-060–FR-066)

**Checkpoint**: US3 is importable by an SRT-capable player/editor and contains
no fabricated speech.

---

## Phase 6: User Story 4 — Stored Summary Export (Priority: P1)

**Goal**: Summary-only and compatible combined exports use the current saved
outcome set and exact source result without generation or invented fields.

**Independent test**: Export available/partial/deferred/failed/missing stored
outcomes and compare categories/items/references/revision to database truth.

- [X] T031 [P] [US4] Add failing stored-summary snapshot cases for category states, item order, owner/due date, source refs, content hash/revision, unresolved refs, and no generator invocation in `apps/server/tests/unit/test_transcript_exports.py` (FR-020–FR-025)
- [X] T032 [US4] Resolve existing outcome segment references to exact canonical turn ids without guessing and retain unresolved references in `apps/server/src/twobrain_rec_server/cabinet/exports.py` (FR-023/FR-025)
- [X] T033 [P] [US4] Add failing summary-only and combined TXT/MD/JSON/XLSX cases for section order, missing states, boundaries, and transcript exclusion/inclusion in `apps/server/tests/unit/test_transcript_exports.py` (FR-020–FR-025, SC-007)
- [X] T034 [US4] Implement summary-only and combined projections in the existing serializers in `apps/server/src/twobrain_rec_server/cabinet/exports.py` (FR-020–FR-025)
- [X] T035 [P] [US4] Add missing/partial/generating/failed/stale stored-outcome capability and response cases, with deferred/not-requested represented truthfully as missing rather than as an invented revision, in `apps/server/tests/integration/test_transcript_export_egress.py` (FR-022, FR-037, SC-008)
- [X] T036 [US4] Replace only canonical content-export summary behavior while preserving the legacy summary seed/package truth in `apps/server/src/twobrain_rec_server/cabinet/egress.py` (FR-056, FR-065)
- [X] T037 [US4] Add summary-only/combined separate-policy, same-result revision pinning, and no-regeneration integration proof in `apps/server/tests/integration/test_transcript_export_egress.py` (FR-020, FR-061, SC-007/SC-010)

**Checkpoint**: US4 exports stored summary truth and never changes it.

---

## Phase 7: User Story 5 — Export Choice, Preview, And Feedback (Priority: P2)

**Goal**: Meeting detail provides one clear, accessible export journey with
truthful compatibility/readiness and safe progress/failure behavior.

**Independent test**: Complete the dialog as each actor/state using keyboard and
embedded/mobile widths; confirm format/scope, metadata preview, focus, and error
truth.

- [X] T038 [P] [US5] Add failing meeting-detail rendering cases for one Export action, Files/governance state, scope-first compatible formats, metadata-only preview, and disabled reasons in `apps/server/tests/unit/test_cabinet_web_shell.py` (FR-030–FR-037)
- [X] T039 [P] [US5] Add failing browser route/CSRF/access cases for capability and canonical file form submissions in `apps/server/tests/integration/test_cabinet_meeting_detail.py` (FR-030–FR-039)
- [X] T040 [US5] Add export capability/dialog view models using existing cabinet primitives in `apps/server/src/twobrain_rec_server/cabinet/rendering.py` (FR-030–FR-037)
- [X] T041 [US5] Render the contextual action, Files state, scope/format/options, revision/readiness, structural preview, progress, and safe errors through the existing trusted-component seam in `apps/server/src/twobrain_rec_server/cabinet/rendering.py` and `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_detail_content.html` (FR-030–FR-039)
- [X] T042 [P] [US5] Add minimal dialog/progress/responsive/focus styles with visible/non-color states in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css` (FR-039–FR-040)
- [X] T043 [US5] Add minimal client behavior for focus trap/return, duplicate-submit prevention, live status, copy/download/error handling, and reduced motion in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js` (FR-036–FR-040)
- [X] T044 [US5] Complete synthetic in-app browser and embedded-width keyboard/screen-reader/zoom/console/overflow/brand-distance QA, measure representative long-export runtime, and record metadata-safe findings in `specs/120-transcript-export/design-qa.md` (SC-006, SC-012)

**Checkpoint**: US5 exposes the completed export capability without becoming a
second authorization or canonicalization owner.

---

## Phase 8: User Story 6 — Lifecycle, Policy, And Provider-Neutral Truth (Priority: P2)

**Goal**: Every attempt is revision-pinned, separately policy-gated,
metadata-audited, deletion-safe, retryable, and provider-neutral.

**Independent test**: Exercise policy/access/deletion/audit/revision races and a
second provider adapter; no denied/stale/mixed bytes escape.

- [X] T045 [P] [US6] Add owner/permitted/view-only/denied and transcript/summary/combined policy matrix cases in `apps/server/tests/integration/test_transcript_export_egress.py` (FR-060–FR-063, SC-008/SC-013)
- [X] T046 [P] [US6] Add access-revoked, deletion-before/during, stale-expired selection, and audit-request/completion failure cases in `apps/server/tests/integration/test_transcript_export_egress.py` (FR-053–FR-055, FR-060–FR-063)
- [X] T047 [US6] Hold the bounded export transaction through final lifecycle/access recheck and completion audit before releasing bytes in `apps/server/src/twobrain_rec_server/cabinet/egress.py` (FR-053–FR-055, FR-060–FR-063)
- [X] T048 [P] [US6] Add no-secret/content assertions for responses, problems, audit/activity, logs, filenames, and committed evidence in `apps/server/tests/contract/test_transcript_export_no_secret_egress.py` (FR-055, SC-009)
- [X] T049 [P] [US6] Add RLS inventory coverage plus strict PostgreSQL tenant-isolation proof for canonical export reads and audit writes in `apps/server/tests/contract/test_rls_access_outcomes.py` and `apps/server/tests/integration/test_rls_postgres_policies.py` (FR-060–FR-063)
- [X] T050 [US6] Add revision-race and deterministic-retry integration coverage in `apps/server/tests/integration/test_transcript_export_egress.py`, plus provider-adapter normalized semantic-equivalence coverage with truthful raw/source-id differences in `apps/server/tests/unit/test_transcript_exports.py` (FR-001/FR-006/FR-053, SC-010/SC-011)
- [X] T051 [US6] Add truthful downloaded-copy/deletion boundary copy to the export dialog using existing deletion language in `apps/server/src/twobrain_rec_server/cabinet/rendering.py` (FR-054)

**Checkpoint**: US6 closes the trust boundary; no UI or serializer path can
bypass current server policy or mix revisions.

---

## Phase 9: Polish And Cross-Cutting Validation

- [X] T052 [P] Document behavior, compatibility/migration impact, validation expectations, and known limitations in `CHANGELOG.md`
- [X] T053 [P] Update merged/current product truth only after validated implementation evidence exists in `docs/current-product-status.md`
- [X] T054 Run all focused commands and cross-format fixture comparisons from `specs/120-transcript-export/quickstart.md`
- [X] T055 Run Ruff and `git diff --check` from the repository root and fix only feature-owned findings
- [X] T056 Run `infra/scripts/ci-local.sh` and record metadata-safe validation evidence in `specs/120-transcript-export/tasks.md`
- [X] T057 Reconcile every completed task with focused evidence, GitHub issue status/comments, and exact PR links in `specs/120-transcript-export/tasks.md` and `specs/120-transcript-export/issues.md`
- [X] T058 Run `@ponytail-review` on the implementation diff and remove unjustified abstraction/dependency/persistence while preserving security, accessibility, lifecycle, and revision truth
- [ ] T059 Before general release, conduct and document the representative-reviewer usability study required by SC-014; do not substitute synthetic browser QA for the 90% product outcome
- [X] T060 [US5] Keep the embedded macOS meeting detail visible while a generated `blob:` attachment is saved through WebKit, and add route/source/filename regression coverage in `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift` and `apps/macos/Shared/Tests/DesktopCabinetRoutePolicyTests.swift` (FR-039)

## Phase 10: User Story 5 Follow-up — Compact Dialog And Native Save (Priority: P1)

**Goal**: Make the common export choice understandable at a glance and restore
normal macOS control over filename and destination without changing the
server-owned export snapshot or egress boundary.

**Independent test**: At embedded width and 200% zoom, choose every available
scope/format with keyboard-only navigation, inspect collapsed technical details,
save one generated file to a non-Downloads folder through the native Save
dialog, and cancel a second save without a file, failure state, or route change.

- [X] T061 [P] [US5] Add failing compact-dialog rendering assertions for direct scope/format choices, concise outcome, collapsed technical details, sticky actions, and `Сохранить…` copy in `apps/server/tests/unit/test_cabinet_web_shell.py` (FR-033/FR-036/SC-012a)
- [X] T062 [P] [US5] Replace automatic-download filename tests with failing safe suggested-filename and native-save cancellation/selection seam coverage in `apps/macos/Shared/Tests/DesktopCabinetRoutePolicyTests.swift` (FR-039/SC-012b)
- [X] T063 [US5] Restructure the export markup with existing GRAF dialog primitives and metadata-only progressive disclosure in `apps/server/src/twobrain_rec_server/cabinet/rendering.py` (FR-030–FR-040)
- [X] T064 [US5] Implement compact responsive styles and minimal selection/preview/disclosure behavior while preserving focus, live status, retry, copy, and browser download in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css` and `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js` (FR-033–FR-040/SC-012a)
- [X] T065 [US5] Present `NSSavePanel` from the existing WebKit download coordinator, use the sanitized server filename, and treat cancel as a non-failure in `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift` (FR-039/SC-012b)
- [X] T066 [US5] Re-run synthetic embedded-width/200%-zoom/keyboard/failure QA plus a real native save/cancel smoke and record metadata-safe results in `specs/120-transcript-export/design-qa.md` and `specs/120-transcript-export/quickstart.md` (SC-012/SC-012a/SC-012b)
- [X] T067 [P] Document the export-dialog and native-save behavior, compatibility, and validation boundary in `CHANGELOG.md` (FR-039/FR-040)
- [X] T068 Run focused server/macOS checks, feature quickstart, `@ponytail-review`, `git diff --check`, and `infra/scripts/ci-local.sh`; reconcile evidence in `specs/120-transcript-export/tasks.md` before requesting implementation commit approval

## Phase 11: User Story 5 Follow-up — Plain-Language Export Dialog (Priority: P1)

**Goal**: Make the default export decision understandable without internal
export terminology or a wall of format cards.

**Independent test**: Open export as a first-time reviewer and complete a save
using only `Что сохранить`, `Формат`, and `Сохранить`; verify optional settings
and copy remain available under `Дополнительно` and no technical metadata is
visible.

- [X] T069 [P] [US5] Replace compact-card assertions with failing plain-language two-select, collapsed-secondary-actions, no-technical-copy, and simple-footer assertions in `apps/server/tests/unit/test_cabinet_web_shell.py` (FR-031–FR-038/SC-012c)
- [X] T070 [US5] Simplify export markup to two labelled selects, one short hint, collapsed `Дополнительно`, bounded post-egress copy, and cancel/save actions in `apps/server/src/twobrain_rec_server/cabinet/rendering.py` (FR-031–FR-040)
- [X] T071 [US5] Delete card/preview/technical-detail styling and restore the minimum compatible-select behavior while preserving options, copy, focus, progress, retry, and browser/native delivery in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css` and `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js` (FR-032–FR-039)
- [X] T072 [US5] Re-run synthetic normal/390 px/200% WebKit visual and keyboard checks and record metadata-safe evidence in `specs/120-transcript-export/design-qa.md` (SC-012/SC-012a/SC-012c)
- [X] T073 Run focused server checks, `git diff --check`, Ponytail review, and `infra/scripts/ci-local.sh`; reconcile the follow-up evidence and PR before merge (SC-012/SC-012c)

---

## Validation Evidence

- Final focused unit/contract lane: `125 passed` across serializers, shared
  canonical turns, cabinet shell, API contract, and no-secret checks. The final
  PostgreSQL export integration rerun passed `24` tests; the broader focused
  meeting/export/RLS run passed `47` tests earlier in the same review cycle.
- Synthetic headed-Chromium QA passed the one-dialog, grouped format,
  dynamic metadata/revision preview, keyboard focus/return, copy, safe failure,
  download, zero-console-error, 390 px overflow, and 200% zoom checks recorded
  in `design-qa.md`.
- The embedded-download hotfix focused lane passed `12` route/source/filename
  tests plus a standalone real-WebKit `Blob` to `WKDownload` smoke. A locally
  signed GRAF build then saved one production TXT artifact to Downloads while
  retaining the meeting detail and playback timeline; diagnostics contained
  only download start/finish metadata.
- The final repository gate passed `594` macOS tests, `2013` parallel server
  tests with `1` skipped, and `35` strict PostgreSQL/RLS tests with `1` skipped,
  followed by Ruff, Python compile, Compose validation,
  deployment-evidence scan, and `ci_local_result=pass`.
- Ponytail review retained one justified bounded dependency (`openpyxl`) and
  replaced a hand-rolled XLSX column helper with the dependency's native
  utility (`net: -7 lines`). No new database table, generated-artifact
  persistence, background workflow, or storage owner was added.
- The compact-dialog follow-up passed `63` cabinet shell/static-contract tests,
  `74` export unit/contract checks, `49` focused PostgreSQL meeting/export/RLS
  checks, and `81` focused macOS cabinet tests. The final repository gate again
  passed `594` macOS tests, `2013` parallel server tests with `1` skipped, and
  `35` strict PostgreSQL/RLS tests with `1` skipped; Ruff, JavaScript syntax,
  Python compile, Compose validation, evidence scan, and `git diff --check`
  were also clean.
- The plain-language follow-up removed the card grid, diagnostic summary,
  technical disclosure, and related styling/JavaScript. Compatible format
  data remains the existing minimal source for filtering the native select;
  native cancellation and filename seams are unchanged. The diff deletes more
  code than it adds and introduces no dependency, service, table, or artifact
  persistence.
- The final plain-language validation passed `63` focused cabinet shell/static
  contract tests, synthetic normal/390 px/200% WebKit visual checks,
  JavaScript syntax, Ruff, `git diff --check`, and the complete repository gate
  with `ci_local_result=pass`.
- After merging the current `master`, the repository gate passed `608` macOS
  tests, `2178` parallel server tests with `1` skipped, and `41` strict
  PostgreSQL/RLS tests with `1` skipped. Production deploy of runtime SHA
  `89084647eb492b770e1efbf4b50ee4039f6fa50c` then passed backup, restore
  rehearsal, migration-head, RLS, smoke, cleanup, worker, dispatch, and public
  readiness gates.
- T066 live evidence passed in the same-identity signed GRAF build: the native
  Save panel wrote one `582`-byte TXT file to an explicitly selected
  non-Downloads directory; cancelling the second panel created no second file,
  showed no failure, and kept the meeting open. The temporary artifact and
  directory were removed immediately after metadata-only verification.
- T057 is complete: [PR #4084](https://github.com/yshishenya/crisp/pull/4084)
  merged as `7ea8afc517b79fa943ec1ef99d047027234e3c35`; completed task issues
  are closed, and each has a Russian closure comment with its Spec task, PR,
  validation evidence, and out-of-scope boundary.
- T053 is complete in the post-merge closeout: current product truth records
  the backend, web-cabinet UI, six formats, merge SHA, validation, native-app
  boundary, and the still-open T059 release gate. The Spec Kit inventory was
  refreshed from 94/88 to 97/91 spec/task artifacts after Features 114, 119,
  and 120 entered `master`; exact closeout is
  [PR #4085](https://github.com/yshishenya/crisp/pull/4085).
- The current-head quickstart rerun passed `74` unit/contract and `49`
  focused PostgreSQL/RLS tests; Ruff and merged-diff checks also passed.
- T059 is tracked by `#4083` and remains open as a representative-reviewer
  pre-release gate; synthetic browser QA is not counted as SC-014 evidence.
- Controlled production preview is live in release `v2026.07.21.13` at runtime
  SHA `0b923f7e4c1198c39ba17951bd0ced7f2d7bcc3f`. Deploy, backup, restore
  rehearsal, RLS, smoke, cleanup, public health/readiness, bounded owner-only
  policy seed, and installed-GRAF read-back are documented in
  `specs/120-transcript-export/validation/production-preview-2026-07-21.md`.
  This receipt does not close T059 or claim general release.

---

## Dependencies And Execution Order

```text
Setup T001-T003
  -> Foundational T004-T013
      -> US1 T014-T019
      -> US2 T020-T027
      -> US3 T028-T030
      -> US4 T031-T037
          -> US5 T038-T044
          -> US6 T045-T051
              -> Polish T052-T058
                  -> Pre-release product outcome T059
                  -> Embedded download regression T060
                      -> Compact dialog/native save T061-T068
```

- T004-T013 block every story: serializers must not invent their own snapshot,
  canonicalization, policy, or audit.
- US1 is the minimum user-visible increment.
- US2 and US3 can proceed in parallel after foundational work; both reuse the
  same dispatch and file route.
- US4 depends only on foundational snapshot/outcome support and can proceed in
  parallel with US1-US3 after T013.
- US5 should consume stable capability/format contracts from US1-US4.
- T061-T062 are the failing contract seams for the follow-up; T063-T065 depend
  on them, T066 follows the implementation, and T068 closes the validation lane.
- US6 may add tests in parallel, but final transaction/audit behavior must cover
  all serializers before polish.

## Parallel Examples

### US1

```text
T014 TXT/MD serializer tests
T017 route/compatibility contract tests
```

### US2

```text
T020 CSV tests
T021 JSON tests
T022 XLSX tests
```

### US3 / US4

```text
T028 SRT tests
T031 stored-summary snapshot tests
T033 summary projection tests
```

### US5 / US6

```text
T038 rendering tests
T039 browser route tests
T045 policy matrix tests
T048 no-secret contract tests
T049 RLS tests
```

## Implementation Strategy

1. Finish foundational shared truth and make its focused tests green.
2. Deliver US1 as the smallest useful canonical export.
3. Add structured and caption projections without changing snapshot/egress.
4. Add stored summary projections without invoking generation.
5. Expose the completed compatibility matrix through one accessible dialog.
6. Close lifecycle/race/RLS/no-secret evidence across every serializer.
7. Run focused quickstart, full repository gate, Ponytail review, issue/evidence
   reconciliation, then request approval before implementation commit/push/PR.

## Format Validation

- 68 tasks use the required checkbox and sequential `T###` format.
- Every story task has `[US#]`; setup/foundational/polish tasks do not.
- `[P]` is used only for tasks on distinct files or independently writable test
  sections after their shared prerequisites.
- Every task names an exact repository path and maps to requirements or a
  validation artifact.
