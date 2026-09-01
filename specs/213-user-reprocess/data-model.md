# Data Model: повторная обработка записи пользователем

## Existing entities reused

### Meeting

No new meeting publication pointer is added. The latest accepted media revision and the shared complete-result selector remain the customer-content boundary.

Authorization for the action is the existing creator relationship:

`Meeting.created_by_user_id == authenticated principal.user_id`.

### ProcessingWorkflow

Reuse the existing durable attempt row, active-attempt indexes, source fingerprint, deletion epoch, retry schedule and manual-command generation.

Constraints:

- one active workflow per existing meeting/revision/purpose/source constraint remains authoritative;
- the request carries the workflow ID observed by the page;
- that workflow may create at most its immediate successor;
- a repeated request for the same predecessor returns that successor, even after it has completed;
- a request older than the immediate predecessor fails as a stale meeting view.

The existing workflow row UUID is carried as `processing_workflow_id` in every new Temporal payload. It is not a second entity.

### ProcessingResult

No new field or publication table is added. A result is customer-visible only when it wins the shared effective selector:

1. current workspace, meeting and accepted media revision;
2. explicit workflow lineage;
3. `complete_processing_result_clause()` passes;
4. newest `ProcessingWorkflow.attempt_ordinal`;
5. newest `ProcessingResult.result_version` and existing deterministic tie-breakers.

Partial transcript, missing/empty diarization, stale workflow, old revision and deleted meeting never win.

### MediaScribeJob

Reuse the attempt-scoped job and idempotency key. A new replacement workflow creates a new job. Automatic retry and `Повторить сейчас` keep the same workflow and job.

### Outcome set and summary slot

Reuse current outcome publication pointers and CAS. An outcome is aligned when its `processing_result_id` equals the current effective complete result. Otherwise it remains readable with `По предыдущей версии расшифровки`.

## State transitions

### Request admission

```text
owner request
  → compare expected workflow with the locked attempt chain
  → return its existing immediate successor
  → create new replacement attempt
  → reject stale revision / missing source / unauthorized request
```

### Customer-visible transcript

```text
complete result A
  → attempt B active or partial; selector remains A
  → attempt B complete; selector becomes B
  → attempt B terminal/stale/deleted; selector remains A
```

### Outcomes

```text
result A + outcomes A
  → result B + outcomes A (previous-version label)
  → result B + outcomes B
```

## Transaction boundaries

### Admission

1. Authenticate the principal and lock the meeting.
2. Verify creator ownership, accepted media revision and source availability.
3. Resolve the expected predecessor and its immediate successor under existing workflow locks.
4. Create one successor workflow when needed.
5. Reuse revision-scoped quota reservation.
6. Commit the durable workflow-start state before the Temporal RPC.

### Result import

The existing import transaction remains authoritative:

1. lock meeting;
2. reject deletion, superseded workflow and stale source revision/fingerprint;
3. persist parent result and transcript/diarization segments;
4. commit atomically.

After commit, the shared selector exposes the result only if complete.

## Migration

No schema migration or backfill is required. Existing workflow IDs, attempt ordinals and active-attempt constraints provide the admission fence.
