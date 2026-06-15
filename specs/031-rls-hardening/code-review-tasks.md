# Code Review Remediation Tasks

**Source**: `specs/031-rls-hardening/code-review.md`

These tasks are separate from T001-T056 because they were discovered during
post-implementation code review after the initial Spec Kit task set was marked
complete.

## P1: Blocks PR Or Deployment Readiness

- [X] R001 [P] [CR-001] Implement real PostgreSQL RLS probes and wire them into `apps/server/scripts/verify_rls_hardening.py` and `apps/server/tests/integration/test_rls_postgres_policies.py` (#723)
- [X] R002 [P] [CR-002] Make `infra/scripts/verify-rec-migration.sh --execute` block/fail when RLS validation verdict is blocked (#724)
- [X] R003 [P] [CR-003] Require explicit `auth_session_lookup` context for token-hash session lookup and remove it from maintenance bypass allowlist (#725)
- [X] R004 [P] [CR-004] Preserve controlled auth/link provider identity conflict outcomes under PostgreSQL RLS (#726)
- [X] R005 [P] [CR-005] Explicitly block worker activity payloads that lack trusted tenant scope before tenant-owned DB queries (#727)
- [X] R006 [P] [CR-006] Require complete maintenance actor/reason/feature metadata in Python helpers and SQL maintenance policy (#728)

## P2: Hardening Before Downstream Product Slices

- [X] R007 [CR-007] Add membership or approved-role guard for organization-scoped RLS, or document and probe a bounded auth bootstrap exception (#729)
- [X] R008 [CR-008] Type tenant context kinds and replace substring-based migration policy inference with explicit policy classification (#730)

## Second Review Findings

- [X] R009 [CR-009] Persist metadata-only audit evidence for provider link conflict/rejected responses before raising `ProblemDetail` (#731)

## Required Flow

1. Update tests first for each remediation task.
2. Implement the smallest code change that satisfies the tests.
3. Re-run focused tests for the affected area.
4. Re-run `./infra/scripts/ci-local.sh`.
5. Update `specs/031-rls-hardening/quickstart.md` with fresh evidence.
6. Mark the matching `R00x` task complete only after validation passes.

## Remediation Status

Recorded on 2026-06-15 after post-review remediation.

- R001-R009 are fixed locally.
- Focused post-review remediation tests passed with `29 passed`.
- RLS focused suite passed with `66 passed, 4 skipped`.
- Real PostgreSQL RLS proof passed on a disposable local PostgreSQL database:
  `tests/integration/test_rls_postgres_policies.py` returned `4 passed`, and
  `apps/server/scripts/verify_rls_hardening.py` returned
  `rls_validation_result=pass`.
