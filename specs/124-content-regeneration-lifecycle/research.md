# Research: Meeting Content Regeneration Lifecycle

**Date**: 2026-07-23
**Feature**: [124-content-regeneration-lifecycle](./spec.md)
**Lane**: high-risk architecture and user-facing workflow

This research consolidates the repository evidence and the independent
business, systems and UX audits. It contains no private meeting content.

## Current-state evidence

| Area | Evidence | Finding |
|---|---|---|
| Media lineage | `apps/server/src/twobrain_rec_server/db/models/ingest.py` (`MediaRevision`) | Immutable media revisions exist, but downstream workflow/job identity is not consistently revision-scoped. |
| Processing identity | `db/models/processing.py`; `processing/store.py` | `ProcessingWorkflow` and `MediaScribeJob` are unique by workspace+meeting and fallback to an older row when a new revision is supplied. This can reuse the wrong external job and lets late old callbacks rewrite current state. |
| Result import | `processing/store.py:persist_processing_result` | A changed payload with the same job/result version deletes segments and rewrites the existing result in place. This breaks immutable result identity and can leave stale outcomes. |
| Outcome reuse | `outcomes/service.py`; `outcomes/store.py` | Reuse is keyed mainly by result identity/generator version and reusable status; the current source hash is not a complete cache fence. |
| Current pointer | `Meeting.current_outcome_set_id`, `cabinet/queries.py`, `cabinet/egress.py` | Some paths use the pointer while ordinary review/export resolves a latest row, so published truth is not uniform. |
| Candidate accept | `outcomes/ai_service.py`; `api/cabinet.py` | Candidate stores source/provenance, but accept checks a limited current pointer/deletion condition and can accept stale source after an import race. |
| Dispatch | `api/cabinet.py` summary candidate route; `workflows/temporal_client.py` | Attempt is committed before Temporal start. A start exception leaves a durable-looking queued attempt without workflow identity or reconciler. |
| Deletion | `deletion/service.py` | Outcome rows are scrubbed, but `GenerationCall` can retain plaintext request/transcript/provider payload; processing/MediaScribe work is not fenced consistently. Storage objects are deleted inside a DB transaction without a per-object journal. |
| UI recovery | `cabinet/static/cabinet/cabinet.js` | Candidate polling is fixed/indefinite; stale conflict can show no recovery action; ready status lacks format identity; candidate response has no preview content. |
| Existing contracts | `specs/121-recording-workflows/contracts/recording-workflow-contract.md` | Durable reconciliation and candidate provenance are described, but current runtime does not satisfy every contract path. |

## Decision 1: Immutable identity plus content fingerprints

**Decision**: Treat media revision, processing run/result, outcome variant,
template version and generator/config version as separate immutable identity
axes. A result fingerprint includes the source media/result hash and normalized
provider payload identity. Repeated delivery of the same fingerprint is an
idempotent no-op; a changed fingerprint always receives a new result identity.

**Rationale**: An integer `result_version` attached to one meeting-wide provider
job cannot distinguish a changed payload, a new media revision and a retried
provider request. Immutable IDs make stale callback and export checks possible.

**Alternatives considered**:

- Keep mutating one result row: rejected because segments and outcomes can be
  silently replaced while a candidate is generating.
- Increment only `result_version`: rejected because the current provider job is
  unique by meeting and can be reused for a different source.
- Store only hashes without new identity: rejected because history, deletion and
  audit need a stable row to fence and reference.

## Decision 2: One authoritative accepted pointer

**Decision**: `Meeting.current_outcome_set_id` (or its migration-safe successor)
is the only published current outcome. Every review, list projection, export,
share and public response resolves that pointer under workspace/access checks.
Candidates and superseded/failed rows are never selected by a generic “latest”
query for a published surface.

**Rationale**: A candidate may be newer than current without being trustworthy or
accepted. One pointer gives users a stable result while work happens and makes
accept/reject semantics explicit.

**Alternatives considered**:

- Always select newest generated row: rejected because a failed/partial/stale
  candidate can leak into export/share.
- Keep pointer only for AI accept while ordinary paths use latest: rejected
  because it creates two product truths.
- Delete old outcomes after accept: rejected because lineage and rollback need
  historical immutable rows.

## Decision 3: Automatic versus manual generation

**Decision**:

1. Automatic generation is limited to the first eligible baseline per unique
   source/result/template/generator key and to an explicitly approved automatic
   follow-up policy for a new source revision.
2. A new source never silently replaces current accepted content; it may create a
   candidate marked as a new variant and still requires explicit accept.
3. Manual generation requires owner authorization and an explicit format or
   `Обновить итоги` intent. Selecting the already-current format is a no-op until
   that intent is explicit.
4. Reopen, view, refresh, prompt/model deployment, or a transient UI error never
   starts a silent regeneration.

**Rationale**: Automatic work provides a useful first result without turning
  model/prompt changes into surprise destructive edits or unbounded provider
  spend. Explicit accept preserves user agency.

**Alternatives considered**:

- Auto-regenerate every time a user opens a meeting: rejected for cost, flicker
  and non-deterministic user experience.
- Auto-replace on every new transcript: rejected because manual edits/accepted
  outcomes can be lost and shared viewers can observe churn.
- Manual-only initial generation: rejected because it makes the first-run value
  unnecessarily difficult while deterministic baseline generation is safe to
  deduplicate.

## Decision 4: Candidate preview before accept

**Decision**: Owner-only candidate preview is a read-only, safe projection that
  includes the format name, source/result identity summary, generated text/items,
  truth labels and non-sensitive provenance needed for a decision. It is never
  used by shared/export/public surfaces. `Использовать` still rechecks the
  optimistic current/source/deletion fence.

**Rationale**: The current candidate response can say “ready” without showing
  what will replace the accepted outcome. Accepting unseen AI output is a trust
  and quality risk.

**Alternatives considered**:

- Status-only response: rejected by UX audit and the existing recording-workflow
  contract.
- Expose raw provider payload: rejected for privacy, stability and trust.
- Auto-publish candidate and allow undo: rejected because it creates a public
  stale window and requires an unplanned history UI.

## Decision 5: Durable dispatch and bounded retries

**Decision**: Persist an explicit dispatch intent and lifecycle before external
  workflow/provider start. A reconciler/outbox retries or terminally classifies
  the intent using the same idempotency key. UI polling is bounded/backed off and
  does not own durable progress.

**Rationale**: A DB commit followed by a Temporal start failure currently strands
  queued attempts. A durable handoff is the only way to recover across process
  restarts and network failures.

**Alternatives considered**:

- Start Temporal before DB commit: rejected because a crash can create orphaned
  external work with no local authority.
- Let the browser retry dispatch: rejected because it is not durable and fails
  when the tab closes.
- Infinite polling/retry: rejected for provider cost, load and unclear terminal
  states.

## Decision 6: Deletion fence and content retention

**Decision**: A monotonic deletion/tombstone epoch is checked before and after
  processing import, provider egress, candidate generation and accept. Late work
  becomes a safe no-op or terminal blocked state. Completed `GenerationCall`
  payloads, Langfuse observations and Temporal History remain retained plaintext
  under the constitutionally required operator policy and are reported as an
  explicit external/observability boundary; they are not metadata-only and are
  not deleted by meeting deletion. GRAF-controlled meeting copies still use a
  durable per-artifact purge state so DB and object-store retries converge.

**Rationale**: Deletion must win races without contradicting the internal-MVP
  observability contract. Inline object deletion cannot roll back with a failed
  DB transaction, and the product must distinguish controlled purge from
  retained operator-managed observability.

**Alternatives considered**:

- Treat retained plaintext observability as metadata-only: rejected because the
  constitution requires the report to name retained content explicitly.
- Rely on workflow cancellation alone: rejected because already-running
  external calls and late callbacks still exist.
- Delete objects inline and trust transaction rollback: rejected because MinIO
  deletion is irreversible while Postgres rollback is not.

## Decision 7: Migration and compatibility strategy

**Decision**: Add migration-safe nullable lineage/dispatch fields and backfill
  legacy rows to an explicit legacy source/result fence. New writes use the new
  constraints; old rows remain readable until a verified backfill and cleanup
  window. Rollout is expand → backfill/reconcile → enforce → contract cleanup,
  with backup/restore rehearsal and rollback instructions.

**Rationale**: Existing meetings and production workflows cannot be reset, and
  a direct uniqueness replacement risks downtime or data loss.

**Alternatives considered**:

- Drop/recreate processing rows: rejected as destructive and incompatible with
  deletion/history guarantees.
- Keep old and new code paths indefinitely: rejected because two lineage truths
  would persist; a bounded migration window is safer.

## Deferred decisions for planning/implementation

- Exact schema names and migration numbering.
- Whether the durable handoff uses a new outbox table or an existing audit/event
  table with a stricter state machine.
- Exact candidate preview shape and redaction rules for each outcome category.
- Bounded retry counts/time budgets per provider error class.
- Whether upload-session/part concurrency hardening is included in this slice or
  tracked as a linked P1 follow-up; it is not silently ignored.

## Research limits

- No real browser/VoiceOver session was run; UI findings are static/contract
  evidence and require runtime validation in the implementation quickstart.
- No production DB probe or destructive RLS test was run; production readiness
  remains blocked until the release gate supplies live evidence.
- No provider credentials or private meeting data were used.
