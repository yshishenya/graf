# Contract: Temporal and MediaScribe reprocessing

## Workflow input

Every processing workflow started after this feature carries the exact database attempt identity:

```json
{
  "processing_workflow_id": "uuid",
  "workspace_id": "uuid",
  "meeting_id": "uuid",
  "media_revision_id": "uuid"
}
```

Old histories may deserialize `processing_workflow_id` as missing only through a compatibility fallback. New starters must provide it.

## Start order

1. Commit the exact `ProcessingWorkflow` row and revision-scoped quota reservation.
2. Durably transition it to `WORKFLOW_STARTED`.
3. Start Temporal with the existing deterministic workflow ID and `WorkflowIDReusePolicy.REJECT_DUPLICATE`.
4. Persist run identity or use existing duplicate/ambiguous-start recovery.

The activity loads `ProcessingWorkflow.id == processing_workflow_id` and checks workspace, meeting, revision and actual Temporal workflow ID. A mismatch fails closed and cannot import a result.

## Attempt and provider rules

- Existing active-workflow indexes prevent parallel attempts.
- One new replacement attempt creates one new `MediaScribeJob`.
- Request replay and active-attempt coalescing create no provider side effect.
- Automatic retry and `Повторить сейчас` use the same workflow/job and existing `schedule_generation` fencing.
- Unknown MediaScribe POST outcome uses existing same-key reconciliation; blind resubmission is forbidden.
- MediaScribe credentials remain worker-only.

## Candidate import

The existing import transaction validates meeting deletion, latest accepted revision, source fingerprint and non-superseded exact workflow before commit. Customer readers select it only after transcript and non-empty diarization satisfy the complete-result predicate.

## Replay compatibility

- The additive payload field does not change workflow command order.
- Database reads and provider calls remain activities.
- Replay tests cover a history without `processing_workflow_id` and a new history with it.
- The compatibility fallback is removed only after no old execution remains.
- No new workflow type, child workflow, schedule or task queue is introduced.
