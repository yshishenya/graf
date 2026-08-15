# Implementation Plan: Remove Workspace Legacy

**Branch**: `codex/150-remove-workspace-legacy` | **Date**: 2026-08-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/150-remove-workspace-legacy/spec.md`

## Summary

Удалить поддержку pre-097 bootstrap memberships и сделать configured login workspace строго внутренним auth anchor. Anchor остаётся для policy/callback/RLS lookup, но callback, tenant session, selector и self-serve billing не могут считать его customer workspace. Новый или повторно вошедший пользователь получает один personal workspace; corporate membership остаётся только для явного enrollment. Старый report-only migration CLI и его проверки удаляются.

## Technical Context

**Language/Version**: Python 3.12; Jinja2 templates

**Primary Dependencies**: FastAPI, SQLAlchemy 2 async, Pydantic Settings, Alembic; существующие auth/workspace helpers

**Storage**: PostgreSQL с forced RLS; существующие identity/workspace/session/billing tables

**Testing**: pytest unit/contract/integration, disposable PostgreSQL RLS suite, repository fast gate

**Risk / Validation Lane**: high-risk-feature — auth, tenant selection, session scope и billing boundary

**Release Gate**: no deploy; production cleanup/deploy только после backup, zero-data inventory, CD dry-run и отдельного подтверждения

**Target Platform**: Linux server/web cabinet; browser and embedded desktop cabinet consumers

**Project Type**: FastAPI web service with server-rendered cabinet

**Performance Goals**: не добавлять сетевые вызовы или background jobs; сохранить bounded query count текущих login/list flows

**Constraints**: fail closed для internal workspace; metadata-only evidence; без новых dependencies; unrelated legacy contracts вне scope

**Scale/Scope**: auth callback/email flow, shared tenant validation, workspace selector/activation, self-serve billing guard, test fixtures, obsolete CLI/docs

## Constitution Check

### Before Phase 0

- Capture-first / visible consent: pass; capture code не меняется.
- Data boundary / secrets: pass; egress не добавляется, evidence metadata-only.
- Deletion truth: pass; cleanup останавливается при customer-owned rows и не переносит данные.
- Spec-driven delivery: pass; high-risk lane с clarify, security/UX checklist, analyze и quickstart.
- Tenant isolation: pass with validation; internal anchor исключается в shared authorization до membership/device checks.

### After Phase 1

- Контракт отделяет internal auth anchor от personal/corporate customer workspaces.
- `auth_bootstrap` RLS context сохраняется только как технический trust boundary.
- Новых таблиц, зависимостей и внешних интерфейсов нет.
- Destructive cleanup не автоматизирован в runtime и остаётся gated operator action.

## Validation Plan

1. Focused unit/contract tests для personal idempotency, email/provider callback selection, workspace list/activation, shared tenant rejection, UI naming и personal-only billing.
2. Focused PostgreSQL/RLS suite после удаления report CLI assertions.
3. Feature quickstart: fresh signup twice and concurrently, stale internal membership negative fixture, explicit corporate offer, revoked corporate fallback, billing personal-only.
4. `infra/scripts/ci-local.sh --fast` перед handoff/PR.
5. Full CI и CD dry-run только перед утверждённым release/deploy.

## Project Structure

### Documentation (this feature)

```text
specs/150-remove-workspace-legacy/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── contracts/workspace-auth-boundary.md
├── checklists/
├── quickstart.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/src/twobrain_rec_server/
├── auth/{callbacks.py,dependencies.py,policy.py,workspace_onboarding.py}
├── cabinet/web_routes/{auth.py,auth_email_flow.py,settings.py,spaces.py}
└── cabinet/templates/cabinet/pages/settings_workspace_content.html

apps/server/tests/
├── conftest.py
├── fakes/auth_contexts.py
├── unit/test_workspace_onboarding.py
├── contract/{test_auth_contracts.py,test_provider_link_settings_contract.py}
└── integration/{test_tenant_authorization.py,test_rls_postgres_policies.py}
```

**Structure Decision**: Переиспользовать существующие auth/workspace services и shared tenant dependency. Удалить obsolete CLI, не заменяя его постоянным migration layer.

## Complexity Tracking

No constitution violations or extra abstractions are required.
