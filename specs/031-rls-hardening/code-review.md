# Code Review: 031 RLS Hardening

**Date**: 2026-06-15

**Scope**: local uncommitted implementation for `031-rls-hardening`.

**Review focus**: correctness, security/privacy, RLS proof quality, worker/auth
logic, maintainability, rollout gates, and Spec Kit traceability.

## Verdict

Original review verdict: request changes before this feature is PR-ready or
deployment-ready.

The implementation has a solid direction: tenant context helpers exist, current
tenant-owned tables are inventoried, API sessions are wired through request
context, and live production enforcement is not enabled automatically.

The original blockers were in the proof and safety boundary:

- PostgreSQL RLS probes are not implemented even when `RLS_TEST_DATABASE_URL` is
  present.
- The production-like migration verification script can print `pass` after a
  blocked RLS verdict.
- Auth/session RLS has partial-context openings around session-token lookup.
- RLS can hide global provider identity conflicts and turn controlled auth/link
  errors into database integrity failures.
- Worker missing-context behavior is implicit DB failure, not explicit
  fail-closed evidence.
- Maintenance context is not fully constrained by SQL metadata requirements.

## Remediation Status

Recorded after the 2026-06-15 full post-review remediation pass.

- CR-001 through CR-009 are fixed locally.
- Real PostgreSQL proof passed against a disposable local PostgreSQL database
  using a non-owner probe role.
- A new PostgreSQL migration stability issue was found while proving CR-001:
  `rec_setting_uuid()` as a PL/pgSQL helper hung on local PostgreSQL 14. It was
  converted to a SQL-only UUID regex helper and covered by a regression test.

## Fresh Remediation Evidence

- `git diff --check`
  - Result: pass
- `./infra/scripts/ci-local.sh`
  - Result: `ci_local_result=pass`
  - Server tests: `314 passed, 4 skipped`
  - Ruff: `All checks passed!`
  - RLS validation boundary: blocked locally because `RLS_TEST_DATABASE_URL` is
    not set
- GitHub issue comments were added for #723, #724, #725, #727, and #728 with
  remediation status and validation evidence.
- Focused post-review remediation tests:
  - Result: `29 passed`
- RLS focused suite:
  - Result: `66 passed, 4 skipped`
- Disposable PostgreSQL RLS proof:
  - `tests/integration/test_rls_postgres_policies.py`: `4 passed`
  - `apps/server/scripts/verify_rls_hardening.py`:
    `rls_validation_result=pass`, `ready_for_operator_decision=true`

## Second Review Finding

### CR-009: Provider link conflict audit was not committed before error response

**Severity**: P1 PR blocker

**Issue**: #731

`link_provider` wrote `provider_link_conflict` or `provider_link_rejected`
metadata-only audit evidence, then raised `ProblemDetail` without committing the
session. The API returned a controlled conflict/rejected response, but the audit
event could be rolled back when the request-scoped DB session closed.

**Product effect**: the auth/link path could be truthful to the caller while
leaving no durable evidence for the denied link attempt.

**Status**: fixed locally. The failure path now commits after writing failure
audit evidence, and
`tests/contract/test_auth_contracts.py::test_auth_link_conflict_persists_metadata_only_audit`
passes.

## Original Reviewed Evidence

Captured before the remediation pass.

- `python3 apps/server/scripts/verify_rls_hardening.py`
  - Result: `rls_validation_result=blocked`
  - Reason: `postgres_test_database_required`
- `RLS_TEST_DATABASE_URL=postgresql+asyncpg://example:example@127.0.0.1:5432/example python3 apps/server/scripts/verify_rls_hardening.py`
  - Result: `rls_validation_result=blocked`
  - Reason: `rls_probe_execution_not_implemented_in_script`
- `rg postgres_rls_engine apps/server/tests`
  - Result: fixture exists, but no real probe test imports it.
- `test -f apps/server/tests/integration/test_rls_postgres_policies.py`
  - Result: file missing, while quickstart references it.

## Original Findings

### CR-001: PostgreSQL RLS probes are still a stub

**Severity**: P1 deployment blocker

**Issue**: #723

`apps/server/scripts/verify_rls_hardening.py` reports a blocked validation even
when `RLS_TEST_DATABASE_URL` is set, because probe execution is not implemented.
`apps/server/tests/fixtures/postgres_rls.py` is not used by any real test, and
the quickstart references missing file
`apps/server/tests/integration/test_rls_postgres_policies.py`.

**Product effect**: the feature cannot honestly claim database-enforced tenant
isolation. It only proves source text and application behavior, not PostgreSQL
RLS semantics.

### CR-002: Migration verification can print pass after blocked RLS validation

**Severity**: P1 deployment blocker

**Issue**: #724

`infra/scripts/verify-rec-migration.sh --execute` calls
`verify_rls_hardening.py` but does not parse `rls_validation_result`. Since the
Python script exits `0` for blocked evidence, the shell script can continue and
print `migration_verification_result=pass`.

**Product effect**: operators could receive a false production-like readiness
signal before RLS proof exists.

### CR-003: Auth session lookup lacks a full context-kind guard

**Severity**: P1 PR blocker

**Issue**: #725

The `auth_sessions` policy allows a row when
`session_token_hash = rec_auth_session_token_hash()` without also requiring
`rec_context_kind() = auth_session_lookup`. `user_identities` can also become
visible through that parent session branch. In contrast, callback-state lookup
does require an explicit callback lookup context.

`auth_session_lookup` is also present in the maintenance operation allowlist,
although auth session lookup is a bounded auth bootstrap context, not operator
maintenance.

**Product effect**: a partial GUC context is enough to unlock auth/session
lookup behavior. For RLS boundary code, partial contexts should fail closed.

### CR-004: RLS can turn global provider identity conflicts into integrity errors

**Severity**: P1 PR blocker

**Issue**: #726

`ExternalIdentity` has global uniqueness on `(provider, provider_subject)`.
Auth callback and link flows check for existing identities through normal
RLS-scoped queries. Under RLS, a conflicting identity in another organization can
be hidden, so the pre-check returns `None` and the insert later fails at flush
instead of returning controlled `identity_subject_conflict` or `link_conflict`.

**Product effect**: an accepted auth error can become a 500-class database
failure and leave callback/link audit behavior less predictable.

### CR-005: Worker missing tenant scope is not explicitly fail-closed

**Severity**: P1 PR blocker

**Issue**: #727

`tenant_scope_from_processing_payload()` returns `None` when required tenant
fields are missing. `run_processing_pipeline_activity()` and
`_persist_activity_client_error()` then continue without applying worker tenant
context.

**Product effect**: under PostgreSQL RLS this likely fails by accident inside
database operations and can become retry noise, not a controlled blocked outcome
with metadata-only evidence.

### CR-006: Maintenance context metadata is not required by SQL policy

**Severity**: P1 PR blocker

**Issue**: #728

`rec_maintenance_allowed()` checks only `context_kind=maintenance` and
allowlisted operation. It does not require non-empty actor, reason, or feature
area. `MaintenanceTenantContext` also validates operation only.

**Product effect**: this weakens the decision that there is no product/admin
RBAC bypass and only fixed metadata-logged operator maintenance.

### CR-007: Organization-scoped policies are broader than the contract

**Severity**: P2 hardening before downstream admin/dashboard work

**Issue**: #729

The policy matrix requires organization-scoped data to be visible through
organization context plus membership or approved organization role. The migration
currently checks only current organization for `organizations` and
`user_identities` request/bootstrap branches.

**Product effect**: current routes may still be protected by application logic,
but the database second line of defense is weaker than the stated contract for
future org/admin paths.

### CR-008: Tenant context and policy generation are too stringly typed

**Severity**: P2 hardening

**Issue**: #730

Tenant context dataclasses accept arbitrary `context_kind` strings.
`apply_tenant_scope()` also accepts any string. Migration policy wrapping infers
content context with substring checks inside SQL expressions.

**Product effect**: future policy or context changes are easy to misclassify
without tests failing, which is risky for security boundary code.

## Non-Blocking Notes

- API request DB sessions for ingest and processing do apply tenant context
  before route work.
- Audit metadata sanitizes callback state nonce into hashes.
- Current table inventory appears to cover all existing SQLAlchemy tenant-owned
  tables.
- Workspace-level RLS for content tables matches the current contract; narrower
  owner/device restrictions remain application-level unless future specs change
  that boundary.

## Recommendation

Original CR-001 through CR-008 and second-review CR-009 no longer block 031
locally.

Run one final full review and full local CI before PR/merge. Live production
enforcement remains a separate operator decision and must not be implied by this
local PostgreSQL proof.
