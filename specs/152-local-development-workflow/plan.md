# Implementation Plan: Локальный контур разработки

Reuse current email auth, seed, MinIO client and Swift URL configuration. Add only
loopback PostgreSQL/MinIO, startup/launcher scripts, a disposable debug app bundle,
development-only HTTP cookie selection and contract tests. The debug bundle uses a
small shell wrapper to inject loopback origins when launched by Finder, has a
separate bundle identifier, and never carries a Sparkle feed. Ports: API `8081`,
PostgreSQL `54330`, MinIO `9010/9011`.

Validation: shell syntax, Compose config, focused disposable-Postgres auth tests,
Ruff, Python compile, Swift tests and `infra/scripts/ci-local.sh --fast`.
