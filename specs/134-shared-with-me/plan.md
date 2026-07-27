# Implementation Plan: Поделились со мной

**Branch**: `codex/shared-with-me-134` | **Date**: 2026-07-27 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/134-shared-with-me/spec.md`

## Summary

Add a separate read-only cabinet section, `Поделились со мной`, for meetings
that the authenticated user can currently open through an active recipient
grant. The section must work in the browser and embedded macOS cabinet, show
only recipient-safe metadata, and open the existing restricted shared-meeting
page.

The database already stores the authoritative grants. Add the smallest missing
capability: a dedicated, SELECT-only RLS lookup context that can enumerate a
user's active direct grants across source workspaces. Revalidate every
candidate with the existing access decision before it becomes a card.

## Technical Context

**Language/Version**: Python 3.14, Swift 6
**Primary Dependencies**: FastAPI, SQLAlchemy async, PostgreSQL RLS, Jinja,
pytest, XCTest
**Storage**: Existing PostgreSQL `meeting_share_grants` and `meetings`; no new
application table
**Testing**: pytest unit/contract/integration suites; macOS route contract test
**Target Platform**: Browser cabinet and embedded macOS cabinet
**Project Type**: Server-rendered web UI with a macOS host
**Performance Goals**: Render up to 50 active recipient cards without exposing
unrelated source-workspace records
**Constraints**: Russian UI; no source workspace, owner, calendar, service or
reshare controls; no pending invitations; no broad cross-workspace meeting
query; access is rechecked at read time
**Scale/Scope**: One cabinet list, two GET routes, one narrow RLS policy,
existing grants and shared-meeting egress reused

## Constitution Check

| Gate | Result | Evidence |
|---|---|---|
| System-audio capture boundary | Pass | No capture code changes. |
| Privacy and access boundary | Pass | RLS lookup exposes only active direct grants for the current user; existing decision revalidates each card. |
| Tenant isolation | Pass | No broad meeting RLS policy; candidate grant lookup is SELECT-only and source meeting access remains exact and authorized. |
| AI and transcript handling | Pass | No AI or transcript storage changes. |
| Clean-room UX | Pass | Reuses cabinet shell and introduces a minimal Russian recipient-only list. |
| macOS parity | Pass | Browser and `/desktop` routes share the same list data and target. |
| Release safety | Pass | No deployment is included in this feature implementation lane. |

## Project Structure

```text
apps/server/src/twobrain_rec_server/
├── cabinet/
│   ├── queries.py
│   ├── view_models.py
│   ├── web_routes/browser.py
│   ├── web_routes/desktop.py
│   └── templates/cabinet/pages/
├── db/models/meeting_access.py
├── db/tenant_context.py
└── db/migrations/
apps/server/tests/
├── contract/
├── integration/
└── unit/
apps/macos/Shared/Tests/
specs/134-shared-with-me/
```

## Implementation Approach

1. Add a `SharedWithMeLookupContext` that carries only the authenticated user
   identity. Add a migration with a `FOR SELECT` RLS policy on
   `meeting_share_grants` for this context. It permits only active, unexpired,
   direct user grants whose grantee is the context user. It creates no write
   capability and grants no access to `meetings`.
2. Add a narrowly scoped query helper that lists candidate grants under that
   context, deduplicates by meeting, then opens each source workspace only to
   run the existing recipient proof and `decide_meeting_access` check. Build a
   recipient-safe card only after that check passes.
3. Add `/shared-with-me` and `/desktop/shared-with-me`, a dedicated read-only
   template, and a `Поделились со мной` cabinet navigation item. Cards route to
   the existing `/shared-meetings/{meeting_id}?workspace_id=...` egress.
4. Extend auth-return path validation for the two exact routes. Do not widen
   the return URL allowlist.
5. Cover RLS isolation, revocation/expiry, duplicate grants, limited metadata,
   browser/embedded paths, and macOS route parity.

## Validation Plan

- `pytest apps/server/tests/unit/test_rls_tenant_context.py`
- `pytest apps/server/tests/contract/test_shared_with_me_contract.py`
- `pytest apps/server/tests/integration/test_shared_with_me.py`
- Relevant existing cabinet/shared-access tests discovered while implementing
- macOS route contract tests for the new desktop path
- `infra/scripts/ci-local.sh` before handoff

## Complexity Tracking

| Decision | Why needed | Simpler option rejected |
|---|---|---|
| Select-only recipient grant lookup context | The recipient list must span source workspaces without membership or owner data. | Reusing workspace-scoped request RLS cannot discover cross-workspace grants; a broad meeting policy would expose too much. |
