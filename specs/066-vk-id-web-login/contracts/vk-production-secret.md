# Contract: VK Production Secret

## Runtime Settings

Required for production VK rollout:

- `TWOBRAIN_VK_CLIENT_ID`
- `TWOBRAIN_VK_CLIENT_SECRET_FILE`
- `TWOBRAIN_AUTH_BASE_URL=https://rec.2brain.pro`

The secret file path is consumed by Docker Compose interpolation and mounted into `rec-api` as `/run/secrets/twobrain_vk_client_secret`.

## Provider Console Callback

VK app settings must include:

```text
https://rec.2brain.pro/api/v1/auth/callback/vk
```

## Failure Behavior

- Missing configured host secret file prevents container startup or deployment.
- Empty configured VK secret fails production settings validation.
- Callback exchange errors return bounded provider-unavailable behavior without exposing VK response bodies.

## Evidence Safety

Deployment and smoke evidence may report:

- secret file present/non-empty as boolean
- file mode/owner class if needed
- public callback URL

Evidence must not include:

- client secret value
- OAuth code
- access token
- raw VK profile payload
- live private user identifiers
