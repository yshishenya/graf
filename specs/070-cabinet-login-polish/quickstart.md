# Quickstart: Cabinet Login Polish

## Focused Validation

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q tests/integration/test_web_owner_session_context.py
```

Expected:

- `/login` still lists enabled providers and email fallback.
- `/login/{provider}/start?next=/meetings` still redirects to the selected provider.
- Email code login still verifies and opens `/meetings`.
- Auth pages include the shared code form/static assets needed for auto-submit.

```sh
swift test --package-path apps/macos --filter DesktopCabinetRoutePolicyTests
```

Expected:

- Desktop route policy allows provider OAuth as an auth-provider leg during auth continuation.
- Unknown external URLs remain blocked.
- Login and code routes remain allowed.
- First-party provider callback routes remain allowed.

## Repository Gate

Run before PR/closeout:

```sh
infra/scripts/ci-local.sh
```

Expected:

- Full local CI passes.
- No OpenAPI drift is introduced.

## Manual Smoke

1. Open `/login?next=/meetings` in web and in the app embedded login recovery.
2. Confirm the panel is narrower and provider tiles no longer feel oversized.
3. Start email login, paste a six-digit code, and confirm the code submits without pressing the button.
4. In the app, choose an enabled provider and confirm the app no longer shows the generic cabinet-session error at the provider redirect or callback.

Do not record real OAuth codes, tokens, account identifiers, or private email content as evidence.

## Validation Evidence

### 2026-06-30 refreshed validation after master merge

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q tests/contract/test_cabinet_static_assets_contract.py tests/integration/test_web_owner_session_context.py
```

Observed:

- `31 passed in 23.09s`

```sh
swift test --package-path apps/macos --filter DesktopCabinetRoutePolicyTests
```

Observed:

- `9 tests, 0 failures`

```sh
swift test --package-path apps/macos --filter DesktopCabinetWorkspaceTests
```

Observed:

- `28 tests, 0 failures`

```sh
infra/scripts/ci-local.sh
```

Observed:

- `988 passed, 4 skipped`
- server lint passed
- python compile passed
- deployment evidence scan passed
- `ci_local_result=pass`
- local RLS live-enforcement probe remained non-production-only: `rls_validation_result=blocked` because the local Postgres test database was not provided
