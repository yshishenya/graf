# Implementation Plan: Meeting Content Regeneration Lifecycle

**Branch**: `124-content-regeneration-lifecycle` | **Date**: 2026-07-23 | **Spec**: [spec.md](./spec.md)

## Summary

Feature 124 establishes one trustworthy lifecycle for meeting content:
immutable media and processing inputs, revision-scoped provider work, durable
candidate generation, one authoritative accepted outcome pointer, explicit
owner-only preview/accept, and deletion-safe recovery. The implementation will
repair the current root causes found by the independent business, systems, and
UX audits instead of adding isolated UI guards:

- processing workflows and provider jobs become scoped to the actual media
  revision/result rather than the meeting alone;
- importing a changed provider payload creates a new immutable result identity,
  never an in-place segment rewrite;
- outcome reuse is fingerprinted by source result, template and generator
  provenance, while the meeting current pointer is the only published truth;
- candidate dispatch is durable across a DB commit/Temporal outage and accepts
  only with source/current/deletion fences;
- deletion blocks late work and reports the constitutionally required retained
  Generation Call/Langfuse/Temporal content separately from controlled GRAF
  purge; ordinary logs and evidence remain metadata-only;
- owner UI gets a safe candidate preview, named format status, bounded polling
  and explicit refresh recovery.

The slice intentionally does not add a full history/compare/revert UI or change
native capture. It leaves lineage sufficient for that follow-up and keeps the
Feature 122 meeting-list contract compatible.

## Technical Context

**Language/Version**: Python 3.13 server, FastAPI, SQLAlchemy async, Alembic,
Jinja/HTMX and dependency-free cabinet JavaScript; Temporal Python SDK; Swift
macOS shell unchanged.

**Primary Dependencies**: Existing PostgreSQL/RLS models and migrations, MinIO
storage, Temporal workflows, MediaScribe client, current cabinet templates and
static assets. No new runtime dependency is planned.

**Storage**: PostgreSQL for immutable lineage, current pointers, attempts,
dispatch records and deletion fences; MinIO for controlled audio/artifacts;
Temporal for durable workflow execution; existing local custody remains native.

**Testing**: Focused pytest unit/contract/integration suites with isolated
PostgreSQL, static JS harnesses, migration/RLS checks, Temporal dispatch tests,
synthetic owner/shared UI contract tests, and the full `infra/scripts/ci-local.sh`
repository gate.

**Risk / Validation Lane**: High-risk architecture and user-facing workflow.
The slice changes processing, AI outcomes, deletion/privacy, public/export
truth, database lineage and accessibility, so full Spec Kit clarify,
checklists, analyze, issue sync, focused gates and repository CI are mandatory.

**Release Gate**: No deployment during planning. After implementation and clean
review: clean worktree, pinned SHA, backup/restore rehearsal, RLS gate,
`infra/scripts/ci-local.sh`, `infra/scripts/cd-remote.sh --dry-run`, explicit
production approval, then `--execute` and smoke evidence. Product release uses
CalVer `vYYYY.MM.DD.N` with Russian release notes.

**Implementation status**: The revision-scoped upload/session API, immutable
lineage, candidate/current outcome contract, source/deletion fences, generator
provenance, durable dispatch/purge reconciliation and owner cabinet recovery
paths are implemented. Automatic baseline generation intentionally uses the
built-in `graf-auto-v1` template and its pinned version/config hash in this
slice. Personal/workspace template defaults are explicit/manual only; changing
template, model or generator configuration never silently regenerates an
accepted outcome. Full history/compare/revert UI remains a follow-up.

**Target Platform**: Linux server/worker and PostgreSQL/MinIO/Temporal runtime,
authenticated browser cabinet and the same server-rendered surface embedded in
the macOS app. Native macOS capture is a non-regression boundary.

**Project Type**: Self-hosted web/API service with durable processing workers,
server-rendered review UI and native macOS capture client.

**Performance Goals**: One active candidate per idempotency key; bounded provider
retry; no foreground polling while the document is hidden; candidate status
requests back off with a finite deadline; list/detail requests keep existing
page bounds and no new client framework.

**Constraints**: Preserve workspace isolation, server-owned provider
credentials, operator-approved plaintext Langfuse/Temporal retention for
completed model calls, metadata-only ordinary logs/evidence, deletion truth,
manual start/stop capture, existing browser/embedded parity, existing
export/share ACLs and clean-room UX. Do not store private content in committed
evidence.

**Scale/Scope**: Existing meeting volume and one workspace boundary per record;
the design must support multiple media revisions, provider runs and candidates
per meeting without meeting-wide uniqueness collisions or unbounded UI polling.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Before Phase 0: PASS**

- **Capture-first integrity**: PASS. Native system-audio-first capture, manual
  controls and local custody remain authoritative and unchanged.
- **Privacy and egress**: PASS with required work. Provider calls remain server
  owned; content-bearing Generation Call/Langfuse/Temporal retention is
  explicitly classified under the operator policy; ordinary logs/evidence stay
  metadata-only and the server never stores provider credentials.
- **Deletion truth**: PASS with required work. Tombstone fencing, controlled
  purge journaling and bounded copy are mandatory; no universal erasure claim.
- **Auth/access**: PASS. Generation, preview and accept are owner-only; shared
  paths resolve only accepted current content.
- **Database/RLS**: PASS with required migration and live gate. Every new or
  changed table must remain workspace-scoped and included in RLS validation.
- **Temporal/MediaScribe**: PASS with required durable dispatch, retry and
  stale-callback fences.
- **Accessibility/UX**: PASS. Preview, status, conflict and bounded polling
  must preserve focus, keyboard and VoiceOver paths.
- **Spec-driven delivery**: PASS. This plan is a separate slice from Feature
  122; history/revert UI is explicitly deferred.
- **Ponytail**: PASS. Reuse existing models/helpers and add only the smallest
  lineage, dispatch and preview boundaries needed to make the promises true.
  Closeout review found no removable dependency, speculative abstraction or
  standard-library replacement without weakening correctness or evidence;
  net simplification opportunity: 0 lines.

**After Phase 1 design**: re-check all gates against migrations, contracts,
deletion evidence and the quickstart before tasks/analyze. Any unresolved
boundary blocks implementation.

## Validation Plan

### Requirements traceability

| Requirement group | Covered by tasks |
|---|---|
| FR-001–FR-005 | T006–T025, T037, T040, T044–T047 |
| FR-006–FR-015 | T022–T041, T046, T065–T070 |
| FR-016–FR-020 | T028, T046, T050–T055, T068 |
| FR-021–FR-025 | T013–T016, T035–T049, T059, T066–T070 |
| FR-026–FR-028 | T003, T056–T064, T075 |
| FR-029–FR-032 | T065, T068–T073 |
| NFR-001–NFR-006 | T003, T013, T057, T063, T065–T076 and plan constraints |
| SC-001–SC-010 | T017–T025, T033–T034, T035–T049, T056–T079, T080–T083 |

### Focused gates before full CI

1. Run prerequisite/placeholder checks and the Spec Kit analyze loop.
2. Run migration/model/RLS contract tests for revision-scoped workflow/job/result
   uniqueness, current pointer fencing and workspace isolation.
3. Run processing tests for duplicate requests, same-hash idempotency, changed
   hash immutable import, late callback fencing, provider retry classification
   and durable dispatch reconciliation.
4. Run outcome tests for source/template/config fingerprint reuse, owner preview,
   stale accept 409, explicit accept supersede, reject/failure preservation and
   shared/export current-only reads.
5. Run deletion tests for tombstone-vs-import/generation/accept races, truthful
   retained-observability classification and storage/DB reconciliation.
6. Run cabinet static/runtime harnesses for named-format status, preview,
   bounded backoff/hidden-tab pause, conflict refresh action and focus/a11y.
7. Run `infra/scripts/ci-local.sh` and record exact output in quickstart.

### Release/deploy gates after implementation

- clean tree and branch/ref sync;
- pinned commit and migration compatibility check;
- backup/restore rehearsal and RLS validation evidence;
- secret/privacy/evidence scan;
- `infra/scripts/cd-remote.sh --dry-run --branch 124-content-regeneration-lifecycle`;
- execute only after explicit release approval, then production health/smoke,
  rollback readiness and installed-app/server version verification.

## Phase 0 Research Decisions

Research evidence and alternatives are recorded in [research.md](./research.md).
The short decisions are:

1. Use immutable identity plus fingerprints, not mutable `result_version` alone.
2. Keep one accepted current pointer; candidates are never implicitly public.
3. Use owner-only read-only preview before accept.
4. Make DB intent and external dispatch recoverable through an outbox/reconciler.
5. Fence every late callback and destructive race with a monotonic deletion/source
   epoch.
6. Treat plaintext Generation Call/Langfuse/Temporal payloads as explicitly
   retained operator-controlled observability, not metadata-only audit; purge
   only the GRAF-controlled meeting copies.

## Project Structure

### Documentation (this feature)

```text
specs/124-content-regeneration-lifecycle/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── content-regeneration-contract.md
│   ├── processing-lineage-contract.md
│   ├── deletion-generation-contract.md
│   └── candidate-preview-contract.md
├── checklists/
│   ├── requirements.md
│   ├── security.md
│   ├── ux.md
│   ├── infra.md
│   └── ai-processing.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/src/twobrain_rec_server/
├── db/models/{ingest.py,processing.py,outcomes.py,deletion.py}
├── db/migrations/versions/00xx_content_regeneration_lifecycle.py
├── processing/{store.py,lifecycle.py,submit.py,pickup.py}
├── ingest/{processing_dispatch.py,media_revisions.py}
├── outcomes/{service.py,store.py,ai_service.py}
├── workflows/{processing_workflow.py,outcome_generation_workflow.py,worker.py}
├── deletion/service.py
├── api/{cabinet.py,processing.py}
└── cabinet/{queries.py,rendering.py,templates/,static/cabinet/}

apps/server/tests/
├── unit/{test_processing_store.py,test_outcomes_service.py,test_deletion_service.py}
├── contract/{test_cabinet_static_assets_contract.py,test_processing_contract.py}
└── integration/{test_processing_*.py,test_outcome_*.py,test_deletion_*.py}
```

**Structure Decision**: Keep existing bounded domains. Add no new frontend
framework or broad service layer. Migrations and stores own persistence
invariants; workflows own durable orchestration; cabinet owns projection and
owner interaction; deletion owns the tombstone/purge contract.

## Implementation Phases

1. **Compatibility and migration foundation**: introduce revision-scoped keys,
   current/source fences, dispatch lifecycle fields and content-retention
   classification while preserving legacy rows for migration/backfill.
2. **Immutable processing lineage**: stop in-place result rewrites, create
   revision-scoped workflows/jobs/results, make provider imports idempotent and
   fence old callbacks.
3. **Outcome candidate/current contract**: fingerprint reuse, authoritative
   current pointer, owner preview/provenance, atomic accept/supersede and stale
   conflict handling.
4. **Durable dispatch and deletion race safety**: reconcile committed intents,
   check tombstone before/after egress, classify retained observability truthfully
   and journal GRAF-controlled storage deletion for retry.
5. **Cabinet UX and accessibility**: named candidate states, preview actions,
   bounded polling/backoff/hidden pause, conflict refresh and shared-owner
   separation.
6. **Validation and release**: focused gates, full CI, Arc/ponytail loops,
   migration/backup rehearsal, PR closeout, CalVer release and production smoke.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| New revision-scoped persistence and dispatch records | Existing meeting-wide uniqueness and post-commit Temporal gap cannot prove immutable lineage or recovery | In-place mutation and pre-checks already caused stale jobs/results, so they cannot satisfy the contract |
| Deletion purge journal/reconciler | Storage deletion and DB transaction are not atomic | Deleting inline and relying on rollback leaves DB/object divergence |
| Owner candidate preview projection | Accepting unseen AI output is an unsafe user decision | Status-only candidate response cannot let the owner review the proposed result |
