# Contract: Public Auth Base URL

## Setting

`TWOBRAIN_AUTH_BASE_URL`

Purpose:

- Defines the public origin used for provider callback URLs behind the reverse proxy.

## Callback URL Generation

For provider `yandex` and default callback path:

- If `TWOBRAIN_AUTH_BASE_URL=https://rec.2brain.pro`, generated callback URL MUST be:
  - `https://rec.2brain.pro/api/v1/auth/callback/yandex`
- If `TWOBRAIN_AUTH_BASE_URL` is unset, generated callback URL MAY use the request-derived URL.

## Normalization

- Preserve the path from the existing provider callback route.
- Avoid double slashes between origin and callback path.
- Do not include query string or fragment in the configured base URL.

## Failure Handling

- Invalid configured URL is rejected by existing settings validation.
- Missing setting is allowed for local development and tests.
