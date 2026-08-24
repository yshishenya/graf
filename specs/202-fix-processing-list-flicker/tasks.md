# Tasks: Стабильные статусы обработки в списке встреч

**Risk lane**: `significant/high-risk UX`

## Phase 1: Regression first

- [X] T001 [P] [US1] Add server-rendering regressions for stable processing readiness and no processing-only full-list poll in `apps/server/tests/unit/test_cabinet_web_shell.py`
- [X] T002 [P] [US1] Add a JavaScript lifecycle regression for processing between failed rows, repeated 15-second ticks, identity/generation fences and one terminal refresh in `apps/server/tests/contract/test_cabinet_static_assets_contract.py`

## Phase 2: Minimal shared fix

- [X] T003 [US1] Reserve active processing readiness in `apps/server/src/twobrain_rec_server/cabinet/view_models.py` and remove submitted/processing from full-list polling in `apps/server/src/twobrain_rec_server/cabinet/rendering.py`
- [X] T004 [US1] Limit projection to active processing rows, schedule the existing 15-second lifecycle and route terminal transitions through canonical refresh in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`

## Phase 3: Validation and closeout

- [X] T005 [P] [US2] Update `[Unreleased]` in `CHANGELOG.md` and verify browser/embedded copy, focus, selection and narrow layout with metadata-only evidence
- [X] T006 [US2] Run `specs/202-fix-processing-list-flicker/quickstart.md`, `infra/scripts/ci-local.sh --fast`, review the final diff, and reconcile GitHub issue/PR evidence

## Dependencies

- T001/T002 must fail for the confirmed reason before T003/T004.
- T003 and T004 implement one contract and precede T005/T006.
- T006 is the PR gate; full CI/deploy are excluded until release approval.

## GitHub issue mapping

- T001–T002: #5805
- T003–T004: #5806
- T005–T006: #5807
