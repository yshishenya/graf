# Contract: Deletion Lifecycle

Feature: `018-retention-deletion-execution`
Date: 2026-06-16

## Ownership

Deletion and retention lifecycle policy is owned by the Rec server. Browser and
desktop clients can request deletion, view lifecycle/report state, and
acknowledge local purge tasks. They must not implement their own deletion
policy, expose dependency credentials, or infer deletion completeness from local
state alone.

## Required Decision Order For Manual Deletion

1. Authenticate the actor and resolve tenant/workspace/device context.
2. Resolve the meeting without exposing private content to unauthorized actors.
3. Verify owner/admin permission for whole-meeting deletion.
4. Verify the meeting is not already deleting/deleted or blocked by policy.
5. Persist `MeetingDeletionRequest`.
6. Persist metadata-only lifecycle audit event and initial report state.
7. Set the meeting lifecycle to `requested`/`deleting`.
8. Block normal review/share/download/export routes.
9. Run active server purge and artifact state updates.
10. Create local purge tasks for relevant registered devices.
11. Update backup/dependency/post-egress report state.

If steps 5 or 6 fail, deletion fails closed and no destructive action may run.

## Access Blocking Rules

Once a meeting has `deletion_state != none`:

- normal list routes hide the row by default;
- normal detail routes show a deletion report for authorized owner/admin users;
- transcript, notes, audio, share, download, and export routes do not return
  original content;
- share links resolve to deleted/deleting state or bounded not-found state;
- direct artifact destinations return unavailable/deleted lifecycle responses
  without private content or object metadata.

Unauthorized actors must not learn whether the meeting exists.

## Active Server Purge Classes

The server must purge, lifecycle-mark, or explicitly fail these classes when
present:

- stored audio objects and `track_artifacts`;
- transcript rows;
- diarization rows;
- notes/summary/action item rows that exist in accepted slices;
- export packages and package manifests;
- share grants and share-link tokens;
- temporary upload objects and retry queues;
- processing workflow and temporary payload accounting;
- search/index entries that exist in accepted slices.

Metadata-only audit events and deletion reports are retained.

## Dependency Truth

Reports must include the following classes:

- MediaScribe: `not_submitted`, `submitted_delete_supported`,
  `delete_requested`, `delete_confirmed`, `retention_window_pending`,
  `delete_not_supported`, `unknown`.
- Langfuse: `metadata_only`, `content_bearing_deletion_required`,
  `delete_requested`, `delete_confirmed`, `disabled`, `not_applicable`,
  `unknown`.
- Backups: `pending_expiry`, `expiry_complete`, `crypto_erased`,
  `unsupported`, `unknown`, `not_applicable`.
- Post-egress copies: `outside_2brain_control` for delivered downloads,
  exports, copied files, or external recipients.

The report must never claim full external purge unless the dependency supports
deletion and confirmation was recorded.

## Retention Job Rules

Retention scan must:

- load or create a retention policy snapshot;
- fail closed when policy is missing or unsafe;
- skip meetings that are processing, already deleting, already deleted, or
  policy blocked;
- create the same deletion request/report shape as manual deletion for eligible
  meetings;
- record skipped and blocked reasons as metadata-only lifecycle audit events.

## Retry Rules

Retryable failures can be retried by an owner/admin/operator route only when:

- the request has `retryable_failed`;
- the previous failure reason is safe and non-content-bearing;
- no newer active deletion request exists for the same meeting;
- required audit/report state can be persisted before retry.

Terminal failures remain visible in the report and cannot be silently converted
to complete.

## Forbidden Data

Lifecycle API responses, reports, audit metadata, logs, screenshots, and
tracked evidence must not include:

- transcript text or summary content;
- audio bytes or file-derived private hashes;
- participant names from private content;
- object-storage keys or local filesystem paths;
- signed URLs, bearer tokens, API keys, passwords, credentials;
- raw dependency/provider response bodies;
- MediaScribe external job identifiers unless safely redacted.

## UI Requirements

The cabinet must expose:

- bounded confirmation copy: "Delete this meeting everywhere 2brain Rec
  controls" or equivalent;
- report state after deletion starts;
- server purge, local purge, backup, dependency, and post-egress limit rows;
- retryable vs terminal failure distinction;
- compact embedded desktop layout without hiding lifecycle truth.

The UI may use dense meeting list, toolbar, modal, and report concepts observed
in Krisp references, but must use 2brain Rec wording and visual treatment.
