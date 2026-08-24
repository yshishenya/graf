# Implementation Plan: Yandex ID account selection

**Branch**: `codex/200-yandex-account-selection` | **Date**: 2026-08-25 | **Spec**: [spec.md](spec.md)

## Summary

Add the smallest Yandex-only authorization request change that asks Yandex ID
to require interactive confirmation/login, while preserving the existing
server-side callback verification, session custody, and all other providers.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: FastAPI, existing provider adapter layer, urllib.parse

**Storage**: Existing PostgreSQL auth callback state and browser session tables; no schema change

**Testing**: pytest focused integration/contract tests; repository fast lane

**Risk / Validation Lane**: high-risk-feature; authentication behavior and external provider interaction

**Release Gate**: no deploy; user explicitly requested local verification only

**Target Platform**: Server-side browser login

**Project Type**: Python web service

**Performance Goals**: Preserve the existing single redirect and callback flow; no new network round trips in GRAF

**Constraints**: Provider secrets remain server-only; no raw OAuth material in logs/evidence; VK ID and other providers unchanged

**Scale/Scope**: One shared Yandex browser-login adapter and its focused regression tests

## Constitution Check

- PASS: reuse the existing provider adapter and callback verification; no duplicate auth path.
- PASS: no provider secret, OAuth token, raw profile, or cookie is moved to the client or committed.
- PASS: preserve state/nonce binding, client binding, bounded provider failures, and email fallback.
- PASS: no database migration, new dependency, deployment, or production mutation.

## Validation Plan

1. Add a focused regression assertion for `force_confirm=1` on Yandex URLs.
2. Assert the same parameter is absent from VK URLs.
3. Run the Feature 200 quickstart focused tests.
4. Run `infra/scripts/ci-local.sh --fast` before calling the local slice ready.
5. Manual two-account browser acceptance remains required to prove provider UI behavior; no live credentials or identifiers are recorded.

## Project Structure

```text
apps/server/src/twobrain_rec_server/auth/providers/base.py
apps/server/tests/integration/test_web_owner_session_context.py
specs/200-yandex-account-selection/
```

**Structure Decision**: Reuse the existing provider adapter and browser
integration test. No new abstraction, storage, endpoint, or dependency.

## Complexity Tracking

No constitution violations.
