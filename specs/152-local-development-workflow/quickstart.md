# Quickstart

```sh
infra/scripts/start-local.sh
# open http://127.0.0.1:8081/login; use local@graf.test and the shown code
apps/macos/Scripts/run-local-app.sh
infra/scripts/ci-local.sh --fast
```

Stop dependencies with `docker compose -f infra/docker-compose.local.yml down`.

Evidence: focused local/auth runner 13 passed; Swift 26 passed; fast CI 1088
passed. Manual smoke now passes: PostgreSQL/MinIO healthy, migrations and seed
complete, API starts on `127.0.0.1:8081`, `/login` returns 200 and the email-code
form is present.
