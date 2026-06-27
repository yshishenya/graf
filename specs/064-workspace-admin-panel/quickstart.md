# Quickstart: Workspace Admin Panel Validation

This quickstart defines the validation target for implementation. It is not a
deployment runbook.

## Preconditions

- Work from repository root.
- Use the active feature directory `specs/064-workspace-admin-panel`.
- Keep evidence metadata-only.
- Do not use real secrets, raw audio, transcript text, private meeting content,
  signed URLs, storage object keys, or local filesystem paths in committed
  fixtures, logs, screenshots, or reports.

## Seeded Fixture Shape

Implementation tests should create:

- workspace A with Owner, Admin, Member, inactive Member, and pending invite;
- workspace B with at least one user and meeting to prove isolation;
- meetings owned by different users in workspace A;
- one ready meeting with downloadable/exportable artifacts;
- one meeting with missing artifact;
- one meeting deleting/deleted;
- one meeting with post-egress audit limit;
- one meeting requiring local purge reporting;
- quota policy configured for one period and missing for another;
- usage rows or source data for minutes, storage, processing jobs, and top
  consumers;
- audit events from auth, invitations, role changes, egress, deletion, denied
  attempts, and admin views.

## Focused Test Commands

After `$speckit-tasks` creates the implementation tasks and tests, run the
focused server suite from `apps/server`:

```sh
cd apps/server
uv run --extra dev pytest -q \
  tests/unit/test_admin_permissions.py \
  tests/unit/test_admin_invitations.py \
  tests/unit/test_admin_usage_metrics.py \
  tests/unit/test_admin_audit_view_models.py \
  tests/contract/test_admin_api_contract.py \
  tests/contract/test_admin_browser_contract.py \
  tests/contract/test_admin_no_secret_content_egress.py \
  tests/contract/test_admin_rls_contract.py \
  tests/integration/test_admin_workspace_access.py \
  tests/integration/test_admin_user_management.py \
  tests/integration/test_admin_file_governance.py \
  tests/integration/test_admin_usage_metrics.py \
  tests/integration/test_admin_audit_journal.py
```

Run the focused desktop handoff policy check from repository root:

```sh
swift test --package-path apps/macos --disable-swift-testing --filter DesktopCabinetRoutePolicyTests
```

Run repository gate from root before implementation closeout or PR:

```sh
infra/scripts/ci-local.sh
```

## Scenario Checklist

### 1. Admin Overview

- Owner opens `/admin` and sees users, usage, files, metrics freshness, and
  recent audit activity for workspace A only.
- Admin opens `/admin` and sees the same overview except Owner-only actions.
- Member and unauthenticated actor are denied without admin data.
- Workspace B data never appears in workspace A admin views.

### 2. Users And Invitations

- Owner creates Member, Admin, and Owner invitations when last-owner safety is
  preserved.
- Admin can create only Member invitations.
- Duplicate active invitation for the same target is rejected.
- Expired, revoked, and already completed invites cannot be completed.
- Invite completion requires allowed provider login and matching identity.
- Admin cannot grant or revoke Owner/Admin authority.
- Last active Owner cannot be downgraded, deactivated, blocked, revoked, or
  removed.
- User detail shows role, status, devices, sessions, files, usage contribution,
  and recent audit activity.

### 3. Files And Meetings

- Owner/Admin can find a non-owned meeting in the same workspace.
- Review/download/export/delete actions succeed only after current admin and
  workspace checks.
- Cross-workspace meeting actions are denied.
- Missing artifact, active deletion, lifecycle/retention block, and post-egress
  limit show truthful unavailable states.
- Admin deletion requires destructive confirmation and a reason, then produces
  a bounded whole-meeting deletion report.
- Sensitive allowed and denied actions write metadata-only audit evidence.

### 4. Balance, Usage, And Quotas

- Displayed minutes, storage bytes, processing jobs, and top consumers reconcile
  to source-backed fixture data.
- Missing quota policy is shown as not configured.
- Configured quota policy shows risk when usage approaches or exceeds limits.
- No quota edit, billing, tariff, invoice, debt, payment, or credit controls are
  present.

### 5. Metrics And Audit

- All five metric families render with definition, denominator, date window,
  source category, freshness, and drill-down.
- Current or lagging periods are marked incomplete.
- Metrics without source-backed data are unavailable or absent, not fake.
- Audit journal filters by period, user, action, object, and outcome.
- Deleted/private objects show safe labels without private content.
- Required audit persistence failure blocks sensitive actions.

### 6. Desktop Handoff

- Desktop/embedded attempts to open admin routes do not render hidden full admin
  UI.
- Allowed actors get browser handoff; disallowed actors get access denied.
- Desktop route policy covers admin handoff/blocking without desktop header
  reinjection into embedded admin UI.

### 7. Privacy Scan

Scan rendered pages, API responses, audit records, and test evidence for banned
content:

- `storage_object_key`
- signed URL markers;
- local filesystem paths;
- tokens/secrets/passwords;
- raw audio/transcript/private meeting content.

Expected result: zero banned content in admin UI evidence, audit details, logs,
and screenshots.

## Release Notes Expectation

When implementation changes behavior, architecture, UX, QA expectations,
operations, or release readiness, update `CHANGELOG.md` under `[Unreleased]`.
No production deploy is part of this quickstart.

## Validation Evidence

Recorded on 2026-06-27 for feature `064-workspace-admin-panel`.

- Checklists: `admin-risk.md` 35/35 complete, `requirements.md` 16/16
  complete.
- Focused admin server suite: `50 passed, 1 warning`.
- Focused desktop handoff suite:
  `swift test --package-path apps/macos --disable-swift-testing --filter DesktopCabinetRoutePolicyTests`
  passed `7 tests, 0 failures`.
- Canonical local gate: `infra/scripts/ci-local.sh` completed with
  `ci_local_result=pass`.
- CI detail: server tests `883 passed, 4 skipped, 148 warnings`; server lint
  passed; Python compile passed; production compose config rendered; deployment
  evidence scan passed.

Remaining limitations:

- No production deploy or live production smoke is part of this implementation
  quickstart.
- RLS hardening validation boundary remained blocked for live/destructive
  postgres probes because no disposable postgres test database was provided in
  the local gate; table inventory, migration contract, and policy matrix tests
  passed locally.
- Admin v1 intentionally excludes support, Analyst role, billing/payment,
  quota editing, global superadmin, external audit/log platform, public meeting
  links, bulk actions, and desktop-embedded admin UI.
- Product metrics are source-backed from current server tables/rollups; missing
  sources render as unavailable or zero source-backed counts, never sample-only
  production numbers.
