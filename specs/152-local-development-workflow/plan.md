# Implementation Plan: Локальный контур разработки

Reuse current email auth, seed, MinIO client and Swift URL configuration. Add only
loopback PostgreSQL/MinIO, startup/launcher scripts, development-only HTTP cookie
selection and contract tests. Ports: API `8081`, PostgreSQL `54330`, MinIO `9010/9011`.

Validation: shell syntax, Compose config, focused disposable-Postgres auth tests,
Ruff, Python compile, Swift tests and `infra/scripts/ci-local.sh --fast`.
