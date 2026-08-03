# Tasks: meeting-summary-ux

**Input**: Design documents from `/specs/138-meeting-summary-ux/`

**Prerequisites**: `spec.md`, `clarifications.md`, `plan.md`, `research.md`,
`data-model.md`, `contracts/meeting-summary-ui.md`, `quickstart.md`,
`checklists/ux.md`, `checklists/security.md`

**Tests**: Required by the high-risk validation lane. Tests are written before
the matching implementation task and tasks are marked `[X]` only after the
focused checks pass.

## Phase 1: Contract tests (TDD)

**Purpose**: Lock the simple IA, truth-state, evidence and existing export contract
before changing the renderer.

- [X] T001 [P] [US1] Add synthetic ready/empty outcome markup assertions for
  priority order, compact secondary states, long text and all eight categories
  in `apps/server/tests/unit/test_cabinet_web_shell.py`.
- [X] T002 [P] [US2] Add owner/due/truth/source seek assertions, including absent
  metadata and no fabricated values, in `apps/server/tests/unit/test_cabinet_web_shell.py`.
- [X] T003 [P] [US3] Add processing/blocked safety assertions and web/embedded
  state/source-basis parity in `apps/server/tests/integration/test_cabinet_meeting_outcomes.py`.
- [X] T004 [P] [US4] Add detail-tab URL hash and existing export presence contract
  assertions in `apps/server/tests/unit/test_cabinet_web_shell.py`.

## Phase 2: User Story 1 - 30-second scan (Priority: P1) 🎯 MVP

**Goal**: Make the first useful information visually dominant while retaining
all existing truth categories.

**Independent Test**: The focused shell tests render ready, empty and long
synthetic outcomes with the required order and no missing category contract.

- [X] T005 [US1] Rebuild the outcome hierarchy and bounded state rendering in
  `apps/server/src/twobrain_rec_server/cabinet/rendering.py`, preserving
  access-safe content and existing eight category attributes.
- [X] T006 [US1] Add simple document sections, native secondary disclosure,
  wrapping and playback-safe spacing in
  `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`.

## Phase 3: User Story 2 - actions, owners, due dates and evidence (Priority: P1)

**Goal**: Turn stored action items into checkable next steps without inventing
assignments or dates.

**Independent Test**: A synthetic item with owner/due and two source refs renders
both metadata values and two labelled seek controls; missing fields render no
fabricated values.

- [X] T007 [US2] Render only saved owner/due/truth metadata and escaped
  timestamp seek controls in
  `apps/server/src/twobrain_rec_server/cabinet/rendering.py`, reusing existing
  `data-seek-seconds` playback behavior.
- [X] T008 [US2] Add focused item metadata/source control styles and mobile
  wrapping in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`.

## Phase 4: User Story 3/5 - trust and degraded states (Priority: P1/P2)

**Goal**: Keep truth-state labels meaningful and prevent blocked/processing
content leakage or fake actions.

**Independent Test**: Processing, blocked, deferred and unsafe fixtures retain
their state map, show no item text where items are not displayable, and preserve
the transcript/player surface when available.

- [X] T009 [US3] Add a single source/provenance explanation and state-aware
  category presentation without changing `view_models.py` semantics in
  `apps/server/src/twobrain_rec_server/cabinet/rendering.py`.
- [X] T010 [US5] Preserve explicit summary candidate/acceptance controls and add
  regression assertions for current accepted outcome, share/export and bounded
  deletion visibility in `apps/server/tests/unit/test_cabinet_web_shell.py`,
  `apps/server/tests/integration/test_cabinet_meeting_outcomes.py` and
  `apps/server/tests/integration/test_recording_share_public_link.py`.

## Phase 5: User Story 4/6 - navigation and export discoverability (Priority: P2)

**Goal**: Make evidence and summary saving discoverable using existing browser
  primitives and server-mediated policy.

**Independent Test**: Browser runtime confirms tab hash persistence, source
  controls, collapsed secondary sections, no horizontal overflow, and existing
  export trigger presence.

- [X] T011 [US4] Update detail tab activation to write/read `#outcomes` and
  `#recording` in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`.
- [X] T012 [US6] Keep the existing meeting Share/Export flow without adding a
  duplicate inline summary CTA in the outcome renderer or cabinet JS.
- [X] T013 [US4] Add synthetic desktop/mobile browser evidence for hierarchy,
  seek controls, states, URL hash, collapsed secondary sections and overflow in
  `specs/138-meeting-summary-ux/evidence/summary-runtime-check.cjs`.

## Phase 6: Polish and validation

- [X] T014 [P] Update behavior, accessibility, trust-state and export
  discoverability notes in `CHANGELOG.md`.
- [X] T015 Run the focused pytest commands and browser runtime check from
  `specs/138-meeting-summary-ux/quickstart.md`, then mark the matching tasks
  complete only when evidence is metadata-only.
- [X] T016 Run `git diff --check` and `infra/scripts/ci-local.sh --fast`; record
  lane/evidence and known limitations in `specs/138-meeting-summary-ux/quickstart.md`.

## Dependencies & Execution Order

- T001–T004 precede implementation and can be written in parallel only where
  file scopes are separate; T001/T002/T004 share one test file and are
  sequential in a single working tree.
- T005–T006 establish the renderer and visual hierarchy before T007–T008 add
  item-level metadata.
- T009–T010 preserve degraded/candidate safety after the renderer changes.
- T011–T013 depend on the new markup contract; T013 is the browser evidence
  gate before closeout.
- T014–T016 are final polish and repository validation; no deploy or production
  mutation is authorized.
