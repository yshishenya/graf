# Implementation Plan: Понятное меню действий со встречей

**Branch**: `123-meeting-actions-menu` | **Date**: 2026-07-23 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/123-meeting-actions-menu/spec.md`

## Summary

Replace the current 560 px modal opened by `Ещё` with the selected compact,
single-level action menu. Keep `Поделиться` visible, render only server-approved
export/download/details/delete actions, move the existing files/revision/
calendar/speaker/activity truth into a separate details dialog, and preserve the
existing export, audio egress, audit, deletion and revision contracts.

The Ponytail path is deliberately small: reuse the current Jinja fragment,
`MeetingReviewResponse` capability projection, cabinet icon macro, modal focus
helpers, export dialog, audio route and delete confirmation. Add no storage,
endpoint, dependency or client-side capability model.

## Technical Context

**Language/Version**: Python 3.13; browser JavaScript and CSS supported by the current cabinet baseline

**Primary Dependencies**: FastAPI, Jinja2, existing server-rendered cabinet templates and native HTML controls; no new dependency

**Storage**: N/A; no persistence or schema changes

**Testing**: pytest unit, contract and integration tests; existing cabinet validation and local CI

**Risk / Validation Lane**: high-risk-feature because the change touches deletion UX, permission-derived action visibility, accessibility, localization and clean-room brand distance

**Release Gate**: focused quickstart and `infra/scripts/ci-local.sh` before PR; production rollout only through the repository release/deploy gate after merge

**Target Platform**: responsive browser cabinet and embedded macOS WebKit cabinet

**Project Type**: server-rendered web application embedded in a native macOS shell

**Performance Goals**: menu becomes interactive in the same render frame as the existing page and keyboard movement produces no network request

**Constraints**: no new egress, policy, database, endpoint, dependency or copied competitor UI; unavailable actions remain absent; 40 px minimum action targets; usable at 200% zoom and 320 CSS px viewport

**Scale/Scope**: one meeting-detail action surface, one separate details dialog, existing export/download/delete flows and their focused tests

## Constitution Check

### Pre-research gate

- **Capture-first integrity**: PASS. The slice does not touch capture, routing,
  buffering, permissions or recording truth.
- **Visible consent and control**: PASS. Recording controls and one-action Stop
  remain unchanged; Escape is limited to transient menu/dialog dismissal.
- **Data boundary and secrets**: PASS. No new request, payload, egress, trace or
  credential surface is introduced.
- **Deletion truth and lifecycle**: PASS. The existing bounded delete dialog,
  report link, server authorization and lifecycle accounting remain authoritative.
- **Spec-driven delivery**: PASS. High-risk UX uses full specify, clarify,
  plan/research, checklist, tasks, analyze and implementation gates.
- **Original design and accessibility**: PASS. The selected mock builds on the
  existing GRAF tokens and icon source; keyboard, focus, zoom, contrast, reduced
  motion and browser/embedded parity are explicit requirements.

### Post-design gate

PASS with no exception. Phase 1 adds only a UI contract and a no-persistence
data model. The plan reuses all policy, audit, export, download and deletion
authorities and introduces no constitution violation.

## Validation Plan

1. Run focused contract tests for menu semantics, action filtering, keyboard
   behavior, focus return, deletion confirmation and browser/embedded parity.
2. Run meeting-detail integration tests covering ready, processing, denied,
   missing-audio and deletion states.
3. Execute every scenario in [quickstart.md](quickstart.md), including mouse,
   keyboard-only, 200% zoom, narrow width, light/dark, increased contrast and
   reduced motion; verify that server-side authorization remains fail-closed
   when the enhancement script is unavailable.
4. Capture the same open-menu state as the selected visual target and complete
   blocking Product Design QA until `design-qa.md` says `final result: passed`.
5. Run `git diff --check`, targeted Ruff where Python changes occur, and the
   canonical `infra/scripts/ci-local.sh` closeout gate.
6. Run Ponytail review and a final security/accessibility diff review before
   commit, PR and release preparation.

## Project Structure

### Documentation (this feature)

```text
specs/123-meeting-actions-menu/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── design-qa.md
├── contracts/
│   └── meeting-actions-menu.md
├── checklists/
│   ├── requirements.md
│   └── ux.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/src/twobrain_rec_server/cabinet/
├── rendering.py
├── review_policy_rendering.py
├── templates/cabinet/
│   ├── components/icons.html
│   ├── fragments/meeting_governance.html
│   └── pages/meeting_detail_content.html
└── static/cabinet/
    ├── cabinet.css
    └── cabinet.js

apps/server/tests/
├── contract/
│   ├── test_recording_governance_ui_contract.py
│   └── test_recording_workflow_accessibility.py
├── integration/
│   └── test_cabinet_meeting_detail.py
└── unit/
    └── test_cabinet_web_shell.py
```

**Structure Decision**: Keep the existing server-rendered cabinet architecture.
The governance fragment remains the single markup source for browser and
embedded views; existing rendering and policy projections decide which actions
exist; the existing cabinet JS/CSS own progressive enhancement and presentation.

## Complexity Tracking

No constitution exception or additional architectural complexity is required.
