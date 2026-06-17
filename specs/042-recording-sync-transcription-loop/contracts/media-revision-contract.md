# Contract: Media Revision Identity

Date: 2026-06-18

## Scope

Defines how `042` represents the initial accepted recording as immutable media
under one logical meeting. This is a forward-compatible contract for future
local trim, video, replace, restore, and reprocess features.

## Invariants

- One real meeting has one `Meeting`.
- One meeting may have multiple `MediaRevision` rows over time.
- `042` creates only revision `1`, source kind `initial_recording`.
- Accepted media revision content is immutable.
- Future edits create new revisions and never mutate accepted artifacts in
  place.
- Processing results and transcripts belong to a media revision.

## Server Entity

`media_revisions`

Required fields:

- `id`
- `workspace_id`
- `meeting_id`
- `local_media_revision_id`
- `revision_number`
- `source_kind`
- `status`
- `manifest_sha256`
- `track_sha256_by_role`
- `duration_seconds`
- `created_at`
- `accepted_at`
- `updated_at`

Required constraints:

- unique `(workspace_id, meeting_id, revision_number)`
- unique `(workspace_id, local_media_revision_id)`

## Initial Revision State Machine

```text
pending_upload -> uploading -> accepted
pending_upload -> blocked
uploading -> blocked
accepted -> deleted
accepted -> superseded (future feature only)
```

`042` MUST NOT create `superseded` through product UI because no edit/replace
flow exists yet.

## Binding Requirements

These records MUST include or resolve to `media_revision_id`:

- upload sessions;
- accepted temporary upload objects when attributable;
- track artifacts;
- manifest snapshots;
- processing workflows;
- MediaScribe jobs;
- processing results;
- transcript/diarization segments through processing result;
- lifecycle/deletion accounting rows;
- audit metadata where safe.

## Processing Workflow Identity

Workflow id format:

```text
processing/<media_revision_id>
```

Rules:

- Duplicate pickup for the same accepted revision reuses the open workflow.
- Successful imported result for the same revision is reused or reported, not
  duplicated.
- Future reprocess of a new revision uses a different `media_revision_id`.

## Conflict Rules

Conflict states are visible and manual-only when:

- local checksum differs from accepted revision checksum;
- server has an accepted revision for the same local key with different
  immutable metadata;
- deleted/revoked server meeting is encountered during desktop reconciliation;
- processing result belongs to a different revision than the desktop item is
  opening.

## Out Of Scope

- No local media editing UI.
- No transcript text editing.
- No speaker assignment editing.
- No video track runtime behavior.
- No destructive server-side mutation of accepted media.
