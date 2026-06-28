# Implementation Plan: VK ID Web Login

**Branch**: `codex/066-vk-id-web-login` | **Date**: 2026-06-27 | **Spec**: `specs/066-vk-id-web-login/spec.md`

**Input**: Feature specification from `specs/066-vk-id-web-login/spec.md`

## Summary

Enable VK ID as a real browser web-cabinet login/sign-up entrypoint by reusing the 013 provider backend, replacing the current disabled stub with a provider start redirect, selecting the VK client ID for VK redirects, and wiring the production VK secret as a server-only Docker secret.

## Technical Context

**Language/Version**: Python 3.13 in `apps/server`.

**Primary Dependencies**: Existing FastAPI, SQLAlchemy async ORM, Pydantic settings, Docker Compose, and 013 auth provider/session modules. No new dependencies.

**Storage**: Existing 013 auth tables only; no migration.

**Testing**: Existing pytest server contract/integration/unit harness.

**Risk / Validation Lane**: High-risk product area / active Spec Kit slice. Auth, secrets, browser sessions, and production Docker secret wiring require full Spec Kit artifacts, focused tests, repository gate, and deploy gate if released.

**Release Gate**: Production deploy is blocked until VK client ID and secret are provisioned on the server. Once provisioned, run `infra/scripts/cd-remote.sh --dry-run` and `infra/scripts/cd-remote.sh --execute` only after release approval.

**Target Platform**: Browser web cabinet served by the Linux/Docker server.

**Project Type**: Backend-rendered web/API service.

**Performance Goals**: Provider start remains a single DB-backed state creation plus redirect; no user-visible delay beyond normal provider navigation.

**Constraints**:
- Do not log or render raw provider secrets, codes, tokens, claims, emails, phones, or live secret paths.
- Do not add a new OAuth library, provider abstraction, database migration, or desktop OAuth flow.
- Preserve email login fallback.
- Preserve existing 013 provider verification and callback state behavior.
- Deploy must fail closed if the configured VK secret file is missing or empty.

**Scale/Scope**: One visible provider surface: VK ID in browser login/sign-up.

## Constitution Check

| Gate | Status | Reason |
|------|--------|--------|
| Capture-first MVP integrity | PASS | No capture, recording, driver, or routing behavior changes. |
| Visible consent and user control | PASS | No capture behavior changes; auth consent remains provider/browser controlled plus existing RU copy. |
| Data boundary and secret discipline | PASS | Reuses server-side provider verification and forbids secret/token/client exposure. VK secret stays server-only. |
| Deletion truth and lifecycle accounting | PASS | No new data stores; existing auth audit/session entities remain accountable. |
| Spec-driven delivery with testable gates | PASS | Slice has spec, clarify decision, plan, checklists, tasks, analyze, and focused tests. |
| Product/platform constraints | PASS | Server/web-only; no new platform support claims. |

## Validation Plan

- Focused tests:
  - `PYTHONPATH=apps/server/src pytest -q apps/server/tests/integration/test_web_owner_session_context.py`
  - `PYTHONPATH=apps/server/src pytest -q apps/server/tests/contract/test_auth_contracts.py`
  - `PYTHONPATH=apps/server/src pytest -q apps/server/tests/unit/test_config_validation.py`
- Repository gate before closeout because auth and Docker secret behavior changed:
  - `infra/scripts/ci-local.sh`
- Deploy gate:
  - `infra/scripts/cd-remote.sh --dry-run`
  - `infra/scripts/cd-remote.sh --execute` only after VK credentials are configured and release is approved.

## Project Structure

### Documentation (this feature)

```text
specs/066-vk-id-web-login/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── browser-vk-login.md
│   └── vk-production-secret.md
├── checklists/
│   ├── requirements.md
│   ├── security.md
│   ├── infra.md
│   └── ux.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/src/twobrain_rec_server/
├── cabinet/rendering.py
├── cabinet/web.py
└── config.py

apps/server/tests/
├── contract/test_auth_contracts.py
├── integration/test_web_owner_session_context.py
└── unit/test_config_validation.py

infra/
├── docker-compose.yml
└── env/rec.production.env.example
```

**Structure Decision**: Keep all changes in existing auth/web/config modules, production compose, and focused tests. No new package, dependency, migration, or template system.

## Phase 0: Research and Clarification

Resolved in `research.md`.

Key decisions:

- Reuse 013 VK provider adapter and callback verification.
- Enable only VK as the next browser provider; keep Telegram as a stub.
- Reuse `TWOBRAIN_AUTH_BASE_URL` for public callback URL generation.
- Use provider-specific client ID selection for browser start routes.
- Mount VK secret through the existing Docker secret pattern.

## Phase 1: Data Model, Contracts, and Validation

Design outputs:

- `data-model.md`: existing entities reused, plus browser action/return-path/secret concepts.
- `contracts/browser-vk-login.md`: browser route behavior and failure mapping.
- `contracts/vk-production-secret.md`: production configuration and secret boundary.
- `quickstart.md`: focused validation commands and expected outcomes.

## Post-Design Constitution Re-check

| Gate | Status | Reason |
|------|--------|--------|
| Capture-first MVP integrity | PASS | No capture paths touched. |
| Visible consent and user control | PASS | No capture or hidden recording controls added. |
| Data boundary and secret discipline | PASS | Provider secrets stay server-side; rendered pages expose no secret data. |
| Deletion truth and lifecycle accounting | PASS | No new lifecycle artifacts. |
| Spec-driven delivery with testable gates | PASS | Focused quickstart and repo gate are defined. |
| Product/platform constraints | PASS | No new platform or deployment claim beyond existing server/web cabinet. |

## Complexity Tracking

No constitution violations.
