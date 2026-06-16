# Data Model: Access, Sharing, And Downloads

Feature: `017-access-sharing-downloads`
Date: 2026-06-16

This feature adds access/share/egress metadata over the meeting review data
accepted in feature 016. It does not create new content-bearing transcript or
audio storage.

## Existing Persistent Sources

- `meetings`: meeting identity, workspace, owner, current visibility and policy
  placeholders, lifecycle status, title, timing, duration.
- `workspace_memberships`: active viewer membership and role.
- `user_identities`: authenticated user identity and active/deactivated state.
- `track_artifacts`: stored local microphone/system audio artifact metadata and
  server-only object keys.
- `processing_results`: transcript, diarization, and summary availability.
- `transcript_segments` / `diarization_segments`: authorized detail content
  used to generate transcript/summary exports.
- Existing audit tables and redaction helpers, extended by this feature with
  cabinet access/egress audit records.

## New Persistent Entities

### MeetingShareGrant

Login-required permission granting access to one authenticated user or allowed
team scope.

Fields:

- `id`: UUID.
- `workspace_id`: UUID, required.
- `meeting_id`: UUID, required.
- `grant_type`: enum `user`, `team`.
- `grantee_user_id`: UUID, nullable; required when `grant_type=user`.
- `share_token_hash`: string, nullable; stable opaque login-required share-link
  token hash, never the raw token.
- `created_by_user_id`: UUID, required.
- `revoked_by_user_id`: UUID, nullable.
- `status`: enum `active`, `revoked`, `superseded`.
- `created_at`: datetime.
- `revoked_at`: datetime, nullable.
- `metadata_json`: metadata-only object for safe reason/source fields.

Validation rules:

- Active user grants are unique by `(workspace_id, meeting_id, grantee_user_id)`.
- `grantee_user_id` must belong to the same organization and be active.
- A revoked grant does not confer access even if an old share URL is opened.
- Team visibility must also require current active workspace membership.
- Raw share tokens are shown only at creation/copy time and are never persisted,
  logged, audited, or exposed as public content URLs.

### MeetingArtifactPolicy

Per-meeting policy snapshot for artifact egress.

Fields:

- `id`: UUID.
- `workspace_id`: UUID.
- `meeting_id`: UUID.
- `audio_download`: enum `allowed`, `owner_only`, `disabled`.
- `transcript_download`: enum `allowed`, `owner_only`, `disabled`.
- `summary_download`: enum `allowed`, `owner_only`, `disabled`.
- `package_export`: enum `allowed`, `owner_only`, `disabled`.
- `policy_source`: enum `meeting_default`, `workspace_default`, `test_fixture`.
- `updated_by_user_id`: UUID, nullable.
- `updated_at`: datetime.

Validation rules:

- Missing policy resolves to a conservative default: owner can view, downloads
  and exports are disabled unless explicitly enabled by accepted seed/policy.
- Package export cannot include an artifact class disabled by its specific
  policy.

### MeetingEgressAuditEvent

Metadata-only record for access, share, download, export, and policy denial
events.

Fields:

- `id`: UUID.
- `workspace_id`: UUID.
- `meeting_id`: UUID, nullable for privacy-preserving denied cases.
- `actor_user_id`: UUID, nullable.
- `device_id`: UUID, nullable.
- `event_type`: enum `share_granted`, `share_revoked`, `share_link_opened`,
  `meeting_viewed`, `meeting_view_denied`, `download_requested`,
  `download_completed`, `download_denied`, `export_requested`,
  `export_completed`, `export_denied`.
- `artifact_class`: enum `audio`, `transcript`, `summary`, `package`, nullable.
- `policy_reason`: string, metadata-only, nullable.
- `outcome`: enum `allowed`, `denied`, `completed`, `failed`.
- `metadata_json`: redacted metadata-only object.
- `created_at`: datetime.

Validation rules:

- Must not contain transcript text, audio bytes, participant content, storage
  keys, signed URLs, bearer tokens, credentials, raw object paths, or local
  filesystem paths.
- Share grants/revokes/downloads/exports require an audit event persisted in
  the same unit of work before the action is committed or content is returned.

### ExportPackage

Policy-filtered export request and package manifest.

Fields:

- `id`: UUID.
- `workspace_id`: UUID.
- `meeting_id`: UUID.
- `requested_by_user_id`: UUID.
- `status`: enum `requested`, `ready`, `failed`, `expired`.
- `included_artifacts`: list of `audio`, `transcript`, `summary`.
- `excluded_artifacts`: list of objects with `artifact_class` and
  `policy_reason`.
- `manifest_json`: metadata-safe package manifest.
- `byte_length`: integer, nullable until ready.
- `created_at`: datetime.
- `ready_at`: datetime, nullable.
- `expires_at`: datetime, nullable.

Validation rules:

- `included_artifacts` must be a subset of artifacts allowed by current policy
  and available lifecycle state.
- Manifest may include title, timestamps, artifact classes, hashes, and policy
  reasons, but not storage keys or dependency URLs.
- Downloading a ready export re-checks current viewer authorization before
  serving package bytes.

## View Models

### MeetingAccessState

Effective access for the current viewer.

Fields:

- `state`: enum `owner`, `team`, `shared`, `denied`, `unavailable`, `deleted`.
- `label`: localized display label.
- `reason`: safe display reason.
- `can_view`: boolean.
- `can_share`: boolean.
- `can_manage_team_visibility`: boolean.
- `can_download`: boolean.
- `can_export`: boolean.

Rules:

- Unauthorized list rows are absent.
- Unauthorized detail/share-link access returns a bounded denied/not-found
  state without private meeting content.

### SharePanelState

State for the share modal/drawer on detail routes.

Fields:

- `meeting_id`: UUID.
- `access_state`: `MeetingAccessState`.
- `team_visibility`: enum `enabled`, `disabled`, `policy_blocked`.
- `active_grants`: list of `ShareGrantView`.
- `copy_link_state`: enum `available`, `auth_required`, `disabled`.
- `public_link_state`: enum `disabled_by_default`, `policy_blocked`.

### ShareGrantView

Fields:

- `grant_id`: UUID.
- `display_name`: safe display string.
- `role_label`: `Owner`, `Team`, or `Can view`.
- `status`: `active` or `revoked`.
- `created_at`: datetime.

### ArtifactEgressState

Policy and lifecycle state for one artifact class.

Fields:

- `artifact_class`: enum `audio`, `transcript`, `summary`, `package`.
- `state`: enum `available`, `policy_blocked`, `missing`, `processing`,
  `failed`, `deleted`, `owner_only`, `audit_unavailable`.
- `label`: localized display label.
- `reason`: safe display reason.
- `action`: enum `download`, `export`, `disabled`.

### MeetingGovernanceState

Extends 016 `GovernanceActionSummary`.

Fields:

- `share`: available when viewer can manage grants.
- `download`: available only when at least one `ArtifactEgressState` is
  `available`.
- `export`: available only when package policy and artifact availability allow
  at least one included artifact.
- `retention`: planned/disabled; no execution in 017.
- `delete`: planned/disabled with truthful deletion copy; no execution in 017.

### MeetingActivityTrail

Metadata-only activity view for permitted reviewers and owners.

Fields:

- `items`: ordered list of `MeetingActivityItem`.
- `redaction_state`: enum `metadata_only`, `limited_by_policy`.

### MeetingActivityItem

Fields:

- `event_id`: UUID.
- `event_type`: display-safe event type.
- `actor_label`: safe actor display label or generic system label.
- `artifact_class`: enum `audio`, `transcript`, `summary`, `package`, nullable.
- `outcome`: enum `allowed`, `denied`, `completed`, `failed`.
- `created_at`: datetime.
- `reason`: safe policy/lifecycle reason, nullable.

Validation rules:

- Activity items must not include transcript text, audio content, storage keys,
  signed URLs, raw tokens, local paths, or dependency identifiers.

## Relationships

- `MeetingShareGrant.meeting_id` maps to `meetings.id`.
- `MeetingArtifactPolicy.meeting_id` maps to `meetings.id`.
- `MeetingEgressAuditEvent.meeting_id` maps to `meetings.id` when revealing the
  meeting id is permitted for the actor/outcome.
- `ExportPackage.meeting_id` maps to `meetings.id`.
- Effective access is derived from meeting owner, active membership, visibility,
  active share grants, lifecycle state, and workspace policy.
- Egress state is derived from effective access, artifact policy, processing
  result availability, track artifact availability, and lifecycle/deletion
  state.

## State Transitions

```text
MeetingShareGrant:
  active -> revoked
  active -> superseded

ExportPackage:
  requested -> ready
  requested -> failed
  ready -> expired

ArtifactEgressState:
  processing -> available
  processing -> failed
  available -> deleted
  available -> policy_blocked when policy changes
```

## Privacy And Evidence Rules

- Denied states must not confirm private titles, participant names, transcript
  text, summaries, artifact names, storage keys, external job IDs, or object
  paths.
- Audit metadata must be redacted and metadata-only.
- Tracked screenshots and fixtures must use synthetic meeting data.
- Export/download copy must state that files already downloaded or exported are
  outside later 2brain Rec revocation.
