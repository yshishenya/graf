# Tasks: meeting-outcome-value

**Input**: Design documents from `/specs/139-meeting-outcome-value/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`contracts/meeting-outcome-value.md`, `quickstart.md`

**Tests**: Required before implementation because this is a high-risk AI/UX,
privacy and release slice. Tests use synthetic content only.

**Organization**: Tasks follow user stories and keep the smallest existing-code
change that closes each independent journey.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because write sets and unmet dependencies differ.
- **[Story]**: Maps to `spec.md` user story.
- Implementation commits remain blocked until focused/fast validation and
  explicit user approval.

## Phase 1: Setup and baseline evidence

**Purpose**: Lock the current synthetic UX/runtime baseline without introducing
new production infrastructure.

- [X] T001 Extend the synthetic current-state Browser harness for owner accepted, candidate, processing, no-player and summary-only states in `specs/139-meeting-outcome-value/evidence/meeting-outcome-runtime-check.cjs`
- [X] T002 [P] Record metadata-only baseline commands, state matrix and forbidden-content rules in `specs/139-meeting-outcome-value/evidence/baseline.md`

**Checkpoint**: Current failures are reproducible with no real meeting content.

---

## Phase 2: Foundational trust contracts

**Purpose**: Strengthen the shared prompt, provenance and release contracts used
by every story before user-facing work.

- [X] T003 Add failing structural-evidence tests for non-empty/unique refs, exact sequence and non-action owner/due rejection in `apps/server/tests/unit/test_outcome_prompts.py`
- [X] T004 Implement the strict response schema and validator invariants in `apps/server/src/twobrain_rec_server/outcomes/prompts.py`
- [X] T005 [P] Add failing stable-speaker and unknown-speaker provenance tests in `apps/server/tests/integration/test_meeting_outcomes_generation.py` and `apps/server/tests/unit/test_summary_candidate_revisions.py`
- [X] T006 Reuse one overlap-based transcript segment loader for deterministic and AI paths in `apps/server/src/twobrain_rec_server/outcomes/service.py` and `apps/server/src/twobrain_rec_server/outcomes/ai_service.py`
- [X] T007 [P] Add failing canonical timestamp/source-role enrichment and stable generator-version tests in `apps/server/tests/unit/test_summary_candidate_revisions.py`
- [X] T008 Enrich stored AI source refs from the pinned transcript and keep the generator version stable in `apps/server/src/twobrain_rec_server/outcomes/ai_service.py`
- [X] T009 [P] Add failing prompt-candidate, worst-example held-out and runtime-sized long-context gate tests in `apps/server/tests/unit/test_outcome_prompts.py` and `apps/server/tests/unit/test_prompt_optimization.py`
- [X] T010 Make changed outcome prompts unlabelled candidates, strengthen judge contracts and gate held-out by the worst example in `apps/server/src/twobrain_rec_server/cli/langfuse_prompts.py` and `apps/server/src/twobrain_rec_server/outcomes/prompt_optimization.py`

**Checkpoint**: Empty/wrong evidence, fake speakers and average-hidden catastrophic
examples fail locally before any UI can expose a candidate.

---

## Phase 3: User Story 1 — strong outcomes start automatically (Priority: P1) 🎯 MVP

**Goal**: First usable transcript creates exactly one durable Auto candidate
without waiting for model/network work or changing accepted truth.

**Independent Test**: Import a synthetic transcript twice and reload; one
accepted fast baseline and one queued/dispatchable Auto identity exist, while
disabled/deleted/stale cases preserve transcript and current outcome.

- [X] T011 [US1] Add failing first-import, replay, disabled-policy, deletion and stale-source tests in `apps/server/tests/integration/test_meeting_outcomes_generation.py`
- [X] T012 [US1] Add an idempotent policy-owned automatic-candidate helper using the meeting creator and exact workspace built-in default in `apps/server/src/twobrain_rec_server/outcomes/ai_service.py`
- [X] T013 [US1] Create/reuse the automatic candidate and dispatch intent after the fast baseline without remote I/O in `apps/server/src/twobrain_rec_server/processing/submit.py`
- [X] T014 [US1] Pass the existing outcome-generation policy through production and manual import callers in `apps/server/src/twobrain_rec_server/workflows/worker.py` and `apps/server/scripts/reprocess_manual_media_uploads.py`

**Checkpoint**: Manual «Обновить итоги» is no longer required for first quality
value; accepted pointer remains unchanged.

---

## Phase 4: User Story 2 — outcome content answers working questions (Priority: P1)

**Goal**: Prompt policy selects outcomes, not greetings or agenda, and treats
proposal/action/decision/correction distinctly.

**Independent Test**: Versioned synthetic fixtures cover greeting, proposal,
retraction, duplicate, empty category, mixed language and long-context position.

- [X] T015 [US2] Add clean-room prompt fixtures and assertions for outcome selection, correction, deduplication, compactness and injection restraint in `apps/server/tests/unit/test_outcome_prompts.py`
- [X] T016 [US2] Rewrite the shared outcome and three judge prompts with explicit category semantics, evidence, unknown and self-check rules in `apps/server/src/twobrain_rec_server/cli/langfuse_prompts.py`
- [X] T017 [US2] Validate all ten built-in plus custom desired prompt snapshots and metadata-only hashes in `apps/server/tests/unit/test_outcome_prompts.py`

**Checkpoint**: Every format changes focus only; common evidence/safety semantics
remain identical.

---

## Phase 5: User Story 3 — every item has a usable source (Priority: P1)

**Goal**: Candidate and accepted AI items carry canonical evidence that can be
resolved to the exact pinned transcript.

**Independent Test**: Empty, duplicate, foreign and wrong-sequence refs fail;
valid refs preserve canonical timestamps through preview and accepted view model.

- [X] T018 [US3] Add failing structured-preview and accepted timestamp provenance tests in `apps/server/tests/contract/test_summary_template_ui_contract.py` and `apps/server/tests/unit/test_meeting_outcomes_view_models.py`
- [X] T019 [US3] Define bounded structured source-reference response models in `apps/server/src/twobrain_rec_server/api/schemas.py`
- [X] T020 [US3] Return canonical structured refs from the owner-only no-store preview route in `apps/server/src/twobrain_rec_server/api/cabinet.py`
- [X] T021 [US3] Preserve seekable enriched refs in accepted outcome projections and exports in `apps/server/src/twobrain_rec_server/cabinet/view_models.py` and `apps/server/src/twobrain_rec_server/cabinet/egress.py`

**Checkpoint**: Evidence survives model validation → persistence → candidate
preview → accepted UI without trusting model-supplied timestamps.

---

## Phase 6: User Story 4 — decisions and actions are conservative (Priority: P1)

**Goal**: Unsupported commitments, people and dates cannot pass the release
gate or be made more specific than the transcript.

**Independent Test**: Synthetic contrasts cover explicit/implicit/cancelled
actions, reassignment, unknown speaker, relative date and no-action meeting.

- [X] T022 [US4] Add adversarial action/decision/owner/due and unknown-restraint fixtures to `apps/server/tests/unit/test_prompt_optimization.py`
- [X] T023 [US4] Enforce critical-failure scoring and per-example pass semantics for action, attribution and injection judges in `apps/server/src/twobrain_rec_server/outcomes/prompt_optimization.py`
- [X] T024 [US4] Add metadata-only eval receipt assertions for action precision/recall, owner/due restraint and must-unit coverage in `apps/server/tests/unit/test_prompt_optimization.py`

**Checkpoint**: One critical unsupported field fails the candidate prompt gate
regardless of mean completeness.

---

## Phase 7: User Story 5 — candidate is easy to review and accept (Priority: P1)

**Goal**: Owner sees the same compact Russian IA, owner/due and source before
choosing between current and new outcomes.

**Independent Test**: Candidate preview has zero internal keys, preserves two
clear decisions and works at desktop and 390 CSS px.

- [X] T025 [US5] Add failing localized grouping, owner/due, source-action and accept/reject UI contract tests in `apps/server/tests/contract/test_summary_template_ui_contract.py`
- [X] T026 [US5] Render localized primary/secondary candidate sections and canonical metadata in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`
- [X] T027 [US5] Reuse existing GRAF document tokens for compact responsive candidate review in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`
- [X] T028 [US5] Capture and compare current-run candidate desktop/mobile interaction evidence in `specs/139-meeting-outcome-value/evidence/meeting-outcome-runtime-check.cjs` and `specs/139-meeting-outcome-value/evidence/after-candidate.md`

**Checkpoint**: Candidate can be checked before accept and does not create a new
workspace or card dashboard.

---

## Phase 8: User Story 8 — every allowed entry remains coherent (Priority: P1)

**Goal**: List, owner, full-viewer and summary-only journeys use truthful artifact
readiness, localized accepted summary and real evidence destinations.

**Independent Test**: Direct/list entries never return JSON dead-ends or raw
keys; no-player source is non-interactive; keyboard jump seeks and focuses exact
transcript; non-ready state is not repeated.

- [X] T029 [US8] Add failing summary-only HTML, list-readiness, aggregate-state, heading and source-destination tests in `apps/server/tests/unit/test_cabinet_web_shell.py`, `apps/server/tests/integration/test_cabinet_meeting_outcomes.py` and `apps/server/tests/contract/test_summary_template_ui_contract.py`
- [X] T030 [US8] Route summary-only browser entry to a localized accepted-summary page and reuse the allowed projection in `apps/server/src/twobrain_rec_server/cabinet/web_routes/browser.py` and `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/shared_meeting_summary_content.html`
- [X] T031 [US8] Derive transcript/outcome artifact readiness and one aggregate summary state in `apps/server/src/twobrain_rec_server/cabinet/queries.py`, `apps/server/src/twobrain_rec_server/cabinet/view_models.py` and `apps/server/src/twobrain_rec_server/cabinet/rendering.py`
- [X] T032 [US8] Make source/timeline controls destination-aware and keyboard/focus complete in `apps/server/src/twobrain_rec_server/cabinet/rendering.py` and `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`
- [X] T033 [US8] Correct heading outline and disabled-action accessible copy in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_detail_content.html` and `apps/server/src/twobrain_rec_server/cabinet/rendering.py`
- [X] T034 [US8] Run the owner/viewer/shared/degraded desktop and 390 CSS px matrix and save synthetic metadata/screenshots in `specs/139-meeting-outcome-value/evidence/after-journey.md`

**Checkpoint**: All permitted routes describe the same accepted result without
content or interaction overclaim.

---

## Phase 9: User Story 6 — failures preserve available value (Priority: P2)

**Goal**: AI/provider/prompt/oversize failures remain distinct and never hide
transcript, playback or current accepted outcome.

**Independent Test**: Each bounded state maps to one localized recovery path;
ambiguous egress does not retry inference and no technical reason code leaks.

- [X] T035 [US6] Add failing processing, dependency, invalid-result, refusal, oversize and ambiguous-outcome presentation tests in `apps/server/tests/contract/test_summary_template_ui_contract.py` and `apps/server/tests/unit/test_summary_candidate_revisions.py`
- [X] T036 [US6] Consolidate truthful localized candidate/degraded recovery copy without changing retry safety in `apps/server/src/twobrain_rec_server/api/cabinet.py`, `apps/server/src/twobrain_rec_server/cabinet/rendering_shared.py` and `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`

**Checkpoint**: A failed quality candidate is a bounded secondary state, not a
lost meeting.

---

## Phase 10: User Story 7 — share/export use only accepted truth (Priority: P2)

**Goal**: Automatic generation never becomes automatic disclosure.

**Independent Test**: Owner, viewer, summary-only, export and deletion/access
race scenarios expose only current accepted outcomes.

- [X] T037 [US7] Add accepted-only candidate/share/export and access/deletion race tests in `apps/server/tests/integration/test_transcript_export_egress.py` and `apps/server/tests/integration/test_cabinet_meeting_outcomes.py`
- [X] T038 [US7] Reuse the authoritative accepted pointer in shared/export projections and remove raw-key drift in `apps/server/src/twobrain_rec_server/cabinet/egress.py`, `apps/server/src/twobrain_rec_server/cabinet/exports.py` and `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/shared_meeting_summary_content.html`

**Checkpoint**: Candidate state changes cannot broaden content authorization.

---

## Phase 11: Cross-cutting validation, prompt promotion and documentation

**Purpose**: Close the implementation gate before any commit, PR, merge or
production mutation.

- [X] T039 [P] Update Russian behavior/release notes and current product status in `CHANGELOG.md` and `docs/current-product-status.md`
- [X] T040 [P] Update prompt/eval and operator quickstart evidence without meeting content in `specs/139-meeting-outcome-value/quickstart.md` and `specs/139-meeting-outcome-value/evidence/eval-receipt.md`
- [X] T041 Run all focused pytest, Ruff, Python compile, JS syntax, diff and forbidden-content checks from `specs/139-meeting-outcome-value/quickstart.md`
- [X] T042 Run Ponytail simplification, security/access-boundary and accessibility review over the final diff; record only actionable metadata in `specs/139-meeting-outcome-value/evidence/review.md`
- [X] T043 Run `infra/scripts/ci-local.sh --fast` and record metadata-only results in `specs/139-meeting-outcome-value/evidence/validation.md`
- [X] T044 Publish changed prompt versions as unlabelled candidates, run versioned synthetic/private-heldout gates and record exact hashes/metrics in `specs/139-meeting-outcome-value/evidence/eval-receipt.md`
- [X] T045 After operator approval, promote the exact passing prompt versions with rollback target and verify a private synthetic end-to-end receipt in `specs/139-meeting-outcome-value/evidence/prompt-promotion.md`

**Checkpoint**: Ask for explicit user approval to create the implementation
commit only after T001–T045 are complete and evidence is green.

---

## Phase 12: Commit, PR, merge, deploy and public package

**Purpose**: Execute the user-requested release train only from validated exact
SHAs and with the required approvals/signing identities.

- [X] T046 Create the approved implementation commit, push `codex/139-meeting-outcome-value` and open a ready Russian PR with task/issue/evidence links
- [X] T047 Wait for GRAF validation and review, address failures without bypasses, then merge the exact green PR SHA to `master` (PR #4851, merge `81bd01b102c86a6ec79cb3f7bba5dae3e812b4ee`; GRAF validation run `30954305938`)
- [ ] T048 Run the full release-candidate lane and `infra/scripts/cd-remote.sh --dry-run --branch master`; execute production deploy only after the explicit deploy gate
- [ ] T049 Re-promote exact outcome `v5` against the compatible deployed SHA, verify prepared `v6` rollback, then run production health/readiness, automatic-candidate, accepted/share and metadata-only smoke checks and record exact runtime SHA in release evidence
- [ ] T050 Prepare the next CalVer release, Developer ID-signed/notarized/stapled public macOS package, Russian GitHub Release and compatible update/publication assets using `scripts/prepare-release.sh` and the repository release procedure

---

## Dependencies & Execution Order

### Phase dependencies

```text
Setup → Foundational → US1
                  ├→ US2 → US4
                  └→ US3 → US5
US1 + US3 + US5 → US8 → US6 + US7
all stories → focused/fast validation → user commit approval
approval → PR/CI/merge → full/dry-run/deploy → public package
```

### Story dependencies

- **US1** depends only on foundational lifecycle contracts.
- **US2** and **US3** can proceed in parallel after foundation.
- **US4** depends on US2 prompt/eval semantics and stable speakers.
- **US5** depends on US3 structured evidence API.
- **US8** depends on US3/US5 source interaction and accepted projection.
- **US6** and **US7** run after the coherent allowed-entry projection exists.

### Parallel opportunities

- T001 and T002 can run in parallel.
- T003/T005/T007/T009 are separate failing-test write sets.
- US2 and US3 can run in parallel after Phase 2.
- T039 and T040 can run in parallel after all code/test tasks.
- Browser evidence can run while independent focused Python suites execute, but
  final validation waits for both.

## Parallel examples

```text
US2 worker: T015 → T016 → T017
US3 worker: T018 → T019 → T020 → T021

After both:
US4 worker: T022 → T023 → T024
US5 worker: T025 → T026 → T027 → T028
```

## Implementation strategy

1. Ship the smallest durable-value MVP first: foundation + US1, with current
   accepted UI unchanged.
2. Close trust before polish: US2–US4.
3. Close decision and entry journeys: US5 + US8.
4. Close degraded/share boundaries: US6 + US7.
5. Validate before any implementation commit; release/deploy/package remain
   exact-SHA gates, never shortcuts.

## Notes

- No new database migration, AI service, dependency, SPA, task hub or chat.
- Every `[X]` requires its focused evidence; running a command alone is not done.
- Do not commit transcript/model output/free judge feedback, secrets or live
  meeting screenshots.
