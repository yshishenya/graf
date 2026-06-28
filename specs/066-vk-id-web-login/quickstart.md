# Quickstart: VK ID Web Login

## Prerequisites

- Feature 013 auth schema and VK provider backend are present.
- Web-login workspace is configured.
- For production smoke:
  - `TWOBRAIN_AUTH_BASE_URL=https://rec.2brain.pro`
  - `TWOBRAIN_VK_CLIENT_ID` in the server `.env`
  - `TWOBRAIN_VK_CLIENT_SECRET_FILE=secrets/twobrain_vk_client_secret` in the server `.env`
- VK app callback registered as `https://rec.2brain.pro/api/v1/auth/callback/vk`
- VK ID access settings allow the `email` and `phone` scopes when unmasked
  data is required.

## Focused Local Validation

```sh
PYTHONPATH=apps/server/src pytest -q apps/server/tests/integration/test_web_owner_session_context.py
PYTHONPATH=apps/server/src pytest -q apps/server/tests/contract/test_auth_contracts.py
PYTHONPATH=apps/server/src pytest -q apps/server/tests/unit/test_config_validation.py
```

Expected:

- `/login` and `/sign-up` render VK as an active provider when policy enables VK.
- `/login` and `/sign-up` render Mail.ru and Одноклассники as VK ID-backed
  active provider hints.
- `/login/vk/start?next=/meetings` redirects to VK ID authorization.
- `/login/vk/start?next=/meetings&auth_provider=mail_ru` forwards
  `provider=mail_ru` to VK ID.
- `/login/vk/start?next=/meetings&auth_provider=ok_ru` forwards
  `provider=ok_ru` to VK ID.
- VK start uses VK client ID and `/api/v1/auth/callback/vk`.
- Telegram remains a stub.
- Email login remains visible.
- Provider failures render bounded recovery copy.

## Repository Gate

```sh
infra/scripts/ci-local.sh
```

Expected:

- server tests, Ruff, compile checks, compose config, and evidence scanning pass.

## Production Configuration Checklist

1. Create or reuse a VK app.
2. Register `https://rec.2brain.pro/api/v1/auth/callback/vk` in the VK app settings.
3. On `2brain.dev`, set `TWOBRAIN_VK_CLIENT_ID` in `/opt/projects/2brain-rec/.env`.
4. On `2brain.dev`, set `TWOBRAIN_VK_CLIENT_SECRET_FILE=secrets/twobrain_vk_client_secret` in `/opt/projects/2brain-rec/.env`.
5. Write the VK client secret to `/opt/projects/2brain-rec/secrets/twobrain_vk_client_secret`.
6. Ensure the secret file is readable by `rec-api` after Docker secret mounting.

## Production Smoke

After release/deploy:

```sh
curl -sS -D /tmp/vk-start.headers -o /tmp/vk-start.body \
  'https://rec.2brain.pro/login/vk/start?next=/meetings'
```

Expected:

- HTTP `303`
- `Location` starts with `https://id.vk.ru/authorize`
- `redirect_uri` is `https://rec.2brain.pro/api/v1/auth/callback/vk`
- `code_challenge_method=S256`
- no secret values are printed
