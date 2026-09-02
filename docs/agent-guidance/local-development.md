# Local Development

The active Dev path is `infra/scripts/start-dev-runtime.sh` through
`infra/scripts/dev-harness.sh`; it owns one `graf-dev` Compose project with
loopback-only API/frontend `http://127.0.0.1:8081`, PostgreSQL `54329`, MinIO
`9002/9003` and Temporal `7233`. It starts API, server-rendered frontend,
Temporal, processing worker and media worker from one exact SHA. The old
`start-local.sh`/`docker-compose.local.yml` path is retained only as a bounded,
non-active compatibility exception until Feature 228 retirement review.

Dev promotion and rollback own the installed app lifecycle. They gracefully
terminate the process launched from `/Applications/GRAF Dev.app`, replace and
re-register the bundle, launch the new candidate, and require
`app_presentation` to prove `GRAF Dev`, channel `dev` and the distinct
Dev-badged icon. Do not run `install-dev-app.sh` directly while the app is
running; it intentionally fails closed. Compensation relaunches the previous
app only when it was running before the transaction.

Login uses the existing email-code flow with `local@graf.test`. Development code
and the non-Secure `graf_dev_owner_session` cookie are enabled only by the local
script; production keeps the existing `__Host-` Secure cookie.

The Dev Compose profile keeps MediaScribe unconfigured by default. Processing
worker pollers still start and are readiness-testable; an actual processing
activity fails closed with `blocked_config` and makes no provider request until
an operator supplies the server-side provider configuration. This exception is
development/test-only; production provider configuration remains mandatory.
