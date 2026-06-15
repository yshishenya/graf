# Feature Specification: RLS Live Production Enforcement Gate

**Feature Branch**: `codex/032-rls-live-enforcement`

**Created**: 2026-06-15

**Status**: Draft

**Input**: User description: "Start work on 032. Check everything, prepare it,
and follow the full SDD Spec Kit cycle."

## Product Scope Boundary

Feature `031-rls-hardening` added the database-level tenant isolation layer,
validation helpers, runbook, and ADR for accepted backend tables. It explicitly
did not enable live production enforcement. This `032` slice turns that
deferred operator decision into a controlled, auditable production gate.

The feature outcome is not "RLS is enabled because code exists." The outcome is
that an operator can make, record, validate, halt, roll back, or defer the live
production enforcement decision using fresh metadata-only evidence. Any live
production enforcement state change requires explicit operator approval after
all required gates pass.

This feature may prepare command flow, evidence templates, runbooks, status
updates, and validation checks for the live production decision. It must not add
dashboard, sharing, deletion execution, desktop upload behavior, MediaScribe
behavior, product admin bypass, customer-facing settings, or automatic live
production enforcement.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Prove Gates Before Live Enforcement (Priority: P1)

As a deployment operator, I want one clear preflight that proves local,
disposable database, and production-like RLS validation gates are current, so
that I do not change live enforcement state from stale or partial evidence.

**Why this priority**: Live database enforcement can break accepted auth,
ingest, processing, and smoke flows if context propagation is incomplete. The
first responsibility is to prove readiness before any live state change.

**Independent Test**: Execute the preflight against current repository and
production-like evidence inputs. It must produce a metadata-only verdict that
is either ready for explicit operator decision or blocked with named missing,
stale, or failed gates.

**Acceptance Scenarios**:

1. **Given** local regression, disposable PostgreSQL probes, and
   production-like migration verification all pass with fresh evidence,
   **When** the operator runs the decision preflight, **Then** the verdict is
   ready for explicit operator decision and names the evidence inputs used.
2. **Given** any required gate is missing, stale, blocked, failed, or
   inconclusive, **When** the preflight is evaluated, **Then** the verdict is
   blocked and the output names the exact gate that must be repaired.
3. **Given** evidence contains transcript text, raw audio, object keys, tokens,
   signed URLs, passwords, live secret paths, or customer meeting content,
   **When** the preflight evaluates the evidence package, **Then** the verdict
   is blocked before any live decision can be recorded.

---

### User Story 2 - Record Explicit Operator Decision (Priority: P1)

As the accountable operator, I want the live RLS decision to require an explicit
decision record with actor, timestamp, intended outcome, evidence references,
and halt criteria, so that production enforcement cannot change silently or be
confused with feature implementation.

**Why this priority**: `031` intentionally separated implementation from live
production enforcement. The production decision must be traceable and
auditable before the project can claim a changed live enforcement state.

**Independent Test**: Attempt to record enable, defer, and halt decisions with
complete and incomplete metadata. Complete records must be accepted; incomplete
or ambiguous records must be rejected without changing live enforcement state.

**Acceptance Scenarios**:

1. **Given** all readiness gates pass and the operator records an enable
   decision with complete metadata, **When** the decision is accepted, **Then**
   the repository has a metadata-only record linking the decision to fresh
   evidence and expected rollback/halt behavior.
2. **Given** the operator chooses to defer live enforcement, **When** the
   decision is recorded, **Then** the project status remains truthful that live
   enforcement is not changed and names the unresolved reason.
3. **Given** an enable request lacks actor, timestamp, evidence references,
   target environment, or halt criteria, **When** the decision is validated,
   **Then** it is rejected and no production change is authorized.

---

### User Story 3 - Execute Or Halt Live Change Safely (Priority: P1)

As an operator applying an approved decision, I want live enforcement changes
to be bounded by pre-change health, post-change probes, halt criteria, and
rollback instructions, so that the system can stop or recover quickly if
accepted flows are affected.

**Why this priority**: A correct decision record is not enough. The live change
itself must preserve the existing production service boundary and fail safely
if RLS enforcement blocks legitimate same-tenant work.

**Independent Test**: Simulate approved enable, blocked enable, and rollback
flows in a production-like environment. The flow must refuse unsafe targets,
run post-change probes, and produce a truthful final state.

**Acceptance Scenarios**:

1. **Given** an approved enable decision and healthy pre-change state, **When**
   the operator applies the live enforcement flow, **Then** post-change probes
   prove same-tenant flows still work and cross-tenant/missing-context access
   remains blocked.
2. **Given** post-change probes fail or production health degrades, **When**
   halt criteria are reached, **Then** the flow stops further rollout and gives
   rollback instructions before success can be claimed.
3. **Given** the target is not the approved production environment or the
   evidence points at a forbidden live validation database target, **When** the
   change is requested, **Then** the flow blocks the change.

---

### User Story 4 - Keep Status And Changelog Truthful (Priority: P2)

As product and engineering leadership, I want the final feature status,
deployment notes, and changelog to say exactly whether live enforcement was
enabled, deferred, halted, or rolled back, so that future dashboard/access/
retention slices do not inherit false assumptions.

**Why this priority**: Future `016`, `017`, and `018` work depends on knowing
whether RLS is only implemented and validated or also live-enforced in
production.

**Independent Test**: Review the final docs after each possible decision
outcome. They must describe the actual enforcement state and avoid unsupported
production-readiness claims.

**Acceptance Scenarios**:

1. **Given** live enforcement is enabled successfully, **When** the feature is
   closed, **Then** current product status and changelog state that live RLS
   enforcement is enabled with evidence references and remaining boundaries.
2. **Given** live enforcement is deferred or halted, **When** the feature is
   closed, **Then** current product status and changelog state that enforcement
   is not changed and name the blocker without implying readiness.
3. **Given** a rollback occurs, **When** the feature is closed, **Then** the
   final record states the rollback result, residue status, and follow-up
   owner without exposing forbidden content.

### Edge Cases

- Required evidence exists but was produced before the latest merged RLS code
  or migration change.
- Local gates pass but production-like verification fails or is inconclusive.
- The decision record says "enable" but the target environment or database
  fingerprint does not match the approved production target.
- A human operator approves enable but post-change probes fail.
- Evidence collection would require forbidden content or live secrets.
- A rollback succeeds functionally but leaves an unresolved documentation,
  evidence, or cleanup residue item.
- Existing dashboard/access/deletion roadmap text assumes RLS live enforcement
  when the actual decision is deferred.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The feature MUST define a single readiness verdict for live RLS
  enforcement that can be `ready_for_operator_decision`, `blocked`, `deferred`,
  `enabled`, `halted`, or `rolled_back`.
- **FR-002**: The readiness verdict MUST require fresh local regression,
  disposable PostgreSQL RLS probe, production-like migration/probe, and
  metadata-only evidence-scan results before it can become
  `ready_for_operator_decision`.
- **FR-003**: The readiness verdict MUST identify stale, missing, failed,
  inconclusive, or forbidden-content evidence as blocking.
- **FR-004**: The feature MUST preserve the `031` safety rule that validation
  must not run probes or migrations against a live production database target
  that is reserved for service traffic.
- **FR-005**: The feature MUST require an explicit operator decision record
  before any live production enforcement state can be changed.
- **FR-006**: The operator decision record MUST include actor, timestamp,
  target environment, intended outcome, evidence references, expected live
  enforcement state, halt criteria, rollback reference, and open risks.
- **FR-007**: The feature MUST reject decision records that omit required
  metadata, contain ambiguous target information, or conflict with current gate
  evidence.
- **FR-008**: The feature MUST support a truthful defer decision that leaves
  live enforcement unchanged and records the reason.
- **FR-009**: The feature MUST support a truthful halt decision when pre-change
  or post-change gates fail.
- **FR-010**: The feature MUST support rollback accounting when live
  enforcement is attempted and then reversed.
- **FR-011**: The live-change flow MUST perform pre-change production health
  and target checks before applying any approved enforcement change.
- **FR-012**: The live-change flow MUST perform post-change same-tenant,
  cross-tenant, missing-context, worker-context, and maintenance-context probes
  before success can be claimed.
- **FR-013**: The live-change flow MUST produce a final metadata-only state
  record that distinguishes enabled, deferred, halted, rolled back, and
  unchanged outcomes.
- **FR-014**: The feature MUST update current product status and deployment
  notes so future dashboard, access, sharing, retention, and deletion slices
  can determine whether RLS is implemented-only or live-enforced.
- **FR-015**: The feature MUST update the changelog for any release-readiness,
  operational, security, or documentation change it implements.
- **FR-016**: The feature MUST not add product UI, customer settings, workspace
  admin bypass, dashboard behavior, sharing/download behavior, retention or
  deletion execution, desktop upload behavior, MediaScribe behavior, or
  automatic live production enforcement.
- **FR-017**: The feature MUST keep logs, diagnostics, evidence, comments, and
  docs free of transcript text, raw audio, object keys, tokens, signed URLs,
  passwords, live secret paths, and customer meeting content.
- **FR-018**: The feature MUST preserve the blocked-access API contract from
  `031`: cross-tenant reads are not found or empty, cross-tenant mutations are
  authorization failures, and missing tenant context is an auth/context
  failure.

### Key Entities *(include if feature involves data)*

- **RLS Enforcement Verdict**: The current decision state for live production
  RLS enforcement, including status, gate summary, target, and timestamp.
- **Operator Decision Record**: Metadata-only record of who chose enable,
  defer, halt, or rollback, with evidence references and open risks.
- **Gate Evidence Package**: References to local, disposable database,
  production-like, post-change, rollback, and forbidden-content scan results.
- **Production Target Fingerprint**: Metadata that identifies the intended
  environment without storing credentials, secret paths, or customer data.
- **Rollback/Halt Record**: Metadata-only state for a stopped or reversed live
  enforcement attempt, including residue and follow-up owner.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of required gates must have current, metadata-only evidence
  before the verdict can become `ready_for_operator_decision`.
- **SC-002**: 100% of incomplete, stale, failed, inconclusive, or
  forbidden-content evidence packages must block enable decisions.
- **SC-003**: 100% of accepted live enable decisions must include actor,
  timestamp, target environment, evidence references, halt criteria, rollback
  reference, and open-risk fields.
- **SC-004**: 100% of final feature closeout outcomes must state exactly one
  live enforcement state: enabled, deferred, halted, rolled back, or unchanged.
- **SC-005**: 100% of post-change validation runs must include same-tenant,
  cross-tenant, missing-context, worker-context, and maintenance-context probe
  outcomes before success is claimed.
- **SC-006**: 0 tracked evidence files, logs, docs, or comments may contain
  transcript text, raw audio, object keys, tokens, signed URLs, passwords, live
  secret paths, or customer meeting content.

## Assumptions

- Feature `031-rls-hardening` remains accepted and is the source of RLS policy,
  context, probe, and ADR behavior.
- The live production service remains on the current `2brain.dev` Rec stack
  unless a later plan records a different approved target.
- The safest default is to leave live enforcement unchanged until all gates
  pass and the operator explicitly records a decision.
- Production validation evidence is metadata-only and must be safe to commit
  or summarize without exposing customer content or secrets.
- Future `016`, `017`, and `018` product slices may proceed only with truthful
  knowledge of whether RLS is implemented-only or live-enforced.
