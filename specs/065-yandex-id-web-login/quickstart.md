# Quickstart: Yandex ID Web Login

## Preconditions

- Feature 013 auth schema and provider backend are present.
- Workspace login is configured through `TWOBRAIN_WEB_LOGIN_WORKSPACE_ID` or `workspace_id` query parameter.
- Yandex credentials are configured for real integration environments:
  - `TWOBRAIN_YANDEX_CLIENT_ID`
  - `TWOBRAIN_YANDEX_CLIENT_SECRET_FILE=secrets/twobrain_yandex_client_secret` in the server `.env`
  - `TWOBRAIN_AUTH_BASE_URL=https://rec.2brain.pro` for production-like public callback URLs.

## Focused Validation

```sh
cd apps/server
uv run --extra dev pytest -q tests/integration/test_web_owner_session_context.py
uv run --extra dev pytest -q tests/contract/test_auth_contracts.py
uv run --extra dev pytest -q tests/unit/test_config_validation.py
```

Expected:

- `/login` and `/sign-up` render Yandex ID as active when enabled.
- `/login/yandex/start?next=/meetings` redirects to Yandex authorization.
- Disabled or unavailable Yandex paths fail closed with bounded copy.
- `TWOBRAIN_AUTH_BASE_URL` controls callback `redirect_uri`.
- Existing email login tests still pass.

## Repository Gate

Run before closeout:

```sh
infra/scripts/ci-local.sh
```

Expected:

- Full local CI passes.
- No OpenAPI drift is introduced unless the runtime contract actually changed.

## Manual Public Callback Check

In a production-like environment:

1. Set `TWOBRAIN_AUTH_BASE_URL=https://rec.2brain.pro`.
2. Register `https://rec.2brain.pro/api/v1/auth/callback/yandex` in the Yandex app settings.
3. Open `/login/yandex/start?next=/meetings`.
4. Verify the Yandex authorization URL contains the same callback `redirect_uri`.

Do not commit real Yandex client secrets, callback URLs with signed material, or private account identifiers as evidence.

## Validation Evidence

### 2026-06-27 focused validation

```sh
cd apps/server
uv run --extra dev pytest -q tests/integration/test_web_owner_session_context.py
uv run --extra dev pytest -q tests/contract/test_auth_contracts.py
uv run --extra dev pytest -q tests/unit/test_config_validation.py
```

Observed:

- `tests/integration/test_web_owner_session_context.py`: `21 passed`
- `tests/contract/test_auth_contracts.py`: `20 passed`
- `tests/unit/test_config_validation.py`: `29 passed`

### 2026-06-27 server credential setup

Observed on `2brain.dev` without printing secret values:

- `.env` contains `TWOBRAIN_AUTH_BASE_URL=https://rec.2brain.pro`
- `.env` contains the Yandex client id and `TWOBRAIN_YANDEX_CLIENT_SECRET_FILE=secrets/twobrain_yandex_client_secret`
- `secrets/twobrain_yandex_client_secret` exists, is non-empty, and has mode `0640`

### 2026-06-27 repository gate

```sh
infra/scripts/ci-local.sh
```

Observed:

- `837 passed, 4 skipped`
- server lint passed
- python compile passed
- production compose config rendered with `TWOBRAIN_AUTH_BASE_URL=https://rec.2brain.pro`
  and `twobrain_yandex_client_secret` mounted only into `rec-api`
- deployment evidence scan passed
- `ci_local_result=pass`
