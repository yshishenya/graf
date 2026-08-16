# Local Development

Run `infra/scripts/start-local.sh` for the API and `apps/macos/Scripts/run-local-app.sh`
for the source macOS app. The local API is `http://127.0.0.1:8081`; PostgreSQL is
`54330`, MinIO is `9010/9011`, all loopback-only and separate from dev Compose.

Login uses the existing email-code flow with `local@graf.test`. Development code
and the non-Secure `graf_dev_owner_session` cookie are enabled only by the local
script; production keeps the existing `__Host-` Secure cookie.
