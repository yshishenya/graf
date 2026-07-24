# Data Model: Meeting Content Regeneration Lifecycle

This model separates the identities that are currently conflated by
meeting-wide workflow/job uniqueness. It is a design contract, not a migration
script. All rows are workspace-scoped and must remain covered by RLS.

## Identity axes

```text
Meeting
  └─ MediaRevision (immutable source package)
       └─ ProcessingRun (one provider orchestration attempt)
            └─ ProcessingResult (immutable imported payload + result fingerprint)
                 ├─ TranscriptSegment / DiarizationSegment
                 └─ OutcomeCandidate / AcceptedOutcome
                      └─ OutcomeItem

TemplateVersion ───────────────┘
GeneratorConfigVersion ────────┘
DeletionFence / DispatchIntent guard every asynchronous edge.
```

A numeric display version may exist for user copy, but it never replaces the
stable IDs and hashes below.

## Entities

### MediaRevision

Existing immutable source entity. Required lifecycle rules:

- identity: `(workspace_id, meeting_id, media_revision_id)`;
- monotonic `revision_number` per meeting;
- source kind, manifest fingerprint and per-track fingerprints;
- accepted/blocked/superseded/deleted state;
- no downstream processing row may point to a different revision after creation.

### ProcessingRun

Revision-scoped orchestration identity.

| Field | Rule |
|---|---|
| `id` | Stable immutable run ID |
| `workspace_id`, `meeting_id`, `media_revision_id` | Required and immutable |
| `workflow_id`, `workflow_run_id` | External correlation; old callback is fenced |
| `status`, `attempt_count`, `reason_code` | State machine with retry classification |
| `source_fingerprint` | Captures the selected revision/input set |
| `deletion_epoch_at_start` | Rejects late completion after tombstone |
| timestamps | Start, last transition, terminal end |

Uniqueness: one active run per `(workspace, media_revision, source_fingerprint,
purpose)`; historical terminal runs remain queryable. A new run for a new
revision never updates the old run row.

### ProviderJob

Revision/run-scoped external provider identity.

| Field | Rule |
|---|---|
| `id`, `processing_run_id` | Stable local identity |
| `media_revision_id`, `source_fingerprint` | Immutable source fence |
| `external_job_id` | Unique within workspace/provider, never reused across revisions |
| `request_mode`, track artifact IDs | Snapshot of actual provider input |
| `status`, `last_error_code` | Provider state plus safe reason code |
| `idempotency_key` | Same request retries reuse this key |
| timestamps | Submission, poll, ready, failure |

The provider job must not be located by meeting alone.

### ProcessingResult

Immutable normalized provider payload.

| Field | Rule |
|---|---|
| `id`, `processing_run_id`, `media_revision_id` | Immutable lineage |
| `source_result_hash` | Hash of normalized source/result payload |
| `provider_result_version` | Provider-provided version, informational only |
| status fields | transcript, diarization, summary availability |
| counts/language | Safe derived metadata |
| `imported_at`, `created_at` | Historical timestamps |
| failure reason/source | Bounded safe diagnostic |

Uniqueness: `(workspace_id, processing_run_id, source_result_hash)`; a changed
hash creates a new result, while identical redelivery returns the existing row.
Transcript and diarization segments reference this result ID and are never
deleted/replaced by a later import.

### OutcomeCandidate

The generated but unpublished variant. This corresponds to the existing outcome
set/attempt split and may be implemented by extending those records.

| Field | Rule |
|---|---|
| `candidate_id` | Stable idempotency identity |
| source IDs/hash | Pins media revision + processing result fingerprint |
| template key/version/id | Immutable template provenance |
| generator/config/prompt/model fingerprints | Reproducibility metadata; no secret material |
| `status` | queued, dispatching, generating, ready, accepted, rejected, failed, stale, expired, blocked |
| `requested_by`, timestamps | Owner or product automatic actor |
| `preview_available` | Owner-only read-only projection gate |
| `supersedes_candidate_id` / `supersedes_outcome_id` | Optional lineage link |
| `deletion_epoch_at_start` | Tombstone fence |
| `workflow_id`, `workflow_run_id` | Durable dispatch correlation |

Uniqueness: one active candidate for the full idempotency key
`(workspace, meeting, source result hash, template version, generator/config,
request intent)`. A manual “refresh same format” uses a new intent ID and may
create a new candidate after the previous one reaches a terminal state.

### AcceptedOutcome

The one outcome published by the meeting current pointer. It may remain the
same physical outcome-set row with lifecycle state, or be represented by a
dedicated pointer row during migration.

Rules:

- at most one current accepted pointer per `(workspace, meeting)`;
- pointer changes only in the same transaction as optimistic source/current/
  deletion fence validation;
- previous current becomes `superseded`, never deleted by accept;
- candidate ready/rejected/failed rows are not current;
- all detail/list/export/share projections use this pointer.

### TemplateVersion

Immutable built-in or personal format definition.

- `(workspace, template_key, version)` is unique;
- editing creates a new version rather than mutating a referenced version;
- archive/delete excludes a version from new requests but does not break old
  outcome rendering;
- candidate stores the exact template version ID and safe display name.

### DispatchIntent

Durable handoff between DB intent and Temporal/provider start.

| State | Meaning |
|---|---|
| `created` | Candidate/run committed; no external start confirmed |
| `dispatching` | Reconciler owns a bounded attempt |
| `started` | External workflow identity persisted |
| `retryable_failed` | Eligible for scheduled retry |
| `terminal_failed` | No automatic retry; owner/operator action |
| `cancelled` | Deletion/policy fence won |
| `completed` | External work reached terminal local state |

The intent contains only metadata-safe payload references, an idempotency key,
attempt count, next-attempt time, safe failure code and source/deletion fences.

### DeletionFence

Monotonic meeting/workspace lifecycle guard.

| Field | Rule |
|---|---|
| `meeting_id`, `workspace_id` | Scope |
| `epoch` | Increment or otherwise monotonically advances at deletion/retention/access terminal transition |
| `state` | active, requested, deleting, purged, blocked, complete |
| `requested_at`, `completed_at` | Audit timestamps |
| `content_retention_policy` | Explicit `graf_controlled_purge` versus `observability_retained` classification |

Every processing/generation/accept/export action captures the epoch at start and
checks it immediately before/after external egress and before commit.

### GenerationCall retention projection

The existing content-bearing `GenerationCall` is an explicit retained
observability artifact for the internal MVP, not a metadata-only audit row:

- retain the exact request/transcript/raw response required by the constitution,
  with operator-approved retention and destination policy;
- keep correlation, token/cost summary, hashes, safe reason codes and delivery
  status so one completed call is delivered exactly once without repeating
  inference;
- meeting deletion purges GRAF-controlled transcript/outcome/object copies and
  blocks new work, but does not delete completed GenerationCall, Langfuse or
  Temporal content; deletion reports name this boundary clearly;
- ordinary logs, audit events, diagnostics and committed evidence remain
  metadata-only and never duplicate the retained content.

## State transitions

### Candidate

```text
created → queued → dispatching → generating → ready
   ├──────────────────────────────→ blocked
   ├──────────────────────────────→ failed_retryable → dispatching
   ├──────────────────────────────→ failed_terminal
   ├──────────────────────────────→ stale (source/current/deletion fence)
   ├──────────────────────────────→ expired
ready → accepted (atomic pointer switch)
ready → rejected/dismissed (current unchanged)
```

### Processing run

```text
created → starting → submitted → polling → importing → processed
   ├──────────────────────────────→ failed_retryable → submitted/polling
   ├──────────────────────────────→ failed_terminal
   ├──────────────────────────────→ blocked (missing/invalid/policy/deletion)
   └──────────────────────────────→ canceled (deletion fence)
```

### Deletion

```text
active → requested → deleting → active_purge_complete
                         ├────→ retryable_failed → deleting
                         ├────→ terminal_failed
                         └────→ pending_backup_expiry → complete
```

Late work after `requested` is blocked even if the provider reports success.

## Derived projections

- `current_outcome`: pointer-selected accepted outcome only;
- `candidate_status`: owner-only candidate state plus format name and next action;
- `processing_status`: source/result-scoped aggregate, never a late old-run
  overwrite of the meeting;
- `deletion_report`: per-artifact controlled/purged/retained/unknown state with
  explicit GRAF boundary;
- `export_snapshot`: captures current outcome ID/result hash at action start and
  rejects or retries if the pointer changes before publication.

## Migration/backfill rules

1. Expand schema with nullable lineage/fence/dispatch fields.
2. Backfill legacy workflow/job rows to a `legacy:<run-id>` source/run identity
   and mark their exact known result hash where available.
3. Reconcile only rows with one fully attested accepted revision; block
   duplicate/ambiguous rows before enforcing new uniqueness.
4. New writes use revision-scoped constraints and pointer-only projections.
5. After a verified compatibility window, enforce non-null fields for new rows
   and remove fallback-to-meeting lookup from stores.
6. Rollback must preserve old rows and disable new dispatch safely; never mutate
   historical result content to fit the old shape.

## Privacy and RLS invariants

- Every content row and candidate projection is workspace-scoped and checked by
  the existing access decision before render/export/share.
- Shared viewers cannot discover candidate IDs, format settings, prompt/model
  metadata or polling URLs.
- Evidence and logs contain hashes/IDs/status/reason codes only; no raw content.
- Deletion marks content-bearing rows and object artifacts explicitly so the
  report cannot mislabel plaintext retention as metadata-only.
