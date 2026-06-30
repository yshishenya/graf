# Infra And Script Dependency Evidence

**Date**: 2026-06-30
**Scope**: `infra/`, `scripts/`, `.specify/scripts/`, `apps/server/scripts/`, macOS scripts, and installer scripts.

## Tracked Script Surfaces

Tracked server scripts:

- `cleanup_smoke_artifacts.py`
- `cleanup_smoke_auth_session.py`
- `create_test_artifact.py`
- `generate_mvp_loop_readiness.py`
- `issue_smoke_auth_session.py`
- `prove_owner_review_live.py`
- `seed_dev_identity.py`
- `seed_smoke_identity.py`
- `upload_test_artifact.py`
- `verify_rls_hardening.py`

Shell/script surfaces include:

- `.specify/scripts/bash/*.sh`
- `infra/scripts/*.sh`
- `scripts/prepare-release.sh`
- `apps/macos/Scripts/*.sh`
- `apps/macos/Installer/Scripts/*.sh`

Generated Python bytecode under `apps/server/scripts/__pycache__/` is not tracked and is excluded from 071 cleanup evidence.

## Runtime Entrypoints

- `infra/server/Dockerfile` launches `uvicorn twobrain_rec_server.main:create_app --factory`.
- `infra/docker-compose.yml` and `infra/docker-compose.dev.yml` run migration services with `alembic upgrade head`.
- `infra/scripts/ci-local.sh` is the local gate and runs server pytest, Ruff, Python compile, RLS boundary validation, production compose config, and deployment evidence scan.
- `infra/scripts/cd-remote.sh`, `run-production-smoke.sh`, backup/restore/rollback scripts, and production validation scripts are deployment surfaces. They are not cleanup candidates without a release/deploy-specific task.
- macOS validation scripts run targeted `swift build` and `swift test` commands for capture, routing, installer, leakage, and release-hardening evidence.

## Decisions

- Keep Docker Compose and Dockerfile references as runtime entrypoints.
- Keep `.specify/scripts` as Spec Kit infrastructure.
- Keep production deploy/smoke/backup/restore scripts. They are operational safety surfaces and out of scope for deletion in a non-deploy cleanup slice.
- Do not remove generated local caches as part of tracked code refactor evidence; they can be cleaned separately if workspace hygiene is requested.

## Validation

- `find apps/macos infra scripts .specify/scripts -type f -name '*.sh' -print0 | xargs -0 -n1 bash -n`: pass.
- `infra/scripts/ci-local.sh`: pass with `ci_local_result=pass`.
