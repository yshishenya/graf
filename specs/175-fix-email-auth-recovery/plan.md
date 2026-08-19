# Implementation Plan: Надёжный вход по email и восстановление аккаунта

**Branch**: `codex/175-fix-email-auth-recovery` | **Date**: 2026-08-19 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/175-fix-email-auth-recovery/spec.md`

## Summary

Устранить production HTTP 500 после корректного email-кода, вернуть действия
Яндекс ID/VK на экране неоднозначного email и исправить классификацию
authenticated linking. Реализация повторно использует существующие
`AuthCallbackLookupContext`, `WorkspaceAuthContext` и account-merge Feature 157.
Endpoint владеет единственным commit: изменения текущего tenant-контекста сначала
flush-ятся, затем callback/link state завершается в его узкой разрешённой
области, а response готовится до commit. Любой другой аккаунт всегда проходит
через preview и явное подтверждение. Новая модель, миграция, provider или
зависимость не нужны.

## Technical Context

**Language/Version**: Python 3.13+

**Primary Dependencies**: FastAPI, SQLAlchemy 2 async, PostgreSQL 17, Jinja templates

**Storage**: Existing PostgreSQL tables with forced RLS; no schema change

**Testing**: pytest 9, FastAPI TestClient, disposable PostgreSQL app-role/RLS harness

**Risk / Validation Lane**: `high-risk-feature` — auth, sessions, account linking, tenant isolation and production incident

**Release Gate**: focused + quickstart + `ci-local.sh --fast` before PR; production requires separate `cd-remote.sh --dry-run` and explicit approval before `--execute`

**Target Platform**: Linux server; shared server-rendered web and embedded macOS WebView surfaces

**Project Type**: FastAPI web service with server-rendered auth UI

**Performance Goals**: No additional network round trip in the normal email-code path; bounded candidate lookup remains organization-scoped

**Constraints**: Preserve forced RLS, CSRF, OAuth state/nonce, single-use codes, first-party redirect allowlist and transaction rollback; never mutate real production accounts during validation

**Scale/Scope**: Three production-visible auth journeys and their shared sibling provider-link completion path; no broader login redesign

## Constitution Check

*GATE: Passed before Phase 0 research; re-checked after Phase 1 design.*

- **Spec-driven delivery**: PASS — successor spec 175, mandatory clarify,
  security/UX checklists, tasks, analyze and issue sync precede implementation.
- **Tenant/privacy boundary**: PASS — existing narrow RLS contexts are reused;
  no maintenance role, RLS bypass or broader policy is introduced.
- **User control and data safety**: PASS — ambiguous accounts remain fail-closed;
  no real account is merged automatically and every one-other-account flow stops
  at explicit preview, включая пустой duplicate.
- **Secret/evidence discipline**: PASS — synthetic addresses only; no codes,
  tokens, account identifiers or meeting content in committed artifacts.
- **Surface parity/accessibility**: PASS — one server contract covers web and
  embedded routes; configured provider actions remain keyboard-accessible links.
- **Release integrity**: PASS — this server-only hotfix does not alter macOS
  artifacts; production execution remains a separately approved exact-SHA gate.
- **Post-design re-check**: PASS — no schema, dependency, external egress or
  constitution exception was added by the design.

## Validation Plan

1. Add focused route/integration checks for successful/failed/expired email
   login, replay, rollback, early/late recovery provider actions, embedded route
   parity, preview content and 0/1/>1 linking candidates.
2. Add disposable PostgreSQL app-role regression(s) that run under forced RLS
   and reproduce the former callback/link-state `StaleDataError` boundaries.
3. Run the feature quickstart selectors through
   `apps/server/scripts/run_local_postgres_tests.sh` so owner-role success cannot
   hide RLS failures.
4. Run focused Ruff/compile checks for touched server files.
5. Run `infra/scripts/ci-local.sh --fast` once after implementation/review, not
   after each edit.
6. Before production, prepare the CalVer hotfix candidate, run
   `cd-remote.sh --dry-run`, obtain explicit approval, then let `--execute` run
   the mandatory full exact-SHA gate and production smoke.

## Project Structure

### Documentation (this feature)

```text
specs/175-fix-email-auth-recovery/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── email-auth-recovery.md
├── checklists/
│   ├── requirements.md
│   ├── security.md
│   └── ux.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/src/twobrain_rec_server/
├── cabinet/web_routes/auth.py
├── cabinet/web_routes/auth_email_flow.py
└── auth/provider_links.py

apps/server/tests/
├── integration/test_web_owner_session_context.py
├── integration/test_account_merge.py
├── integration/test_rls_postgres_policies.py
└── contract/test_auth_contracts.py
```

**Structure Decision**: Patch the three existing shared auth owners and extend
their current test modules. Do not add a second auth service, migration or UI
component.

## Complexity Tracking

No constitution violations or justified complexity exceptions.
