# Infra Candidates

**Date**: 2026-06-30
**Scope**: `infra/`, `scripts/`, `.specify/scripts/`, server scripts, macOS validation scripts, and Docker/Compose references.

## Static Evidence

- Shell syntax check passed across `apps/macos`, `infra`, `scripts`, and `.specify/scripts`.
- `infra/scripts/ci-local.sh` passed and reported `ci_local_result=pass`.
- Docker Compose production config rendered successfully during `ci-local`.

## Candidate Decisions

### INFRA-001: Production deploy/smoke/backup/restore scripts

Locations:

- `infra/scripts/cd-remote.sh`
- `infra/scripts/run-production-smoke.sh`
- `infra/scripts/backup-rec-stack.sh`
- `infra/scripts/rehearse-rec-restore.sh`
- `infra/scripts/rollback-rec-stack.sh`
- `infra/scripts/validate-production-config.sh`
- `infra/scripts/verify-rec-migration.sh`

Decision: retained.

Reason:

- These are operational safety entrypoints. They are not redundant just because this cleanup slice does not deploy.

### INFRA-002: Spec Kit scripts

Locations:

- `.specify/scripts/bash/*.sh`

Decision: retained.

Reason:

- The 071 feature itself depends on these scripts for prerequisite and plan/task context.

### INFRA-003: Generated caches

Locations:

- `apps/server/scripts/__pycache__/`
- `apps/macos/.build/`

Decision: excluded from tracked-code refactor.

Reason:

- They are generated local outputs and not tracked source. Cleaning them is workspace hygiene, not a code refactor.

### INFRA-004: `XXX`/`TODO` text scan hits

Locations:

- `infra/scripts/cd-remote.sh`
- `apps/macos/Scripts/validate-us1-regression.sh`

Decision: retained.

Reason:

- The hits are `mktemp` templates containing `XXXXXX`, not TODO/FIXME debt.

## Approved Infra Removals

None in the current audit pass.
