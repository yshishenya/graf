# Contract: user reprocessing API

All routes use existing authenticated web, tenant, device and CSRF boundaries. Reprocessing actions additionally require `Meeting.created_by_user_id == principal.user_id`.

## POST `/api/v1/meetings/{meeting_id}/processing/reprocess`

Starts or resolves one user replacement attempt without waiting for MediaScribe.

Request:

```json
{
  "expected_workflow_id": "processing/{media_revision_id}/{attempt_ordinal}",
  "expected_media_revision_id": "uuid"
}
```

`dispatch` is `started` or `reused` when this request contacted Temporal and
may be `null` for a replayed or already active successor.

Success: `202` with the existing content-safe processing projection plus:

```json
{
  "request_result": "created",
  "attempt_ordinal": 2,
  "workflow_id": "processing/{media_revision_id}/2",
  "dispatch": "started"
}
```

`request_result` values:

- `created` — a new replacement workflow was admitted;
- `replayed` — the expected predecessor already has this immediate successor;
- `already_in_flight` — the request already points at the one active workflow.

Rules:

- the same expected predecessor returns the same immediate successor, including after a lost response;
- a predecessor older than that immediate successor returns `409 stale_meeting_view`;
- stale expected revision returns `409 stale_meeting_view`;
- shared recipients and non-owners receive the repository's non-disclosing response;
- no second provider job or quota charge is created by replay/coalescing.

Stable failures include `processing_reprocess_not_eligible`,
`processing_source_unavailable`, `processing_source_expired`,
`processing_meeting_deleting`, `processing_quota_exceeded`,
`stale_meeting_view`, `processing_temporal_unavailable` and
`processing_attempt_dispatch_unavailable`.

## GET `/api/v1/meetings/{meeting_id}/processing`

Reuse the existing route. Operational stage/retry fields come from the latest workflow. Artifact availability comes from the effective complete result, which may belong to the previous attempt.

For a replacement attempt, owner-only action fields are returned only after creator authorization. Shared views receive no recovery command metadata.

## POST `/api/v1/meetings/{meeting_id}/processing/check`

Reuse the existing same-attempt manual check.

- `schedule_generation` fences stale countdowns;
- `command_id` keeps the Temporal update idempotent;
- `Повторить сейчас` wakes the same workflow and job;
- a replacement attempt requires creator ownership;
- an already-running or newer generation returns current state without parallel work.
