# Implementation Plan: Owner Review Live Polish

**Branch**: `036-owner-review-live-polish` | **Date**: 2026-06-16 | **Spec**: `specs/036-owner-review-live-polish/spec.md`

**Input**: Feature specification from `specs/036-owner-review-live-polish/spec.md`

## Summary

Close the next MVP-readiness slice after 035 by proving the production owner
review path on `rec.2brain.pro`, making notes/actions availability truthful in
meeting review surfaces, polishing the installed desktop and server-owned web
review surfaces toward the accepted V8 clean-room baseline, and updating the
launch-readiness claim without overreaching beyond evidence.

The implementation approach is to keep owner review server-owned, reuse the
existing provider/session auth and temporary smoke-session helpers, add only a
safe browser/session path if needed, keep native macOS capture controls outside
embedded web content, represent notes/actions as structured truth states rather
than fabricated output, make installed-app cabinet connectivity persistent or
packaged for the internal MVP instead of shell-env-only, and commit
metadata-safe evidence only.

## Technical Context

**Language/Version**: Python 3.13 backend; Swift 6 macOS app; server-rendered
HTML/CSS for the current cabinet web surface.

**Primary Dependencies**: FastAPI, Pydantic, SQLAlchemy/Alembic, pytest/Ruff,
SwiftUI, WebKit, macOS native capture controls, existing readiness scripts, and
GitHub Spec Kit artifacts.

**Storage**: Existing Postgres tables for auth sessions, users, workspaces,
devices, meetings, processing results, transcript segments, sharing, egress,
retention, and deletion lifecycle. Existing local macOS Application Support
recording storage is evidence-only for this slice. No new content-bearing
storage is planned unless implementation discovers a required schema gap for
non-secret metadata state.

**Testing**: pytest contract/integration/unit tests for cabinet, auth,
readiness, and forbidden-content boundaries; Ruff and Python compile checks;
Swift build and focused macOS tests for desktop shell/capture control
visibility and cabinet configuration resolution; metadata-safe live
`curl`/Chrome checks against `rec.2brain.pro`; installed-app launch proof from
`/Applications/2brain Rec.app` without relying on shell-only environment
variables; canonical `infra/scripts/ci-local.sh`.

**Target Platform**: Production Rec web service at `https://rec.2brain.pro`;
local macOS desktop app installed at `/Applications/2brain Rec.app`; backend
Docker/remote deployment path remains bounded by existing infrastructure gates.

**Project Type**: Multi-surface product slice: FastAPI web/API, server-rendered
review UI, macOS desktop shell, readiness/evidence documentation.

**Performance Goals**: Meeting list/detail review states should render in the
same request shape as existing cabinet routes; no additional background
processing or large transcript payload expansion is introduced by notes/action
truth states. Desktop capture controls must remain responsive and visible while
embedded review content loads or fails.

**Constraints**: No raw audio, private transcript text, account identifiers,
tokens, cookies, signed URLs, private local paths, provider payloads, or private
reference captures in committed artifacts. No hidden recording state. No
desktop-held MediaScribe credentials. No public-link/external-recipient,
assisted auto-start, signed-installer, broad rollout, or generated-notes claim
without separate evidence.

**Scale/Scope**: One owner-review live proof path, one installed-app cabinet
connection path, one set of notes/action truth states, runtime-critical
V8-aligned desktop/web review surfaces, and one 036 readiness closeout pack.
This does not implement all 17 V8 frames, broad production rollout, or full
AI-generated meeting outcomes unless existing stored data can be proven safely.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Reason |
|-----------|--------|--------|
| I. Capture-First MVP Integrity | PASS | 036 does not replace the accepted system-audio capture path and preserves native capture controls as authoritative. |
| II. Visible Consent And User Control | PASS | Active capture stays visible with one-action Stop/Pause/Resume in the desktop app; web review content cannot obscure native controls. |
| III. Data Boundary And Secret Discipline | PASS | Desktop still does not call MediaScribe or hold MediaScribe credentials; evidence and auth proof are metadata-safe and token-redacted. |
| IV. Deletion Truth And Lifecycle Accounting | PASS | Governance and deletion states remain truthful and bounded to 2brain-controlled storage/dependencies. |
| V. Spec-Driven Delivery With Testable Gates | PASS | Full Spec Kit sequence is active; clarify completed; plan/checklist/tasks/analyze will run before implementation. |

## Project Structure

### Documentation (this feature)

```text
specs/036-owner-review-live-polish/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── notes-action-truth-contract.md
│   ├── owner-review-live-proof-contract.md
│   ├── readiness-claim-contract.md
│   └── runtime-polish-cleanroom-contract.md
└── tasks.md

docs/evidence/036-owner-review-live-polish/
├── README.md
├── validation-log.md
├── launch-gap-register.md
├── readiness-report.json
├── readiness-report.md
├── clean-room-reference.md
└── screenshots/
```

### Source Code (repository root)

```text
apps/server/src/twobrain_rec_server/
├── api/
│   ├── auth.py
│   ├── cabinet.py
│   └── schemas.py
├── auth/
│   ├── dependencies.py
│   └── sessions.py
├── cabinet/
│   ├── access.py
│   ├── queries.py
│   ├── view_models.py
│   └── web.py
└── readiness/
    ├── evidence.py
    ├── matrix.py
    └── report.py

apps/server/scripts/
├── issue_smoke_auth_session.py
├── cleanup_smoke_auth_session.py
└── generate_mvp_loop_readiness.py

apps/server/tests/
├── contract/
├── integration/
└── unit/

apps/macos/RecApp/Sources/
├── Cabinet/
│   ├── DesktopCabinetConfiguration.swift
│   ├── DesktopCabinetRoutePolicy.swift
│   ├── DesktopCabinetWorkspaceView.swift
│   ├── DesktopMeetingShellView.swift
│   └── EmbeddedCabinetWebView.swift
└── SystemAudio/

apps/macos/Shared/Tests/
```

**Structure Decision**: Keep server-owned review UI and API behavior in
`apps/server/src/twobrain_rec_server/cabinet` and auth/session behavior in
`apps/server/src/twobrain_rec_server/auth`. Keep desktop product polish and
installed-app cabinet connection resolution in the existing macOS Cabinet views
and configuration path while preserving capture control source of truth in
native SwiftUI. Keep production and local evidence under
`docs/evidence/036-owner-review-live-polish`.

## Complexity Tracking

No constitution violations are planned.

## Phase 0 Research

Research output is recorded in `specs/036-owner-review-live-polish/research.md`.
All planning unknowns are resolved there before implementation:

- owner review auth proof on `rec.2brain.pro`;
- browser/session versus header-only smoke access;
- installed-app cabinet configuration versus shell-only environment variables;
- notes/action output truth versus generated-output implementation;
- V8 runtime-critical polish scope;
- metadata-safe evidence boundaries;
- installed desktop launch and native capture control authority.

## Phase 1 Design

Design output is recorded in:

- `specs/036-owner-review-live-polish/data-model.md`;
- `specs/036-owner-review-live-polish/contracts/owner-review-live-proof-contract.md`;
- `specs/036-owner-review-live-polish/contracts/notes-action-truth-contract.md`;
- `specs/036-owner-review-live-polish/contracts/runtime-polish-cleanroom-contract.md`;
- `specs/036-owner-review-live-polish/contracts/readiness-claim-contract.md`;
- `specs/036-owner-review-live-polish/quickstart.md`.

## Constitution Check After Design

| Principle | Status | Design Result |
|-----------|--------|---------------|
| I. Capture-First MVP Integrity | PASS | Contracts require desktop capture controls to stay native and authoritative. |
| II. Visible Consent And User Control | PASS | Quickstart validates active, paused, resumed, and stopped control visibility from `/Applications/2brain Rec.app`. |
| III. Data Boundary And Secret Discipline | PASS | Owner proof contract forbids token/cookie/private-content evidence and requires temporary session cleanup. |
| IV. Deletion Truth And Lifecycle Accounting | PASS | Notes/action and readiness contracts preserve truthful unavailable/deferred states and deletion/governance boundaries. |
| V. Spec-Driven Delivery With Testable Gates | PASS | Checklist, tasks, analyze, GitHub issue sync, implementation, and quickstart validation remain required. |
