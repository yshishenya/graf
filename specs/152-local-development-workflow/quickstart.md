# Quickstart

```sh
infra/scripts/start-local.sh
# open http://127.0.0.1:8081/login; use local@graf.test and the shown code
apps/macos/Scripts/run-local-app.sh
apps/macos/Scripts/build-local-app.sh --open
infra/scripts/ci-local.sh --fast
```

The packaged local app is created at `apps/macos/.build/local/GRAF Local.app`.
It is disposable, debug-only, loopback-bound, and is not installed into
`/Applications`.

Stop dependencies with `docker compose -f infra/docker-compose.local.yml down`.

Evidence: focused local/auth runner 2 passed; Swift 26 passed; local debug app
bundle built and launched from `.build/local`; fast CI 1088 passed. Manual smoke
now passes: PostgreSQL/MinIO healthy, migrations and seed complete, API starts on
`127.0.0.1:8081`, `/login` returns 200 and the email-code form is present.
