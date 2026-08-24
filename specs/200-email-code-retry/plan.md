# Implementation Plan: Повторный ввод email-кода с лимитом попыток

**Branch**: `codex/200-email-code-retry` | **Date**: 2026-08-25 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/200-email-code-retry/spec.md`

## Summary

Сохранить email-code state после первой и второй неверной проверки, чтобы
пользователь мог повторить ввод, и снизить state-specific rate limit с 10 до 3.
После исчерпания лимита rate limiter блокирует дальнейшие проверки; форма
предлагает запросить новый код. Используются существующие HMAC/browser binding,
TTL, single-use state и лимиты отправки/email/IP.

## Technical Context

**Language/Version**: Python 3.12, Jinja templates, vanilla JavaScript

**Primary Dependencies**: FastAPI, SQLAlchemy, PostgreSQL, existing auth rate limiter

**Storage**: Existing PostgreSQL `auth_callback_states` and
`auth_rate_limit_buckets`; no migration

**Testing**: Focused pytest integration/contract tests, JavaScript static asset
contract tests, existing RLS auth tests

**Risk / Validation Lane**: `high-risk-feature`; authentication state,
brute-force protection, browser binding, replay behavior and user-facing error
UX are affected

**Release Gate**: `no deploy`; implementation and focused validation only

**Target Platform**: GRAF web cabinet and the existing macOS WebView surface

**Project Type**: web service with server-rendered browser and embedded desktop UI

**Performance Goals**: Preserve current auth request cost; add only one bounded
existing-bucket read after a wrong code, with no polling, dependency, or network
round trip

**Constraints**: Do not weaken HMAC, browser nonce, TTL, single-use, replay,
tenant isolation, audit or existing resend/email/IP limits; do not log codes

**Scale/Scope**: Shared login/signup email-code consumer, auth rendering, rate
limit constant and focused tests; account-linking behavior is out of scope

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Capture-First MVP Integrity: **PASS** — no capture or recording code changes.
- Visible Consent And User Control: **PASS** — no capture controls change.
- Privacy And Truthfulness: **PASS** — no code/token/content enters logs or
  evidence; existing auth audit remains metadata-only.
- Auth/session security: **PASS** — browser binding, HMAC, expiry, replay,
  single-use, tenant/RLS behavior and existing resend/email/IP limits remain.
- Clean-room UX/accessibility: **PASS** — shared six-slot input remains, error
  focus and recovery copy are explicit, and WebView/browser use one template.
- Spec-driven delivery: **PASS** — clarify, security/UX checklists, analyze,
  tasks and focused validation are required before closeout.

## Validation Plan

1. Run the focused wrong-code integration test: first/second wrong code keeps
   state usable; correct code then succeeds.
2. Run the three-failure integration test: fourth verification attempt is
   rate-limited and creates no session; resend can start a fresh code.
3. Run signup parity, expiry, replay, browser-binding and RLS auth tests.
4. Run the email-code template/static asset contract tests.
5. Run `infra/scripts/ci-local.sh --fast` before closeout because auth and shared
   user-facing surfaces changed.
6. Do not deploy, prepare a release, or run notarization/appcast checks.

## Project Structure

### Documentation (this feature)

```text
specs/200-email-code-retry/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── contracts/email-code-retry.md
├── checklists/requirements.md
├── checklists/security.md
├── checklists/ux.md
├── quickstart.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/src/twobrain_rec_server/auth/rate_limit.py
apps/server/src/twobrain_rec_server/cabinet/web_routes/auth_email_flow.py
apps/server/src/twobrain_rec_server/cabinet/auth_rendering.py
apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/auth/email_code.html
apps/server/tests/integration/test_web_owner_session_context.py
apps/server/tests/contract/test_account_routes.py
apps/server/tests/contract/test_cabinet_static_assets_contract.py
```

**Structure Decision**: Сохраняем поведение в существующем rate limiter и общем
email-code consumer; новая сущность, миграция и зависимость не нужны.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| None | N/A | Existing state rate-limit bucket and shared template are sufficient. |
