# Implementation Plan: Safe Browser Login Returns and Callback Diagnostics

**Branch**: `107-auth-return-safety` | **Date**: 2026-07-17 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/107-auth-return-safety/spec.md`

## Summary

Resolve a browser sign-in return only after the new authenticated session exists.
For a meeting-detail return, reuse the existing meeting access policy under the
new session's RLS request context: retain an authorized deep link and otherwise
send the user to the corresponding regular or embedded meeting list.  Keep the
pre-auth local-path sanitizer and provider-link callback behavior unchanged.

Use the server-side callback state as the sole source of the email return
candidate, so a form resubmission cannot alter it.  Replace the raw browser
detail 404 with a route-local neutral cabinet page, preserving the existing
JSON contract for API and HTMX/fragment calls.  Stop Uvicorn's query-bearing
access log and restrict application request events to an explicit metadata
allowlist.

## Technical Context

**Language/Version**: Python 3.13 with FastAPI and async SQLAlchemy; Jinja cabinet templates; Docker/Uvicorn runtime

**Primary Dependencies**: FastAPI, SQLAlchemy async, Pydantic, Jinja, Uvicorn; no new dependency

**Storage**: Existing PostgreSQL identity, callback-state, session, meeting, membership, and share-grant records; no schema migration or new persisted data

**Testing**: pytest focused browser/auth/RLS/template/logging tests; a real Uvicorn subprocess log regression; canonical `infra/scripts/ci-local.sh` at closeout

**Risk / Validation Lane**: High-risk feature. It changes authentication return handling, RLS-scoped access evaluation, privacy-preserving unavailable UX, runtime diagnostics, and Docker server launch behavior.

**Release Gate**: No deploy, release preparation, tag, or production cleanup. The user is completing parallel work and has explicitly kept the release gate closed.

**Target Platform**: Linux Docker server, regular browser cabinet, and macOS embedded WebView cabinet (server-rendered behavior only)

**Project Type**: Self-hosted web service with a server-rendered cabinet and a native macOS client consuming its embedded surface

**Performance Goals**: One bounded meeting/access lookup only for an exact browser detail return; no transcript, media, or full review loading in callback processing; existing list/detail response behavior otherwise unchanged

**Constraints**: Preserve callback state binding, expiry, single-use, and browser nonce checks; fail closed without revealing meeting existence; emit metadata-only request diagnostics; retain API and HTMX error contracts; do not alter access policy, capture, client permissions, dependencies, or database schema

**Scale/Scope**: One shared post-sign-in resolver across supported external and email browser flows; two cabinet surfaces; one Docker API command; no production operation in this slice

## Constitution Check

*GATE: Passed before Phase 0 research and re-checked after Phase 1 design.*

- **Capture-First MVP Integrity — PASS / not affected**: no capture, audio routing, native permission, or client recording behavior changes.
- **Visible Consent And User Control — PASS / not affected**: no capture UI or consent state changes.
- **Data Boundary And Secret Discipline — PASS**: the design removes raw callback-query output from Uvicorn logs and removes arbitrary request headers from structured request events. It adds no egress, credential, token, transcript, media, or content storage.
- **Deletion Truth And Lifecycle Accounting — PASS / not content-bearing**: no meeting artifact, retention, or deletion behavior changes.
- **Spec-Driven Delivery With Testable Gates — PASS**: high-risk clarify, planning, security/UX/infra checklists, tasks, analyze, issue synchronization, focused validation, and canonical local CI are required before closeout.
- **Privacy And Access — PASS**: the resolver uses the existing `decide_meeting_access` authority under an explicit authenticated RLS request context. Missing, deleted, malformed, and denied details converge to neutral responses; no access policy is broadened.
- **Deployment Boundary — PASS**: the Dockerfile change is validated locally but is neither built nor deployed to production in this user-closed release lane.
- **Post-design re-check — PASS**: the plan introduces no new persistent model or external dependency, keeps provider-link callbacks isolated, and limits the new resolver to browser meeting-detail returns.

## Validation Plan

1. Add tests before or alongside each behavior change: exact authorized and denied browser return paths for regular and embedded surfaces; external-provider browser state/replay preservation; email login and registration state-bound return behavior; and a focused RLS resolver path.
2. Test direct unavailable browser and embedded detail pages for missing, denied, and malformed identifiers. Verify their bodies are neutral, use the matching list link, and do not expose the problem code, identifiers, titles, transcript text, or private fields. Retain the HTMX/API 404 contract.
3. Test the cabinet renderer shell and the structured logging event schema. Start the real application through Uvicorn with synthetic query/header/cookie markers and assert the process output contains metadata (`request.end`, templated path, status, duration) but none of the markers.
4. Assert the production Docker runtime command includes `--no-access-log`; run the focused server suite specified in `quickstart.md` while implementing.
5. Run `infra/scripts/ci-local.sh` before feature closeout or any PR. Do not run `cd-remote.sh`, build a production image, deploy, tag, publish a GitHub Release, or perform production log rotation/deletion in this slice.

## Project Structure

### Documentation (this feature)

```text
specs/107-auth-return-safety/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── browser-auth-return.md
├── checklists/
└── tasks.md
```

### Source Code (repository root)
```text
apps/server/src/twobrain_rec_server/
├── api/auth.py
├── auth/callbacks.py
├── cabinet/
│   ├── access.py
│   ├── auth_return.py
│   ├── rendering.py
│   ├── templates/cabinet/pages/meeting_unavailable_content.html
│   └── web_routes/
│       ├── auth.py
│       ├── auth_email_flow.py
│       ├── browser.py
│       └── desktop.py
└── observability/logging.py

apps/server/tests/
├── integration/
│   ├── test_cabinet_web_access_states.py
│   ├── test_compose_hardening.py
│   ├── test_runtime_request_logging.py
│   ├── test_web_owner_session_context.py
│   └── test_rls_postgres_policies.py
└── unit/
    ├── test_cabinet_web_shell.py
    └── test_structured_logging.py

infra/server/Dockerfile
AGENTS.md
CHANGELOG.md
```

**Structure Decision**: Reuse the existing FastAPI auth, cabinet access, RLS, template, and logging surfaces. Add one narrowly scoped server-side return resolver and one unavailable-page template; do not add a client router, database migration, provider-specific implementation, logging sink, background service, or dependency.

## Complexity Tracking

No constitution violations or justified exceptions.
