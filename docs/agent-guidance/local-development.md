# Local Development

Run `infra/scripts/start-local.sh` for the API and `apps/macos/Scripts/run-local-app.sh`
for the source macOS app. The local API is `http://127.0.0.1:8081`; PostgreSQL is
`54330`, MinIO is `9010/9011`, all loopback-only and separate from dev Compose.

For a single local command center, use `./scripts/graf-mac.sh` from the repository
root:

```sh
./scripts/graf-mac.sh status
./scripts/graf-mac.sh start       # foreground API; keep this terminal open
./scripts/graf-mac.sh app         # build and open GRAF Local after API is ready
./scripts/graf-mac.sh preflight   # tools, Compose, whitespace and health
./scripts/graf-mac.sh ci          # fast repository CI
```

The helper delegates server, app-build and CI work to the existing scripts. It
does not change permissions, install packages, stop Docker, or collect audio.

Login uses the existing email-code flow with `local@graf.test`. Development code
and the non-Secure `graf_dev_owner_session` cookie are enabled only by the local
script; production keeps the existing `__Host-` Secure cookie.
