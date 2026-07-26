# Implementation Plan: Надёжное принятие invitation magic-link

**Branch**: `129-share-magic-rls`
**Date**: 2026-07-26
**Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/129-share-magic-rls/spec.md`

## Summary

Закрыть production HTTP 500 в first-entry invitation magic-link flow минимальным
изменением существующей транзакционной границы: auth-аудит должен быть flushed
под personal workspace context до перехода к source meeting workspace. Добавить
регрессионную проверку реального cross-workspace pending-row сценария, проверить
все callers общего context/rate-limit/audit пути и не расширять RLS bypass.

## Technical Context

**Language/Version**: Python 3.13

**Primary Dependencies**: FastAPI, SQLAlchemy async, PostgreSQL RLS, Jinja2
cabinet, existing session/invitation/audit helpers; no new dependency

**Storage**: Existing PostgreSQL auth, session, invitation, grant and rate-limit
tables; no schema change expected

**Testing**: pytest unit/contract/integration; isolated PostgreSQL runner;
`infra/scripts/ci-local.sh`; sanitized production smoke/log review

**Risk / Validation Lane**: `high-risk-feature` — auth, sessions, audit, RLS,
privacy-sensitive invitation access and production deployment are involved.

**Release Gate**: `cd-remote.sh --dry-run` then `--execute` after focused tests,
full local CI, release notes, rollback readiness and explicit user approval.

**Target Platform**: Production Linux Docker/PostgreSQL server and browser/
embedded server-rendered cabinet

**Project Type**: Server-rendered web service embedded in macOS product

**Performance Goals**: No additional database round trip beyond the required
flush; normal invitation acceptance remains within existing request budget.

**Constraints**: Preserve RLS/CSRF/exact-recipient/replay/deletion gates; no raw
tokens, email, audio or transcript in evidence; no new migration unless testing
proves it unavoidable; no speculative abstractions.

**Scale/Scope**: One first-entry route, shared audit/context helper callers and
their focused tests; no redesign of sharing or notification delivery.

## Constitution Check

### Pre-research gate

- Capture-first integrity: PASS; no capture path changes.
- Visible consent: PASS; invitation remains an explicit recipient action.
- Data boundary and secret discipline: PASS; no content or credential logging.
- Authorization/RLS/deletion: PASS with blocking regression; existing policies
  remain authoritative and exact recipient/revoke/expiry/deletion checks remain.
- External dependencies: PASS; notification workflow remains secondary and
  server-side.
- Spec-driven delivery: PASS; full high-risk flow, checklists, analyze,
  task-to-issue sync and implementation are required.

### Post-design gate

PASS with conditions:

1. The focused regression must fail before the fix and pass after it.
2. No policy bypass, maintenance role or broad autoflush suppression may be
   introduced.
3. Existing notification failure isolation must remain covered.
4. Full local CI and guarded production deploy must pass before release claims.

## Research summary

See [research.md](research.md). Selected approach: flush the pending audit event
while its matching personal workspace context is active. Separate session and
policy changes are rejected as larger or unsafe alternatives.

## Validation Plan

1. Requirements/security/infra checklists pass with no incomplete blockers.
2. Add the failing regression before implementation and run the focused
   PostgreSQL invitation matrix.
3. Implement the smallest context-boundary fix; inspect all callers and remove
   only proven dead/duplicate code.
4. Run focused contract/integration tests, `git diff --check`, Python compile,
   targeted Ruff and full `infra/scripts/ci-local.sh`.
5. Run Ponytail/code/security review and reconcile tasks/issues.
6. Prepare CalVer release notes, build the macOS candidate, validate signed
   update continuity and perform the update smoke.
7. Run remote dry-run, then guarded production deploy with sanitized post-deploy
   log review, backup/restore, RLS, smoke and live/ready evidence.

## Project Structure

### Documentation (this feature)

```text
specs/129-share-magic-rls/
├── spec.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── invitation-magic-link.md
├── checklists/
│   ├── requirements.md
│   ├── security.md
│   └── infra.md
└── tasks.md
```

### Source Code

```text
apps/server/src/twobrain_rec_server/cabinet/web_routes/browser.py
apps/server/src/twobrain_rec_server/cabinet/access.py
apps/server/src/twobrain_rec_server/auth/audit.py
apps/server/src/twobrain_rec_server/db/tenant_context.py
apps/server/tests/contract/test_recording_share_invitation_contract.py
apps/server/tests/contract/test_recording_share_ui_contract.py
apps/server/tests/integration/test_recording_share_public_link.py
```

**Structure Decision**: Reuse the existing server-rendered cabinet, access,
audit, tenant-context and test authorities. No new service, dependency, table,
or permission layer.

## Implementation Phases

### Phase 1 — Regression and contract boundary

- Add a test that creates an auth audit row in personal context, switches to
  source workspace context and executes the first rate-limit query; assert no
  RLS failure and correct audit ownership.
- Extend the invitation route regression to assert successful first-entry
  response and preserve existing replay/identity behavior.

### Phase 2 — Minimal implementation and cleanup

- Flush the email-login audit at the matching personal context boundary.
- Search all callers of the shared context/rate-limit/audit helpers.
- Remove only code made provably unreachable or duplicate by the regression;
  preserve the post-commit notification catch.

### Phase 3 — Validation and release

- Run focused and full CI; complete security/infra checklists and analyze.
- Commit/PR/merge the hotfix, prepare CalVer release, build and update-test the
  macOS app, then deploy exact immutable SHA with guarded rollback evidence.

## Complexity Tracking

No constitution violations. The selected fix is one existing-session flush,
not a new abstraction or policy exception.
