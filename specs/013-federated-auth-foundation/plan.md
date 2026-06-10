# Implementation Plan: Provider-Neutral Federated Authentication with RU-Local Identity & Device Sessions

**Branch**: `013-federated-auth-foundation` | **Date**: 2026-06-10 | **Spec**: `specs/013-federated-auth-foundation/spec.md`

**Input**: Feature specification from `specs/013-federated-auth-foundation/spec.md`

## Summary

Add a provider-neutral, Russian-market-ready auth foundation in `apps/server` that replaces header-only identity assumptions with stable federated identity, provider linking, workspace-scoped auth policy, and registered-device session controls. The slice stays server-only, preserves existing 012 tenant/device scope validation style, and prepares the backend to issue server-mediated session proofs for later desktop upload work.

The implementation is intentionally limited to:

- provider directory and token/state orchestration,
- internal identity + external identity persistence,
- workspace-provider policy and residency controls,
- auditability for auth and linking events,
- and no direct provider token handling in desktop clients.

## Technical Context

**Language/Version**: Python 3.13 on the existing server service.

**Primary Dependencies**:
- FastAPI, SQLAlchemy 2 async ORM, Alembic, asyncpg,
- Pydantic v2 / pydantic-settings,
- `authlib` or `httpx`-based OAuth client flows,
- `itsdangerous`-style session signing or server-side session UUID store,
- `PyJWT`/`cryptography` only if provider metadata requires server validation.

**Storage**:
- PostgreSQL for identity/auth/device/audit entities.
- Existing server-managed Redis-like in-memory cache is avoided in MVP unless needed for temporary callback state; all session truth remains in Postgres.
- No desktop-side secret storage.

**Testing**:
- `pytest`, `pytest-asyncio`, `httpx` contract tests, and existing server test harness patterns in `apps/server/tests`.
- Existing 012 migration and contract-test approach.

**Target Platform**:
- Self-hosted Linux/Docker API runtime at `apps/server`.
- Existing macOS client remains consumer of server-mediated auth and device sessions in later slices.

**Project Type**:
- Backend API service and infrastructure migration layer.

**Performance Goals**:
- Login start-to-session completion under normal network conditions within two minutes for US1.
- OAuth callback and session lookup overhead remains bounded for normal load; auth checks continue to be cheap and tenant-scoped.

**Constraints**:
- Do not introduce provider credentials or secrets in logs, diagnostics, or desktop outputs.
- Keep auth behavior fail-closed and tenant-safe with explicit deterministic failure states.
- Maintain backward compatibility for existing header-based integration endpoints while they transition to full provider sessions in later slices.

**Scale/Scope**:
- Initial MVP for enterprise-like Russian self-hosted deployments.
- Supports at least `Yandex ID`, `VK ID`, `Telegram Login`, with additional providers behind config after foundation stabilizes.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Reason |
|------|--------|--------|
| Driver-first macOS MVP | PASS | Auth foundation is server-side and does not add new local capture pathways. |
| Visible capture and one-action stop | PASS | No capture flow changes in this feature. |
| Owner-controlled storage and explicit egress policy | PASS | Auth/session/profile data residency is explicitly part of feature policy and DB writes remain server-controlled. |
| MediaScribe and Langfuse boundaries | PASS | No MediaScribe credentials or workflow calls are introduced; server remains metadata-truth-only. |
| Deletion truthfulness | PASS | New auth/device/audit entities will be traceable and participate in deletion/audit truth. |
| Security/privacy gates | PASS | Workspace policy, explicit consent, verified linking rules, and redaction are central requirements. |
| Clean-room brand-distance | PASS | Work includes backend-focused UX/API contracts; no branding changes in this slice. |

## Project Structure

### Documentation (this feature)

```text
specs/013-federated-auth-foundation/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── federated-auth-flow.md
│   ├── workspace-auth-policy.md
│   └── openapi-auth-contract.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/
└── server/
    ├── src/twobrain_rec_server/
    │   ├── auth/
    │   │   ├── context.py (existing, to be extended)
    │   │   ├── dependencies.py (existing, to be extended)
    │   │   ├── providers/
    │   │   │   ├── base.py
    │   │   │   ├── telegram.py
    │   │   │   ├── vk.py
    │   │   │   └── yandex.py
    │   │   ├── callbacks.py
    │   │   ├── sessions.py
    │   │   └── links.py
    │   ├── api/
    │   │   ├── auth.py
    │   │   └── contracts.py
    │   ├── db/models/
    │   │   ├── identity.py
    │   │   ├── auth_audit.py
    │   │   ├── workspace_auth_policy.py
    │   │   ├── external_identity.py (new or merged into identity model)
    │   │   └── auth_session.py
    │   ├── ingest/authorization.py
    │   └── observability/redaction.py (to expand redaction field coverage)
    ├── tests/
    │   ├── contract/
    │   ├── integration/
    │   └── unit/
    └── alembic revisions
```

**Structure Decision**: Keep the server as the source of truth for auth federation and policy, with new auth modules under `apps/server/src/twobrain_rec_server/auth` and dedicated API handlers in `apps/server/src/twobrain_rec_server/api/auth.py`. Reuse existing 012 ingress/dependency patterns and 012 test conventions.

## Phase 0: Research and Clarification

Resolved questions from clarifying analysis are in `research.md`.

Decisions:

- Use provider-specific adapters with a provider abstraction.
- Keep callbacks/state store in Postgres for auditability and recovery.
- Keep RU-local storage and policy flags in workspace-level entities first, with secure opt-in/out per workspace.
- Prepare adapter placeholders for future providers without implementing all flows in MVP.
- Keep desktop client unaware of provider tokens, raw claims, or secret material.

## Phase 1: Data Model, Contracts, and Validation

Design outputs:

- `data-model.md`: user/identity/session/device/audit/policy tables and transitions.
- `contracts/federated-auth-flow.md`: start/auth callback/link/revoke endpoints and failure-state matrix.
- `contracts/workspace-auth-policy.md`: workspace-scoped policy and residency constraints.
- `contracts/openapi-auth-contract.md`: explicit API contract signatures for manual or generated OpenAPI review.
- `quickstart.md`: runnable validation scenarios for local smoke and failure states.

## Post-Design Constitution Re-check

| Gate | Status | Reason |
|------|--------|--------|
| Driver-first macOS MVP | PASS | No recorder transport or local capture changes; auth readiness only. |
| Visible capture and one-action stop | PASS | No capture behavior changed. |
| Owner-controlled storage and explicit egress policy | PASS | Workspace policy and residency are explicit and server-governed. |
| MediaScribe and Langfuse boundaries | PASS | No provider secrets or content payloads exposed via this feature’s contracts. |
| Deletion truthfulness | PASS | Auth and audit entities include explicit lifecycle and deletion metadata expectations. |
| Security/privacy gates | PASS | Explicit consent, explicit linking, callback state checks, and failure recovery are core requirements. |
| Clean-room UX | PASS | No brand-level front-end scope in this server slice; UI copy is limited to server-visible contract language and policy text for future client implementation. |

No constitution violations are introduced by this design.

## Product Acceptance Metrics for 013

- 100% of valid provider start/callback/linking flows result in a stable `InternalUser` and workspace-scoped session.
- 100% of disabled providers hidden per workspace policy.
- 0 occurrences of provider tokens/claims in structured logs and API response secrets.
- 100% of callback/revoke/conflict failures produce deterministic outcomes and audit events.
- 100% of RU-local workspace writes constrained to RU policy fields once policy is enabled.

## Story Slice Map

| Story | Implementation slice |
|-------|----------------------|
| US1 One-click auth in Russian workspace | Provider onboarding start, callback handling, workspace-scoped session issuance, failure state mapping. |
| US2 Duplicate identity merge behavior | Explicit linking + deterministic verified-link candidate flow + conflict handling. |
| US3 Device registration and continuity | Device model extension for registration policy, revoke/rebind lifecycle, upload-scoped server sessions. |
| US4 Workspace policy and residency | Workspace-level provider allowlist and RU-local boundary enforcement + admin-visible outcomes. |
| US5 Failure and recovery visibility | Deterministic auth state machine, explicit errors, retry guidance. |
| US6 Privacy and audit transparency | Consent copy model, audit event model, redaction and evidence checks. |
