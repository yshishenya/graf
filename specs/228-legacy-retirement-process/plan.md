# Implementation Plan: Управляемое поэтапное retirement legacy

**Branch**: `codex/228-legacy-retirement-process`
**Date**: 2026-08-31
**Spec**: [spec.md](spec.md)
**Risk / validation lane**: Significant feature — shared governance,
compatibility and release surfaces.
**Release gate**: No deploy/release in this feature. Any resulting runtime
slice must pass its own quickstart, exact-SHA fast CI, review, frozen candidate
and one authoritative Full CI before release consideration.

## Audit Baseline (read-only, 2026-08-31)

| Source | Verified fact | Planning consequence |
|---|---|---|
| Feature 216 contract | Every feature has `remove`, `retain-with-exception`, or `untouched`; protected migration/Temporal/client-update boundaries require their own cutover feature. | Reuse this contract; do not create a competing definition. |
| Current validator | `scripts/validate-legacy-impact.py` validates one classification and fields on an exception, but it does not maintain an inventory, path taxonomy, registry status, or slice safety contract. | Add only bounded, test-first extensions. |
| Feature 220 branch | `codex/220-legacy-retirement` is a documentation-only draft outside current `HEAD`; it proposes inventory, finite exceptions and slices but contains no implementation/evidence. | Treat it as input, not merged policy or proof. Reconcile rather than blindly merge. |
| `codex/206-legacy-cleanup` | It has no unique commits relative to current base and is materially behind it. | Do not revive it; classify real current compatibility from current code. |
| Feature 206 recovery | Current processing contracts preserve historical `processed`/workflow compatibility and Temporal replay identities. | Inventory must make it a protected candidate; no generic cleanup may remove it. |
| Current source scan | Observed candidates include serialized media filenames, `legacy_backfill` normalization, historical processing workflow IDs, a disabled legacy-header auth guard, MediaScribe dual-track drain, and `compatibility_099` rollback/deploy logic. | They are candidates, not approved deletion targets; owner/reviewer classification is required. |
| Release policy | Changelog fragments have one feature writer; only release operator edits root changelog. One Full CI is authoritative only for frozen exact candidate SHA. | Legacy evidence must reuse fragment and release-train contracts. |
| Agent guidance | Root `AGENTS.md` is a small router and active context comes from `.specify/feature.json`/active artifacts. | Store long-lived legacy policy in one scoped file and per-contour detail in active slice artifacts. |

## Constitution Check

- **Pass**: no capture, auth, privacy, deletion, database, Temporal or macOS
  runtime change is planned in this Feature.
- **Pass**: production data, migration pointers, Temporal history and public
  signing/update continuity are explicit protected boundaries.
- **Pass**: no root `CHANGELOG.md` or mutable active-feature content in root
  `AGENTS.md`; the Feature owns only its fragment and artifacts.
- **Gate for implementation**: reviewer-owned requirement/infra checklists must
  remain unchecked until reviewed; `speckit-analyze` must report no unresolved
  Critical/High finding before implement.

## Target Design

### 1. Versioned registry and deterministic inventory

Create one repository-level schema and an accepted registry that stores only
metadata. Discovery produces candidate contours deterministically, then a
reviewer/owner converts a candidate to `remove`, `retain-with-exception`,
`untouched`, or `blocked`. A discovery match never proves that code is dead.

The record model is intentionally small:

```text
LegacyContour
  contour_id, category, source_path, source_digest, source_sha
  status(candidate|approved|blocked|retired)
  classification(remove|retain-with-exception|untouched)
  owner, risk, rationale, evidence, linked_feature, linked_issue

LegacyException
  contour_id, compatibility_boundary, reason, owner, expiry
  removal_trigger, validation, retirement_task

RetirementSlice
  feature_id, contour_ids, scope_fence, protected_domain
  rehearsal, abort_conditions, rollback_target, validation_evidence
```

The generated report has a stable digest and no content-bearing fields. The
registry does not replace `tasks.md`; it points to the task/issue that owns the
next action.

### 2. Taxonomy with false-positive boundaries

Discovery covers aliases, fallback names, flags, deprecated configuration,
dependencies, fixtures/tests, documentation, migrations, Temporal workflow
identity/history, media compatibility and macOS/Sparkle/update paths. It must
distinguish active behavior from archival release notes, evidence, tests that
prove past removal and normative prohibition of reintroduction. Suppression is
not a free-form allowlist: any accepted exclusion needs a rationale and owner.

### 3. Safe retirement protocol

Each approved removal starts from a fresh Feature ID and follows the full
Spec Kit path. A slice is constrained to one compatibility boundary; a common
boundary can group contours only when the same rollback and validation prove
the whole group safe. Protected-domain matrix:

| Domain | Minimum additional evidence before approval |
|---|---|
| Migration / persistent data | expand-contract plan, isolated backup/restore rehearsal, abort and rollback; no manual pointer mutation |
| Temporal | deterministic replay/idempotency result, history compatibility decision, no history deletion |
| Historical MediaScribe/media artifacts | source-data cutoff, exact canonical-source rules, truthful unavailable outcome, bounded cleanup path |
| macOS / Sparkle | bundle ID/Developer ID/designated-requirement continuity, notarized rollback and appcast check |
| Deploy rollback | target compatibility contract and release gate evidence; no production run from the inventory feature |

### 4. Agent and GitHub workflow

The reusable harness validates a short fixed sequence:

```text
allocate Feature ID → create umbrella issue → specify/clarify/plan/checklist/tasks
→ analyze → task-to-issues → implement one slice → fast CI on exact SHA
→ merge → freeze release train → one Full CI → release decision
```

Root instructions provide only this router and links. Scoped legacy guidance
contains the taxonomy and how to open a slice; active feature artifacts contain
the one contour record, current task and paths. Change fragments avoid a shared
changelog write target.

## Implementation Approach

1. Reconcile Feature 220 documents against current `HEAD` and convert the
   result into a registry v1 contract; do not copy its unverified inventory as
   fact.
2. Write tests first for metadata safety, deterministic discovery, exception
   expiry, changed-path classification and protected-domain routing.
3. Implement the smallest stdlib-based inventory/registry validators and wire
   them to existing governance checks without scanning user/production data.
4. Add a narrow scoped guidance file, PR/issue templates and portable harness
   templates; keep root `AGENTS.md` and root changelog conflict-free.
5. Seed only observed candidates with `candidate`/`blocked` status, then ask
   owner/reviewer to classify each before child removal issues are created.
6. Run analysis/convergence, exact-SHA fast CI and attach metadata-only
   evidence. Do not perform a removal or release in this Feature.

## Planned Repository Surface

```text
governance/legacy/registry.v1.yaml
governance/legacy/registry.schema.json
scripts/legacy-inventory.py
scripts/validate-legacy-registry.py
scripts/validate-retirement-slice.py
scripts/check-development-process.py
tests/governance/test_legacy_inventory.py
tests/governance/test_legacy_registry.py
tests/governance/test_retirement_slice.py
docs/agent-guidance/legacy-retirement.md
docs/agent-guidance/README.md
.github/pull_request_template.md
specs/228-legacy-retirement-process/
changes/unreleased/F228.yaml
```

The reusable portions (schemas, generic validators, receipt/template contracts
and bounded skill) are extracted to `graf-development-harness` only after the
GRAF-specific policy is proven. Product-specific capture/privacy/MediaScribe/
Temporal/Apple requirements remain in GRAF.

## Validation Plan

1. `python3 scripts/validate-agent-context.py`
2. Focused governance tests for the new registry/inventory/slice validators.
3. Determinism run twice on the same exact source SHA; inspect JSON for
   forbidden content fields and stale-SHA behavior.
4. `python3 scripts/check-development-process.py --self-test`
5. `PYTHONDONTWRITEBYTECODE=1 pytest -q tests/governance`
6. Feature quickstart, then `infra/scripts/ci-local.sh --fast` once on the
   PR-ready exact SHA.
7. `$speckit-analyze`, `$speckit-converge`, GitHub task-to-issues and reviewer
   checklist review before implementation closeout.

Full CI, production CD, database repair, Temporal mutation and release
publication are expressly absent from Feature 228. They occur only for a
frozen future release candidate under the release operator's approval.

## Risks and Controls

| Risk | Control |
|---|---|
| False positive leads to removal of live behavior | Candidate status plus owner/reviewer approval and domain-specific slice before removal. |
| Inventory leaks meeting/private data | Metadata-only schema, forbidden-field tests and no production/data traversal. |
| Compatibility exception becomes permanent | Required owner/expiry/trigger/task; expired or incomplete records fail closed. |
| Huge cleanup PR creates unreviewable blast radius | One boundary per independently testable slice; root feature does no deletion. |
| Migration/Temporal/Sparkle break rollback | Protected-domain routes require dedicated rehearsal and separate release gate. |
| Agent context causes stale/conflicting work | Stable root router; active path and contour data are scoped, no mutable feature state in `AGENTS.md`. |
| CI cost/race returns | Fast CI per exact PR SHA; one Full CI after candidate freeze, no restart on unrelated worktree commits. |
