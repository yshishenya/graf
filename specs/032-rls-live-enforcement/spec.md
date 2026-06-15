# Feature Specification: RLS Production Enforcement Truth

**Feature Branch**: `codex/032-rls-live-enforcement`

**Created**: 2026-06-15

**Status**: Draft

**Input**: User description: "Start work on 032. Check everything, prepare it,
and follow the full SDD Spec Kit cycle."

## Clarifications

### Session 2026-06-15

- Q: Should `032` stop before live production enforcement or complete the
  intended `031` rollout? -> A: `031` was intended to enable RLS after
  validation. Current production inspection shows `0005_rls_hardening` is
  already applied and every covered production table has RLS enabled and
  forced. `032` must correct the stale `031` language and tooling that still
  reports live production enforcement as unchanged, preserve the rule that
  destructive probes run only on disposable/test databases, and add read-only
  production-state verification plus truthful evidence.
- Evidence checked on 2026-06-15: production deploy path
  `/opt/projects/2brain-rec` is on `master` at `3fd2162`; Alembic current is
  `0005_rls_hardening (head)`; read-only system-catalog inspection shows every
  covered tenant-owned table reports `relrowsecurity=true` and
  `relforcerowsecurity=true`.

## Product Scope Boundary

Feature `031-rls-hardening` added the database-level tenant isolation layer,
validation helpers, runbook, and ADR for accepted backend tables. The SQL
migration enables and forces row-level security when it is applied to a
PostgreSQL database. Current production inspection shows the production Rec
stack is at Alembic head `0005_rls_hardening`, and all covered production
tables report RLS enabled and forced.

The gap is now evidence and wording truth: `031` docs, current product status,
ADR/runbook text, validation reports, and production-boundary tests still say
live production enforcement is separate or unchanged. `032` must correct that
claim, preserve the safe test-to-production rule, and give operators a
read-only way to verify live production RLS state without seeding destructive
probe rows into live customer tables.

This feature may change validation commands, evidence templates, runbooks,
status updates, and production-state checks needed to make the RLS rollout
truthful. It must not add dashboard, sharing, deletion execution, desktop
upload behavior, MediaScribe behavior, product admin bypass, customer-facing
settings, or destructive live production probes.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Preserve Test Gate Before Production Claims (Priority: P1)

As a deployment operator, I want the RLS validation workflow to keep proving
policies on local/disposable PostgreSQL before production claims are accepted,
so that live production state is never treated as proof for destructive probe
behavior.

**Why this priority**: Live database enforcement can break accepted auth,
ingest, processing, and smoke flows if context propagation is incomplete. The
first responsibility is to prove the exact migration/probe path before it can
touch the production database.

**Independent Test**: Execute the disposable/test validation path and confirm
it still runs migrations and direct probes only on safe databases, never on the
live `twobrain_rec` service database.

**Acceptance Scenarios**:

1. **Given** local regression, disposable PostgreSQL probes, and
   production-like migration verification all pass with fresh evidence,
   **When** the operator records RLS rollout evidence, **Then** the evidence
   names the safe database path used for destructive probes.
2. **Given** any required gate is missing, stale, blocked, failed, or
   inconclusive, **When** the preflight is evaluated, **Then** the verdict is
   blocked and the output names the exact gate that must be repaired.
3. **Given** evidence contains transcript text, raw audio, object keys, tokens,
   signed URLs, passwords, live secret paths, or customer meeting content,
   **When** the preflight evaluates the evidence package, **Then** the verdict
   is blocked before any live decision can be recorded.

---

### User Story 2 - Verify Production RLS Is Actually Enabled (Priority: P1)

As the accountable operator, I want a read-only production verification command
that proves `031` RLS policies are actually enabled and forced on the live
production database, so that the project status reflects reality instead of
the stale "not changed" wording.

**Why this priority**: The intended security outcome is live production tenant
isolation. Alembic current alone is not enough; the operator needs a direct
read-only table-state check for `relrowsecurity` and `relforcerowsecurity`.

**Independent Test**: Run the production-state inspection against a controlled
fixture and against production read-only metadata. It must report every covered
table as enabled/forced or block the production-enabled claim with the exact
missing table names.

**Acceptance Scenarios**:

1. **Given** production Alembic current is `0005_rls_hardening`, **When** the
   operator inspects RLS state, **Then** every covered tenant-owned table
   reports RLS enabled and forced.
2. **Given** any covered table is missing RLS enabled or forced state, **When**
   production state is inspected, **Then** the production-enabled claim is
   blocked and the output names the table.
3. **Given** the production inspection only reads system catalog metadata,
   **When** it runs, **Then** it does not seed, mutate, or expose customer rows.

---

### User Story 3 - Correct Stale 031 Rollout Language (Priority: P1)

As engineering, I want `031` status, runbook, ADR, quickstart, and validation
output to stop saying live production enforcement is unchanged when production
metadata proves it is enabled, so that future work builds on the correct
security boundary.

**Why this priority**: False status language is dangerous in both directions:
it can make future work ignore an active production control, or make operators
repeat an already-applied migration unnecessarily.

**Independent Test**: Scan `031` docs, current product status, ADR/runbook,
changelog, and validation output for stale `not_changed` or separate-decision
claims. Remaining mentions must either be removed or explicitly scoped to
pre-production/test validation.

**Acceptance Scenarios**:

1. **Given** production inspection proves RLS enabled and forced, **When**
   product status is updated, **Then** it says live production RLS enforcement
   is enabled with metadata-only evidence references.
2. **Given** a validation command is only testing a disposable database,
   **When** it reports `not_changed`, **Then** the wording is explicitly about
   the live production database not being used for destructive probes.
3. **Given** stale docs say live enforcement still needs a separate decision,
   **When** this feature closes, **Then** those docs are corrected or marked as
   historical `031` pre-production wording.

---

### User Story 4 - Keep Status And Changelog Truthful (Priority: P2)

As product and engineering leadership, I want the final feature status,
deployment notes, and changelog to say exactly that live production RLS
enforcement is enabled only if read-only production metadata proves it, so that
future dashboard/access/retention slices do not inherit false assumptions.

**Why this priority**: Future `016`, `017`, and `018` work depends on knowing
whether RLS is only implemented and validated or also live-enforced in
production.

**Independent Test**: Review the final docs after each possible decision
outcome. They must describe the actual enforcement state and avoid unsupported
production-readiness claims.

**Acceptance Scenarios**:

1. **Given** live enforcement is verified successfully, **When** the feature is
   closed, **Then** current product status and changelog state that live RLS
   enforcement is enabled on production with evidence references and remaining
   boundaries.
2. **Given** production inspection fails, **When** the feature is closed,
   **Then** current product status and changelog state that production
   enforcement is not accepted and name the blocker without implying readiness.
3. **Given** a rollback or remediation occurs, **When** the feature is closed,
   **Then** the final record states the result, residue status, and follow-up
   owner without exposing forbidden content.

### Edge Cases

- Required evidence exists but was produced before the latest merged RLS code
  or migration change.
- Local gates pass but production-like verification fails or is inconclusive.
- Production Alembic current is at head but one or more tables are not
  `relrowsecurity=true` and `relforcerowsecurity=true`.
- Production inspection cannot connect or cannot prove the environment
  fingerprint.
- A stale doc says production RLS is not changed even though production
  metadata proves enabled/forced.
- Evidence collection would require forbidden content or live secrets.
- Post-production checks need read-only RLS state inspection on live database
  but must not seed destructive probe rows into live customer tables.
- A rollback succeeds functionally but leaves an unresolved documentation,
  evidence, or cleanup residue item.
- Existing dashboard/access/deletion roadmap text says RLS is not live-enforced
  even though production metadata proves enabled/forced.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The feature MUST define a single RLS production truth verdict
  that can be `test_gate_required`, `production_verified_enabled`,
  `production_verification_blocked`, `halted`, or `rolled_back`.
- **FR-002**: The readiness verdict MUST require fresh local regression,
  disposable PostgreSQL RLS probe, production-like migration/probe, and
  metadata-only evidence-scan results before production-enabled status can be
  accepted.
- **FR-003**: The readiness verdict MUST identify stale, missing, failed,
  inconclusive, or forbidden-content evidence as blocking.
- **FR-004**: The feature MUST preserve the `031` safety rule that validation
  must not run probes or migrations against a live production database target
  that is reserved for service traffic.
- **FR-005**: The feature MUST verify the deployed production commit and
  Alembic current revision before accepting any production RLS claim.
- **FR-006**: The production truth record MUST include actor, timestamp, target
  environment, deployed commit, Alembic revision, test-gate evidence
  references, read-only table-state evidence, rollback reference, and open
  risks.
- **FR-007**: The feature MUST reject production truth records that omit
  required metadata, contain ambiguous target information, or conflict with
  current gate evidence.
- **FR-008**: The feature MUST support a truthful blocked decision that leaves
  live enforcement unchanged and records the reason.
- **FR-009**: The feature MUST support a truthful halt decision when pre-change
  or post-change gates fail.
- **FR-010**: The feature MUST support rollback accounting when live
  enforcement is attempted and then reversed.
- **FR-011**: The production verification flow MUST perform production health
  and target checks before accepting production-enabled status.
- **FR-012**: The test/disposable validation flow MUST continue to perform
  same-tenant, cross-tenant, missing-context, worker-context, and
  maintenance-context probes before it can support production truth claims.
- **FR-013**: The production verification flow MUST verify live production RLS state with a
  read-only table-state inspection that proves covered tables have RLS enabled
  and forced.
- **FR-014**: The production verification flow MUST produce a final
  metadata-only state record that distinguishes production verified enabled,
  production verification blocked, halted, rolled back, and unchanged outcomes.
- **FR-015**: The feature MUST update current product status and deployment
  notes so future dashboard, access, sharing, retention, and deletion slices
  can determine whether RLS is implemented-only or live-enforced.
- **FR-016**: The feature MUST update the changelog for any release-readiness,
  operational, security, or documentation change it implements.
- **FR-017**: The feature MUST not add product UI, customer settings, workspace
  admin bypass, dashboard behavior, sharing/download behavior, retention or
  deletion execution, desktop upload behavior, MediaScribe behavior, or
  blind live production enforcement before test gates pass.
- **FR-018**: The feature MUST keep logs, diagnostics, evidence, comments, and
  docs free of transcript text, raw audio, object keys, tokens, signed URLs,
  passwords, live secret paths, and customer meeting content.
- **FR-019**: The feature MUST preserve the blocked-access API contract from
  `031`: cross-tenant reads are not found or empty, cross-tenant mutations are
  authorization failures, and missing tenant context is an auth/context
  failure.
- **FR-020**: The feature MUST correct `031` documentation and validation
  language that says live production enforcement is still separate or
  unchanged when production inspection proves the accepted rollout result is
  production-enabled.

### Key Entities *(include if feature involves data)*

- **RLS Production Truth Verdict**: The current proven state of test and
  production RLS enforcement, including gate summary, target, and timestamp.
- **Production Truth Record**: Metadata-only record of who verified, blocked,
  halted, or rolled back production enforcement, with evidence references and
  open risks.
- **Gate Evidence Package**: References to local, disposable database,
  production-like, post-change, rollback, and forbidden-content scan results.
- **Production Target Fingerprint**: Metadata that identifies the intended
  environment without storing credentials, secret paths, or customer data.
- **Rollback/Halt Record**: Metadata-only state for a stopped or reversed live
  enforcement attempt, including residue and follow-up owner.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of required test gates must have current, metadata-only
  evidence before production-enabled status can be accepted.
- **SC-002**: 100% of incomplete, stale, failed, inconclusive, or
  forbidden-content evidence packages must block production-enabled claims.
- **SC-003**: 100% of production truth records must include actor, timestamp,
  target environment, deployed commit, migration head, evidence references,
  rollback reference, and open-risk fields.
- **SC-004**: 100% of final feature closeout outcomes must state exactly one
  live enforcement state: production verified enabled, production verification
  blocked, halted, rolled back, or unchanged.
- **SC-005**: 100% of post-change validation runs must include same-tenant,
  cross-tenant, missing-context, worker-context, and maintenance-context probe
  outcomes before success is claimed.
- **SC-006**: 0 tracked evidence files, logs, docs, or comments may contain
  transcript text, raw audio, object keys, tokens, signed URLs, passwords, live
  secret paths, or customer meeting content.
- **SC-007**: 100% of covered production tables must report RLS enabled and
  forced before the feature can close as production verified enabled, or the
  rollout must be halted or rolled back.

## Assumptions

- Feature `031-rls-hardening` remains accepted and is the source of RLS policy,
  context, probe, and ADR behavior.
- The live production service remains on the current `2brain.dev` Rec stack
  unless a later plan records a different approved target.
- The safest default is to block production-enabled claims until the
  test/disposable database gate and read-only production state checks pass.
- Production validation evidence is metadata-only and must be safe to commit
  or summarize without exposing customer content or secrets.
- Future `016`, `017`, and `018` product slices may proceed only with truthful
  knowledge of whether RLS is implemented-only or live-enforced.
