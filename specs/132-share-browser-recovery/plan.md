# Implementation Plan: Понятное состояние приглашения в браузере

**Branch**: `132-share-browser-recovery`
**Date**: 2026-07-26
**Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/132-share-browser-recovery/spec.md`

## Summary

Сохранить одноразовую auth-защиту invitation flow, но разделить browser- и
API-ответы на границе Problem Details. Повторный или недоступный browser
continuation будет получать существующую безопасную страницу GRAF с понятным
сообщением, а API-клиент с JSON `Accept` сохранит текущую схему. Явный
HTML-переход из письма на защищённую страницу без сессии сохранит существующий
вход; generic/missing `Accept` специальным образом обрабатывается только на
одноразовом invitation continuation, чтобы не менять общий `/meetings` API-
контракт.

## Technical Context

**Language/Version**: Python 3.13

**Primary Dependencies**: FastAPI, Starlette responses, SQLAlchemy async,
Jinja2 server-rendered cabinet; no new dependency

**Storage**: Existing PostgreSQL invitation, continuation, auth-session and
grant records; no schema change

**Testing**: pytest unit/contract/integration, existing local PostgreSQL
runner, `infra/scripts/ci-local.sh`, metadata-only production log review

**Risk / Validation Lane**: `high-risk-feature` — auth/session/recipient
boundaries and unavailable/degraded browser UX are involved; mandatory clarify,
security and UX checklists, tasks-to-issues, analyze, focused tests and full
repository gate apply

**Release Gate**: `cd-remote.sh --dry-run`; production execute only after
validation, release evidence and explicit release approval

**Target Platform**: Production Linux Docker server and server-rendered browser
cabinet used by the macOS product

**Project Type**: Server-rendered web service

**Performance Goals**: Error presentation adds no database query and keeps the
existing request path within its current latency budget

**Constraints**: Preserve RLS, exact recipient, CSRF, session, grant,
expiry/revoke and replay protections; preserve API Problem Details; do not put
tokens, email addresses, meeting content, audio or stack traces in HTML or
evidence; no migration or new dependency

**Scale/Scope**: Invitation browser exception handling, protected browser
navigation from email, one existing cabinet error surface and focused auth/
sharing tests; no redesign of email delivery

## Constitution Check

### Pre-research gate

- Capture-first integrity: PASS; no capture path changes.
- Visible consent and user control: PASS; invitation remains recipient-bound
  and explicit; no recording behavior changes.
- Plaintext observability and secret discipline: PASS; only metadata-level
  response and log behavior changes; no secrets or meeting content added.
- Authorization/RLS/deletion truth: PASS conditionally; one-time, recipient,
  CSRF, session, grant, expiry, revoke and RLS checks remain authoritative.
- External dependencies: PASS; no new egress, dependency or workflow.
- Spec-driven delivery: PASS; this is a high-risk auth and unavailable-state
  UX slice with required checklists, analyze, issue sync and repository gate.

### Post-design gate

PASS with conditions:

1. Browser replay/invalid responses must be HTML while explicit JSON requests
   remain Problem Details JSON.
2. The error page must not expose the token, continuation state, recipient
   address, meeting content or stack trace.
3. The focused first-entry and replay matrix must preserve the existing
   successful result and no-side-effect guarantees.
4. Full local CI must pass before PR; production deploy requires a separate
   release gate and approval.

## Research Summary

See [research.md](research.md). The selected approach reuses the existing
server-rendered cabinet and unavailable-state pattern, adds one invitation-safe
HTML error surface, and narrows response negotiation at the global problem
handler without changing invitation state transitions.

## Validation Plan

1. Complete the requirements, security and UX checklists; no infra checklist is
   needed because this slice changes no deployment topology, secret or schema.
2. Add contract and integration regressions for browser replay/expiry, missing
   or general `Accept` on invitation paths, explicit JSON, successful first
   entry and no side effects.
3. Implement the smallest shared browser-response change and reuse existing
   cabinet rendering conventions.
4. Run focused invitation tests, `git diff --check`, Python compile and
   targeted Ruff.
5. Run `infra/scripts/ci-local.sh` at closeout; record metadata-only evidence
   and reconcile tasks/issues.
6. If released, run the CD dry-run and the guarded production smoke/log review
   only after explicit release approval.

## Project Structure

### Documentation (this feature)

```text
specs/132-share-browser-recovery/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── browser-invitation-errors.md
├── checklists/
│   ├── requirements.md
│   ├── security.md
│   └── ux.md
└── tasks.md
```

### Source Code

```text
apps/server/src/twobrain_rec_server/api/problems.py
apps/server/src/twobrain_rec_server/cabinet/rendering.py
apps/server/src/twobrain_rec_server/cabinet/templates.py
apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/share_invitation_content.html
apps/server/tests/contract/test_browser_problem_responses.py
apps/server/tests/contract/test_recording_share_invitation_contract.py
apps/server/tests/integration/test_recording_share_public_link.py
```

**Structure Decision**: Reuse the existing ProblemDetail handler, cabinet
template shell, existing invitation unavailable branch and invitation test
fixtures. Add only the smallest renderer/helper and focused tests; do not
create a new service, error framework, data table or dependency.

## Complexity Tracking

No constitution violations. No complexity exception is required.
