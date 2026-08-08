# Tasks: Interactive Playback Timeline

**Input**: Design documents from `/specs/118-interactive-playback-timeline/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/playback-speaker-review.md](./contracts/playback-speaker-review.md), [quickstart.md](./quickstart.md)

**Tests**: Required before implementation because this is a high-risk shared playback/transcript and authorized-data slice.

**Organization**: Tasks are grouped by independently testable user story; no new project setup or dependency installation is required.

## Phase 1: User Story 1 - One shared seek timeline (Priority: P1) 🎯 MVP

**Goal**: Main playback and every speaker lane represent the same horizontal time and seek through one bounded path.

**Independent Test**: Equivalent positions on the main control and any lane resolve within 0.25 seconds, including speech and gap areas, while keyboard range behavior remains available.

- [X] T001 [US1] Add failing shared-scale, lane-seek metadata, and native-range accessibility coverage in `apps/server/tests/unit/test_cabinet_web_shell.py` and `apps/server/tests/contract/test_cabinet_playback_contract.py`.
- [X] T002 [US1] Render one measurable timeline scale, bounded segment timing, and repeated playhead anchors in `apps/server/src/twobrain_rec_server/cabinet/rendering.py`.
- [X] T003 [US1] Align progress and speaker tracks to the native range thumb geometry at supported widths in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`.
- [X] T004 [US1] Route range, lane, skip, and timestamp seeks through one bounded synchronization function in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`.

**Checkpoint**: The current player and all lanes seek on one visually aligned timeline without transcript-following or rename persistence.

---

## Phase 2: User Story 2 - Active speaker and transcript follow (Priority: P2)

**Goal**: Current audio time identifies active speaker lanes and the deterministic transcript turn; deliberate seeks center that turn without stealing focus.

**Independent Test**: Single-speaker, overlap, silence, before-first-turn, pause, end, and deliberate-seek samples produce the required active/current states and reduced-motion behavior.

- [X] T005 [US2] Add failing stable speaker-key, transcript anchor, interval, overlap, and fallback coverage in `apps/server/tests/unit/test_cabinet_view_models.py`, `apps/server/tests/unit/test_cabinet_web_shell.py`, and `apps/server/tests/contract/test_transcript_turn_contract.py`.
- [X] T006 [US2] Add provider-neutral `speaker_key` fields and project them through canonical segments/turns/lanes in `apps/server/src/twobrain_rec_server/api/schemas.py` and `apps/server/src/twobrain_rec_server/cabinet/view_models.py`.
- [X] T007 [US2] Render transcript/lane timing anchors and implement active-lane plus deliberate transcript-follow states with reduced motion in `apps/server/src/twobrain_rec_server/cabinet/rendering.py`, `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`, and `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`.

**Checkpoint**: Playback and deliberate seek expose speaker and transcript context while ordinary playback does not continuously scroll or move focus.

---

## Phase 3: User Story 3 - Manual speaker names (Priority: P3)

**Goal**: Creator or workspace owner/admin can set or clear a meeting-local speaker display name that survives reload and appears consistently; viewers remain read-only.

**Independent Test**: Set, replace, reload, and clear a synthetic name across browser and embedded paths, then prove unauthorized/cross-workspace/invalid requests fail closed, audit is metadata-only, and meeting deletion removes the override.

- [X] T008 [P] [US3] Add failing persistence, validation, authorization, CSRF, audit, browser/embedded parity, and projection coverage in `apps/server/tests/integration/test_speaker_names.py` and `apps/server/tests/unit/test_cabinet_web_shell.py`.
- [X] T009 [P] [US3] Add failing tenant-RLS, migration, and meeting-deletion purge coverage in `apps/server/tests/integration/test_rls_meeting_content_policies.py`, `apps/server/tests/integration/test_postgres_migrations.py`, and `apps/server/tests/integration/test_speaker_names.py`.
- [X] T010 [US3] Add the meeting-scoped speaker-name model, tenant policy, uniqueness constraints, and service/audit behavior in `apps/server/src/twobrain_rec_server/db/models/processing.py`, `apps/server/src/twobrain_rec_server/db/models/__init__.py`, `apps/server/src/twobrain_rec_server/db/migrations/versions/0029_meeting_speaker_names.py`, and `apps/server/src/twobrain_rec_server/cabinet/speakers.py`.
- [X] T011 [US3] Load display overrides, expose `can_rename`, project names without mutating imported labels, and purge overrides with meeting content in `apps/server/src/twobrain_rec_server/cabinet/queries.py`, `apps/server/src/twobrain_rec_server/cabinet/view_models.py`, `apps/server/src/twobrain_rec_server/api/schemas.py`, and `apps/server/src/twobrain_rec_server/deletion/service.py`.
- [X] T012 [US3] Add CSRF-protected browser/embedded rename routes and the compact existing-design-system editor in `apps/server/src/twobrain_rec_server/cabinet/web_routes/speakers.py`, `apps/server/src/twobrain_rec_server/cabinet/web.py`, `apps/server/src/twobrain_rec_server/cabinet/rendering.py`, and `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`.

**Checkpoint**: All three user stories are independently functional and safe across browser and desktop-embedded cabinet surfaces.

---

## Phase 4: Polish, evidence, and repository gate

- [X] T013 [P] Update `[Unreleased]` behavior notes and feature references in `CHANGELOG.md`.
- [X] T014 Run the focused scenarios from `specs/118-interactive-playback-timeline/quickstart.md`, fix failures, and record only synthetic metadata-safe outcomes in `specs/118-interactive-playback-timeline/tasks.md`.
- [X] T015 Perform in-app browser interaction/design QA against the supplied behavior references at browser and embedded widths, resolve P0-P2 findings, and write `design-qa.md` with `final result: passed`.
- [X] T016 Run `git diff --check` and `infra/scripts/ci-local.sh`, then reconcile every completed task with its GitHub issue and record the merged implementation/release boundary in `specs/118-interactive-playback-timeline/tasks.md`.

### Synthetic validation evidence

- Focused PostgreSQL-backed suite: 148 passed with two upstream deprecation warnings; disposable database and container removed by the runner.
- Focused Ruff validation: passed for the changed API, cabinet, model, deletion, migration, contract, integration, and unit-test surfaces.
- In-app browser: 8.97-second overlap seek activated two lanes and the 8.00-second transcript turn; 18.92-second silence seek activated no lanes and centered the deterministic transcript turn.
- Geometry: desktop range-to-lane inset was 8 px per edge; embedded 900 px mode was 10 px per edge with no horizontal overflow.
- Rename/reload, reduced motion, browser/embedded parity, visible focus, and zero browser console warnings/errors were verified with synthetic data. The source-versus-implementation review is recorded in repository-root `design-qa.md` with `final result: passed`.
- Full repository gate: `git diff --check` and `infra/scripts/ci-local.sh` passed after synchronizing the OpenAPI contract, packaged migration head, and RLS inventories for migration `0029_speaker_names`.
- GitHub issues #3922-#3937 received task-specific local validation comments; PR #3944 links the implementation and is merged. Tracker closure remains a separate issue-state operation.

## Phase 5: Production visual follow-up

- [X] T017 [US1] Add regression coverage for one explicit visual scale shared by the range thumb and every lane playhead in `apps/server/tests/unit/test_cabinet_web_shell.py`.
- [X] T018 [US3] Move the authorized speaker-name editor into the playback timeline, preserve the non-playable fallback, and rerun focused, visual, and full validation in `apps/server/src/twobrain_rec_server/cabinet/rendering.py`, `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`, `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`, `design-qa.md`, and `CHANGELOG.md`.

Follow-up evidence: 62 focused cabinet tests and 10 focused PostgreSQL playback/name tests passed; the full server gate passed with 1954 tests and 34 strict-RLS tests after limiting the disposable PostgreSQL run to one worker to stay within Docker memory. The macOS suite passed 583 tests, and Ruff, JavaScript syntax, contract validation, and `git diff --check` passed. Installed-app production inspection remains part of release closeout rather than implementation validation.

## Phase 6: Krisp-density playback follow-up

- [X] T019 [US1] Keep every speaker name above its full-width lane, reduce the lane rhythm to a compact fixed dock, and bind the dock edge to the browser/embedded content boundary in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css` and `apps/server/tests/unit/test_cabinet_web_shell.py` ([#3981](https://github.com/yshishenya/crisp/issues/3981)).
- [X] T020 [US2] Project one stable speaker color into lane segments, transcript dots, and transcript turn borders while retaining a non-color active outline in `apps/server/src/twobrain_rec_server/cabinet/rendering.py`, `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`, and `apps/server/tests/unit/test_cabinet_web_shell.py` ([#3982](https://github.com/yshishenya/crisp/issues/3982)).
- [X] T021 [US3] Move authorized rename forms into one native top-left speaker manager, preserve the existing endpoint/CSRF behavior, and add keyboard cancel coverage in `apps/server/src/twobrain_rec_server/cabinet/rendering.py`, `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`, and `apps/server/tests/unit/test_cabinet_web_shell.py` ([#3983](https://github.com/yshishenya/crisp/issues/3983)).
- [X] T022 Re-run rendered source-versus-implementation QA, the repository gate, and release closeout after explicit commit/deploy approval; record the final production evidence in `design-qa.md` ([#3984](https://github.com/yshishenya/crisp/issues/3984)).

Phase 6 evidence: the exact quickstart selection passed 149 PostgreSQL-backed tests after rebasing onto `v2026.07.21.7`; the complete repository gate passed with 583 macOS tests, 1954 server tests plus 34 strict-RLS tests, Ruff, JavaScript syntax, Python compilation, compose validation, deployment-evidence scan, and `git diff --check`. Rendered and production evidence is closed by T022 below.

Installed-app follow-up: the compact timeline and central-column dock rendered correctly in `v2026.07.21.8`, but the native disclosure element used by the speaker manager did not respond reliably in the macOS WebView accessibility path. T021 was hardened with an explicit button, `aria-expanded` state, outside-click close, and separate Escape behavior for rename cancellation before final T022 closeout.

Final Phase 6 evidence: PRs [#4008](https://github.com/yshishenya/crisp/pull/4008) and [#4009](https://github.com/yshishenya/crisp/pull/4009) are merged and release [v2026.07.21.9](https://github.com/yshishenya/crisp/releases/tag/v2026.07.21.9) is live. The exact feature selection passed 149 tests; the repository gate passed 583 macOS tests, 1954 server tests, 34 strict-RLS tests, Ruff, compilation, Compose, and deployment evidence. Production deploy, backup/restore rehearsal, smoke cleanup, public artifact re-fetch, in-app update from `.8` to `.9`, speaker-manager open/cancel, lane seek, active-lane outline, and centered transcript follow all passed without changing meeting data.

## Dependencies & Execution Order

- US1 is the MVP and has no dependency on rename persistence.
- US2 reuses US1 synchronization but remains independently testable with existing speaker/turn data.
- US3 reuses stable speaker keys from US2; T008 and T009 can be authored in parallel before T010–T012.
- T013 can run after behavior stabilizes; T014–T016 run sequentially after all requested stories.

## Parallel Opportunities

- T008 and T009 touch different test surfaces and can run in parallel.
- T013 can run in parallel with the first focused validation pass after implementation stabilizes.

## Implementation Strategy

1. Ship the aligned seek surface first (T001–T004).
2. Add active speaker and transcript following on the same synchronization path (T005–T007).
3. Add the smallest durable rename boundary (T008–T012).
4. Finish changelog, browser/design QA, focused checks, full CI, and issue reconciliation (T013–T016).

## Format Validation

- All 16 tasks use checkbox, sequential `T###`, correct story labels where applicable, and exact repository paths.
- No task adds a new dependency, framework, playback implementation, or speaker identity subsystem.
