# Implementation Plan: Cabinet Login Polish

**Branch**: `codex/070-cabinet-login-polish` | **Date**: 2026-06-28 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/070-cabinet-login-polish/spec.md`

## Summary

Polish the shared cabinet auth layout and remove the app-only provider-login blocker by reusing the existing server-owned auth pages, the existing code form, and the desktop route policy. No new provider backend, database state, or credential handling is needed.

## Technical Context

**Language/Version**: Python 3.12 server templates/tests, JavaScript/CSS static assets, Swift 6 macOS package

**Primary Dependencies**: FastAPI/Jinja server cabinet, existing vanilla JS/CSS assets, WebKit route policy in `TwoBrainRecAppCore`, XCTest/pytest

**Storage**: Existing auth/session storage only; no schema changes

**Testing**: `uv run --extra dev pytest -q ...`, `swift test --package-path apps/macos --filter ...`

**Risk / Validation Lane**: high-risk-feature, because the slice touches auth recovery, desktop embedded navigation policy, and user-facing login UX

**Release Gate**: no deploy; local focused validation plus repository gate before PR/closeout

**Target Platform**: Web cabinet and macOS embedded cabinet

**Project Type**: server-rendered web UI plus desktop app shell

**Performance Goals**: Code auto-submit runs on existing input/paste events with no polling or extra network calls beyond the existing form submit.

**Constraints**: Preserve fail-closed external navigation, do not leak secrets/tokens, do not attach desktop headers to provider domains, keep email fallback visible.

**Scale/Scope**: Three shared auth pages and one desktop route-policy class.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Capture-first MVP integrity: not touched.
- Visible consent and user control: not touched.
- Data boundary and secret discipline: pass; no provider secrets or tokens are added to client state, docs, logs, or tests.
- Deletion truth: not touched.
- Spec-driven delivery with testable gates: pass; this plan records high-risk lane, focused tests, quickstart, tasks, and analyze.

Post-design check: pass. The design reuses existing auth routes/assets and adds only a provider-origin policy exception required for the current login flow.

## Validation Plan

Focused checks:

- `cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/integration/test_web_owner_session_context.py`
- `swift test --package-path apps/macos --filter DesktopCabinetRoutePolicyTests`

Repository gate before PR/closeout:

- `infra/scripts/ci-local.sh`

No deploy gate is required because this slice does not release to production in this turn.

## Project Structure

### Documentation (this feature)

```text
specs/070-cabinet-login-polish/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── auth-login-polish-contract.md
├── checklists/
│   ├── requirements.md
│   ├── security.md
│   └── ux.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/src/twobrain_rec_server/cabinet/static/cabinet/
├── cabinet.css
└── cabinet.js

apps/server/tests/integration/
└── test_web_owner_session_context.py

apps/macos/RecApp/Sources/Cabinet/
└── DesktopCabinetRoutePolicy.swift

apps/macos/Shared/Tests/
└── DesktopCabinetRoutePolicyTests.swift
```

**Structure Decision**: Reuse the existing server-owned auth templates and desktop route policy. No new package, abstraction, or dependency.

## Complexity Tracking

No constitution violations.
