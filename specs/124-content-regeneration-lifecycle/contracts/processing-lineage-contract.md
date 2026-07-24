# Contract: Processing Lineage and External Work

## Source fence

Every processing request records an immutable tuple:

```text
(workspace_id, meeting_id, media_revision_id, source_fingerprint, run_id)
```

The tuple is present in local workflow/job/result records and in every worker
payload. A callback whose tuple does not match the row it would update is a
safe no-op with a metadata-only audit event.

## Provider submission

1. Validate the selected immutable media revision and source artifacts.
2. Commit a durable processing run and dispatch intent with an idempotency key.
3. Start Temporal/provider work using that key.
4. Persist the returned external identity against the same revision-scoped run.
5. Poll/import only into a new immutable processing result identity.

If step 3 fails after step 2, the reconciler retries or produces a terminal safe
state. The browser is never the durable dispatcher.

## Import idempotency

- Same normalized payload hash for the same run returns the existing result.
- Different normalized hash creates a new result and new segments.
- Existing segments are never deleted to make room for a later payload.
- Outcome generation is notified with the new result fingerprint, not only the
  meeting ID.

## Retry classification

| Error class | Automatic behavior | User state |
|---|---|---|
| timeout, 429, transient 5xx | bounded retry with same idempotency key | `Обрабатывается` / retryable |
| malformed provider payload | terminal block, no retry loop | `Не удалось обработать` |
| missing/deleted artifact | blocked, no provider call | concrete prerequisite |
| auth/permission/policy | terminal/blocked, owner action | concrete next step |
| deletion epoch changed | cancel/no-op | `Удаляется` or unavailable |

## Meeting aggregate

Meeting processing status is derived from the active/current source run. A late
terminal transition from a previous revision cannot overwrite the aggregate
status for a newer revision.

## Concurrency

Database uniqueness/locks protect active run/job creation for the complete source
identity. A pre-check followed by insert is not sufficient. Worker retries use
the same run/job rows and never fall back to a meeting-wide legacy row once a
revision-scoped row exists.
