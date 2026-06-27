# Implementation Plan: Workspace Admin Panel

**Branch**: `codex/064-workspace-admin-panel` | **Date**: 2026-06-27 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/064-workspace-admin-panel/spec.md`

## Summary

Build a browser-owned workspace admin panel for active Owners and Admins to
manage workspace users, monitor read-only quota/usage balance, govern
server-known user files/meetings, inspect source-backed product metrics, and use
one metadata-only product audit journal. The implementation should be a separate
server admin module, not another growth path inside `cabinet/web.py`; it should
reuse existing auth, workspace membership, cabinet egress, deletion lifecycle,
RLS, and metadata-only audit patterns.

V1 deliberately excludes support/break-glass workflows, Analyst role, billing,
external audit/log platform integration, public meeting links, external
meeting-recipient invitations, quota editing, bulk actions, and desktop-embedded
admin UI.

## Technical Context

**Language/Version**: Python >=3.13 for the server package in `apps/server`.

**Primary Dependencies**: FastAPI, SQLAlchemy asyncio, Alembic, Jinja2, existing
server-rendered cabinet/HTMX-style patterns, pytest/pytest-asyncio, Ruff.

**Storage**: PostgreSQL for identities, memberships, invitations, usage rollups,
quota display policy, admin audit events, and RLS-covered tenant data. MinIO
remains the artifact store behind existing cabinet/deletion egress services; the
admin UI must not expose storage object keys, signed URLs, or local paths.

**Testing**: Pytest unit, contract, and integration tests under
`apps/server/tests`, plus RLS and no-secret/no-content egress contracts, and one
focused macOS route-policy check for desktop admin handoff. The feature
quickstart defines the focused suite; closeout requires `infra/scripts/ci-local.sh`.

**Risk / Validation Lane**: High-risk product area. This feature touches admin
UX, auth, role changes, invitations, privacy, file access, egress, deletion,
audit, Postgres/RLS, and metrics truth. It must keep the full Spec Kit sequence:
clarify, plan, checklist, tasks, analyze, task-to-issues, then implement.

**Release Gate**: No deployment during planning. Implementation closeout must
run the feature quickstart and `infra/scripts/ci-local.sh`. Production deploy or
smoke requires a later release/deploy lane with explicit approval and
`infra/scripts/cd-remote.sh --dry-run` before any execute step.

**Target Platform**: Server-owned browser web surface for `2brain Rec`.
Desktop clients may hand off to browser routes or show access-denied/handoff
states, but v1 must not embed the full admin UI in the native recorder.

**Project Type**: Web service with server-rendered admin pages and JSON/action
routes. No standalone frontend application.

**Performance Goals**: Admin lists must use bounded pagination/filtering and
must not perform unbounded workspace-wide scans in request handlers. Usage and
metric views must use bounded date windows or stored rollups. List endpoints
should cap page size at 100 records unless a later task justifies a smaller
limit for a specific page.

**Constraints**:

- Enforce workspace and role checks at page render time and again at action
  submission time.
- Fail closed when required audit evidence for a sensitive action cannot be
  persisted.
- Keep admin audit, logs, screenshots, and validation evidence metadata-only.
- Do not expose raw audio, transcript text, private meeting content, storage
  identifiers, signed URLs, local paths, tokens, or secrets.
- Admin file access does not bypass missing artifacts, active deletion,
  retention/lifecycle blocks, post-egress limits, or other unavailable states.
- Balance/limits are read-only monitoring in v1; no quota editing or billing.
- Use Russian-first user-facing labels and deletion copy that does not promise
  erasure outside `2brain Rec` control.

**Scale/Scope**: One workspace-scoped admin surface with five areas:
overview, users/invitations, files/meetings, balance/usage/quotas, and
metrics/audit. Roles are exactly Owner, Admin, and Member for v1.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Before Phase 0 Research

PASS. The feature is high-risk because it touches admin, auth, privacy,
Postgres/RLS, deletion, egress, and audit. The spec has completed clarify
questions and a requirements checklist with no remaining clarification markers.
No constitution amendment is required.

Applicable gates:

- Capture-first integrity: not directly changing capture. The admin panel must
  not add hidden capture controls or desktop-embedded admin policy changes.
- Visible consent and user control: preserved by keeping admin in browser and
  not adding recording controls that can hide active capture.
- Data boundary and secret discipline: preserved by metadata-only audit/log
  requirements and no external audit/log platform integration in v1.
- Deletion truth: preserved by whole-meeting deletion copy, required reason,
  bounded reports, and no partial artifact deletion.
- Spec-driven delivery: full high-risk Spec Kit lane is selected.

### After Phase 1 Design

PASS. `research.md`, `data-model.md`, `contracts/`, and `quickstart.md` keep
the admin surface separate from `cabinet/web.py`, preserve existing cabinet
egress and deletion services, define metadata-only audit persistence, and leave
support, billing, external log export, quota editing, bulk actions, and desktop
admin UI out of scope. No complexity exception is required.

## Validation Plan

Planning validation:

- Check this feature directory for placeholders and unresolved clarification
  markers.
- Check markdown paths and the root `AGENTS.md` Spec Kit plan reference.
- Run `git diff --check` for `specs/064-workspace-admin-panel` and `AGENTS.md`.

Implementation validation to be generated by `$speckit-tasks`:

- Unit tests for admin permission decisions, Owner/Admin/Member role authority,
  last-owner protection, invitation state transitions, read-only quota labels,
  metric definitions, and audit redaction.
- Contract tests for `/admin` browser routes and `/api/v1/admin/*` JSON/action
  routes, including 401/403/404/409/503 problem states.
- Desktop route-policy tests proving admin routes hand off to the browser or
  stay blocked instead of embedding the full admin UI.
- Integration tests for workspace isolation, invitation completion through an
  allowed provider, admin file review/download/export/deletion, lifecycle
  unavailable states, audit fail-closed behavior, and usage/metrics
  reconciliation.
- RLS and no-secret/no-content egress tests for new admin tables, admin pages,
  API responses, audit details, and validation evidence.
- Accessibility and compact-width checks for admin tables, filters, destructive
  confirmation, keyboard navigation, and Russian-first labels.

Repository gate before implementation closeout or PR:

```sh
infra/scripts/ci-local.sh
```

Deploy gate:

- Not required for planning or implementation-only local closeout.
- A later release/deploy slice must run `infra/scripts/cd-remote.sh --dry-run`
  and execute only after explicit release approval.

## Project Structure

### Documentation (this feature)

```text
specs/064-workspace-admin-panel/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   |-- admin-api-contract.md
|   `-- admin-ui-contract.md
|-- checklists/
|   `-- requirements.md
`-- tasks.md
```

`tasks.md` is not created by this plan step; it is the next Spec Kit artifact.

### Source Code (repository root)

```text
apps/server/src/twobrain_rec_server/
|-- admin/
|   |-- __init__.py
|   |-- audit.py
|   |-- files.py
|   |-- invitations.py
|   |-- metrics.py
|   |-- permissions.py
|   |-- queries.py
|   |-- templates.py
|   |-- usage.py
|   |-- view_models.py
|   |-- web.py
|   |-- templates/admin/
|   `-- static/admin/
|-- api/
|   `-- admin.py
|-- db/
|   |-- models/
|   |   |-- admin.py
|   |   `-- identity.py
|   `-- migrations/versions/
|-- main.py
|-- cabinet/
|-- deletion/
`-- auth/

apps/server/tests/
|-- unit/
|   |-- test_admin_permissions.py
|   |-- test_admin_invitations.py
|   |-- test_admin_usage_metrics.py
|   `-- test_admin_audit_view_models.py
|-- contract/
|   |-- test_admin_api_contract.py
|   |-- test_admin_browser_contract.py
|   |-- test_admin_no_secret_content_egress.py
|   `-- test_admin_rls_contract.py
`-- integration/
    |-- test_admin_workspace_access.py
    |-- test_admin_user_management.py
    |-- test_admin_file_governance.py
    |-- test_admin_usage_metrics.py
    `-- test_admin_audit_journal.py

apps/macos/
|-- RecApp/Sources/Cabinet/DesktopCabinetRoutePolicy.swift
`-- Shared/Tests/DesktopCabinetRoutePolicyTests.swift
```

**Structure Decision**: Add a dedicated `twobrain_rec_server.admin` package and
`twobrain_rec_server.api.admin` router. Reuse cabinet/deletion/auth modules at
their service boundaries, but do not add the admin control room to
`cabinet/web.py`. Add models/migrations only for gaps that do not exist today:
workspace invitations, read-only quota display policy, usage rollups, and admin
audit events. Do not add a separate frontend app.

## Complexity Tracking

No constitution violations or complexity exceptions are planned.
