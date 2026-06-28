# Implementation Plan: Yandex ID Web Login

**Branch**: `codex/065-yandex-id-web-login` | **Date**: 2026-06-27 | **Spec**: `specs/065-yandex-id-web-login/spec.md`

**Input**: Feature specification from `specs/065-yandex-id-web-login/spec.md`

## Summary

Enable Yandex ID as a real browser web-cabinet login/sign-up entrypoint by reusing the 013 provider backend, replacing the current disabled stub with a provider start redirect, and making provider callback URLs respect the configured public auth base URL.

## Technical Context

**Language/Version**: Python 3.13 in `apps/server`.

**Primary Dependencies**: Existing FastAPI, SQLAlchemy async ORM, Pydantic settings, and 013 auth provider/session modules. No new dependencies.

**Storage**: Existing 013 auth tables only; no migration.

**Testing**: Existing pytest server contract/integration/unit harness.

**Risk / Validation Lane**: Active Spec Kit slice, high-risk auth area. Scope is narrow and reuses 013 backend, but browser auth and callback URL behavior require focused tests plus repository gate before closeout.

**Release Gate**: No deploy in this slice unless explicitly approved later. Production rollout would require `infra/scripts/cd-remote.sh --dry-run` and then `--execute` only after a release decision.

**Target Platform**: Browser web cabinet served by the Linux/Docker server.

**Project Type**: Backend-rendered web/API service.

**Performance Goals**: Provider start remains a single DB-backed state creation plus redirect; no user-visible delay beyond normal provider navigation.

**Constraints**:
- Do not log or render raw provider secrets, codes, tokens, claims, emails, phones, or live secret paths.
- Do not add a new OAuth library, provider abstraction, database migration, or desktop OAuth flow.
- Preserve email login fallback.
- Preserve existing 013 provider verification and callback state behavior.

**Scale/Scope**: One visible provider surface: Yandex ID in browser login/sign-up.

## Constitution Check

| Gate | Status | Reason |
|------|--------|--------|
| Capture-first MVP integrity | PASS | No capture, recording, driver, or routing behavior changes. |
| Visible consent and user control | PASS | No capture behavior changes; auth consent remains provider/browser controlled plus existing RU copy. |
| Data boundary and secret discipline | PASS | Reuses server-side provider verification and forbids secret/token/client exposure. |
| Deletion truth and lifecycle accounting | PASS | No new data stores; existing auth audit/session entities remain accountable. |
| Spec-driven delivery with testable gates | PASS | Slice has spec, clarify decisions, plan, checklists, tasks, quickstart, and focused tests. |
| Product/platform constraints | PASS | Server/web-only; no new platform support claims. |

## Validation Plan

- Focused tests:
  - `PYTHONPATH=apps/server/src pytest -q apps/server/tests/integration/test_web_owner_session_context.py`
  - `PYTHONPATH=apps/server/src pytest -q apps/server/tests/contract/test_auth_contracts.py`
  - `PYTHONPATH=apps/server/src pytest -q apps/server/tests/unit/test_config_validation.py`
- Repository gate before closeout because auth and web login behavior changed:
  - `infra/scripts/ci-local.sh`
- Deploy gate:
  - Not run unless release/deploy is approved.

## Project Structure

### Documentation (this feature)

```text
specs/065-yandex-id-web-login/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── browser-yandex-login.md
│   └── public-auth-base-url.md
├── checklists/
│   ├── requirements.md
│   ├── security.md
│   └── ux.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/src/twobrain_rec_server/
├── api/auth.py
├── cabinet/rendering.py
├── cabinet/templates/cabinet/auth/login.html
├── cabinet/templates/cabinet/auth/signup.html
├── cabinet/web.py
└── config.py

apps/server/tests/
├── contract/test_auth_contracts.py
├── integration/test_web_owner_session_context.py
└── unit/test_config_validation.py
```

**Structure Decision**: Keep all changes in existing auth/web modules and tests. No new package, dependency, migration, or template system.

## Phase 0: Research and Clarification

Resolved in `research.md`.

Key decisions:

- Reuse 013 provider start and callback services.
- Enable only Yandex browser start in this slice.
- Use `TWOBRAIN_AUTH_BASE_URL` for public callback URL generation when configured.
- Keep email login fallback visible.

## Phase 1: Data Model, Contracts, and Validation

Design outputs:

- `data-model.md`: existing entities reused, plus browser action/return-path concepts.
- `contracts/browser-yandex-login.md`: browser route behavior and failure mapping.
- `contracts/public-auth-base-url.md`: callback URL generation contract.
- `quickstart.md`: focused validation commands and expected outcomes.

## Post-Design Constitution Re-check

| Gate | Status | Reason |
|------|--------|--------|
| Capture-first MVP integrity | PASS | No capture paths touched. |
| Visible consent and user control | PASS | No capture or hidden recording controls added. |
| Data boundary and secret discipline | PASS | Provider secrets stay server-side; rendered pages expose no secret data. |
| Deletion truth and lifecycle accounting | PASS | No new lifecycle artifacts. |
| Spec-driven delivery with testable gates | PASS | Focused quickstart and repo gate are defined. |
| Product/platform constraints | PASS | No new platform or deployment claim. |

## Complexity Tracking

No constitution violations.
