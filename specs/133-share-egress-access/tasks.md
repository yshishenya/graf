# Tasks: полный egress внешнего приглашения

**Input**: Design documents from `/specs/133-share-egress-access/`

**Prerequisites**: `spec.md`, `research.md`, `data-model.md`,
`contracts/shared-meeting-egress.md`, `quickstart.md`, security and UX
checklists

**Risk lane**: `high-risk-feature`; tests precede implementation and full local
CI is required before PR/closeout.

## Phase 1: Foundational regression coverage

- [X] T001 [US1] Extend the external full-invitation integration test in
  `apps/server/tests/integration/test_recording_share_public_link.py` to assert
  transcript download plus metadata-only transcript and combined exports, while
  retaining audio playback/download and capability format assertions.
  GitHub: #4678
- [X] T002 [US2] Extend the same integration matrix in
  `apps/server/tests/integration/test_recording_share_public_link.py` to assert
  revoke denial for shared egress and preserve summary-only restrictions without
  adding workspace membership.
  GitHub: #4679

**Checkpoint**: The full package contract is executable before the shared
authorization path changes.

## Phase 2: User Story 1 — full package works

- [X] T003 [US1] Thread optional `ShareRecipientAccessProof` through the common
  egress recheck and content-export functions in
  `apps/server/src/twobrain_rec_server/cabinet/egress.py`, preserving the
  existing owner/team/admin default path.
  GitHub: #4680
- [X] T004 [US1] Return the existing proof from shared authorization and pass it
  to playback, artifact download and content-export routes in
  `apps/server/src/twobrain_rec_server/api/cabinet.py`.
  GitHub: #4681

**Checkpoint**: Accepted external full recipients can use playback, audio and
transcript downloads, and existing report exports when artifacts are ready.

## Phase 3: User Story 2 — boundaries remain closed

- [X] T005 [US2] Verify the shared egress call chain still rechecks grant scope,
  expiry/revoke, deletion, policy and storage/revision readiness using focused
  tests in `apps/server/tests/integration/test_cabinet_playback_route.py`,
  `apps/server/tests/integration/test_transcript_export_egress.py` and the
  external invitation matrix; adjust only the minimal regression assertions
  required by the fix.
  GitHub: #4682

**Checkpoint**: No proof propagation path broadens summary-only, owner-only
policy, revoked, deleted or unavailable-artifact access.

## Phase 4: Documentation and validation

- [X] T006 [P] Update the Russian `[Unreleased]` `Fixed` entry in
  `CHANGELOG.md` and record metadata-only focused evidence in
  `specs/133-share-egress-access/quickstart.md`.
  GitHub: #4683
- [X] T007 Run focused tests, `git diff --check`, Python compile, targeted Ruff
  and `infra/scripts/ci-local.sh`; reconcile this task list with GitHub issues
  and PR evidence before closeout.
  GitHub: #4684

## Dependencies & Execution Order

- T001–T002 precede T003–T004.
- T003 precedes T004 because routes consume the egress parameter.
- T005 follows the implementation and guards the unchanged security boundary.
- T006–T007 follow validation; production release remains separately approved.

## Parallel Opportunities

- T001 and T002 touch the same integration file and should be implemented in one
  focused test edit.
- T006 can run alongside final review after code tests pass.
