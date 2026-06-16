# Data Model: Meeting Dashboard Review

Feature: `016-meeting-dashboard-review`
Date: 2026-06-16

This feature primarily adds API/UI view models over existing database tables.
No new content-bearing tables are required for the MVP implementation.

## Existing Persistent Sources

- `meetings`: meeting identity, workspace, creator, title, timing, duration,
  upload/status fields, and current policy placeholders.
- `processing_workflows`: durable processing lifecycle and retry/failure state.
- `mediascribe_jobs`: MediaScribe submission/poll/import status and server-side
  dependency truth.
- `processing_results`: imported transcript/diarization/summary availability,
  language, segment counts, and import status.
- `transcript_segments`: ordered transcript text, time range, source role, and
  sequence.
- `diarization_segments`: ordered speaker labels, time range, source role, and
  speaker-segment text.
- `processing_dependency_states`: dependency/lifecycle state for future
  deletion and status truth.

## View Models

### MeetingListItem

User-facing row in the cabinet meeting list.

Fields:

- `meeting_id`: UUID.
- `title`: sanitized display string, with fallback to safe untitled copy.
- `started_at`: optional ISO datetime.
- `ended_at`: optional ISO datetime.
- `duration_seconds`: non-negative integer.
- `source`: enum `desktop_recording`, `manual_upload`, `unknown`.
- `status`: `MeetingReviewStatus`.
- `status_label`: localized display label.
- `status_reason`: optional content-safe reason.
- `primary_action`: enum `open`, `wait`, `retry_future`, `open_status`,
  `unavailable`.
- `source_roles_available`: list of `local_microphone`, `incoming_system`.
- `transcript_available`: boolean.
- `diarization_available`: boolean.
- `notes_available`: boolean; false unless accepted generation exists.
- `updated_at`: optional ISO datetime.
- `governance`: `GovernanceActionSummary`.
- `future_slots`: list of reserved affordances such as `star`, `tag`,
  `access`, `collaboration`, `more`.

Validation rules:

- Must not include raw transcript text.
- Must not include storage keys, signed URLs, workflow IDs that reveal PII, or
  MediaScribe external IDs.
- Unauthorized or cross-tenant meetings are absent, not marked as foreign.

### MeetingReview

Authorized meeting detail payload.

Fields:

- `meeting`: `MeetingListItem`.
- `provenance`: `MeetingProvenance`.
- `processing`: `ProcessingReviewState`.
- `notes`: `NotesReviewState`.
- `transcript`: `TranscriptReviewState`.
- `speakers`: `SpeakerReviewState`.
- `playback`: `PlaybackReviewState`.
- `governance`: `GovernanceActionSummary`.
- `assistant`: `AssistantSlotState`.
- `template`: `TemplateSlotState`.

Validation rules:

- Transcript text appears only when the requesting actor is authorized and the
  detail endpoint is returning `ready` or `partial` review content.
- If transcript is unavailable, `transcript.segments` is empty and UI copy must
  explain the truthful state.
- Generated notes are unavailable unless a separate accepted feature provides
  them; the detail page may show a disabled/reserved slot.

### MeetingReviewStatus

Canonical user-facing status for list and detail.

Values:

- `local_only`: desktop/local artifact not uploaded or upload truth unavailable.
- `uploading`: upload in progress.
- `submitted`: accepted by server, processing not started.
- `processing`: workflow/job running or polling.
- `ready`: transcript and diarization content available.
- `partial`: some content available, some degraded or missing.
- `blocked`: processing cannot proceed without operator/user action.
- `failed`: processing failed after accepted attempts.
- `unavailable`: server/session/dependency state prevents review.
- `deleted_future`: deletion state placeholder for later slices.

Transitions:

```text
local_only -> uploading -> submitted -> processing -> ready
                                      -> partial
                                      -> blocked
                                      -> failed
ready/partial -> deleted_future (future 018 only)
any -> unavailable when auth/session/server state prevents review
```

### ProcessingReviewState

Content-safe processing lifecycle summary.

Fields:

- `state`: `MeetingReviewStatus`.
- `stage`: optional enum `upload`, `stored`, `submitted`, `mediascribe`,
  `importing`, `ready`, `blocked`, `failed`.
- `reason_code`: optional metadata-only reason.
- `reason_label`: localized safe label.
- `content_available`: boolean.
- `transcript_available`: boolean.
- `diarization_available`: boolean.
- `summary_available`: boolean.
- `updated_at`: optional ISO datetime.
- `next_action`: enum `wait`, `retry_future`, `contact_operator`,
  `open_desktop_queue`, `none`.

Validation rules:

- No raw transcript text, raw error body, credentials, signed URLs, live paths,
  or external job IDs.

### TranscriptReviewState

Authorized transcript model for ready/partial detail.

Fields:

- `language`: optional BCP-47-ish language code or provider language string.
- `segments`: ordered list of `TranscriptSegmentView`.
- `available`: boolean.
- `degraded_reason`: optional safe reason.
- `search_enabled`: boolean.

### TranscriptSegmentView

Fields:

- `segment_id`: UUID or stable opaque string.
- `sequence`: integer.
- `start_seconds`: decimal seconds.
- `end_seconds`: decimal seconds.
- `timestamp_label`: localized `mm:ss` or `hh:mm:ss`.
- `speaker_label`: display label from diarization match or source-role
  fallback.
- `source_role`: `local_microphone`, `incoming_system`, or `unknown`.
- `text`: transcript text, only in authorized detail payload.
- `confidence_label`: optional `low`, `medium`, `high`, or `unknown`.

Validation rules:

- Segment order is ascending by `sequence` and `start_seconds`.
- Long text wraps without overlapping controls.

### SpeakerReviewState

Fields:

- `available`: boolean.
- `speakers`: list of `SpeakerLane`.
- `assignment_state`: `available`, `reserved`, `disabled`, `conflict_future`,
  or `unavailable`.
- `degraded_reason`: optional safe reason.

### SpeakerLane

Fields:

- `speaker_key`: stable opaque key.
- `label`: display label.
- `talk_time_percent`: integer 0-100.
- `source_roles`: list of source roles represented by this speaker.
- `segments`: list of time ranges for timeline lanes.
- `confidence_label`: optional safe confidence label.

### NotesReviewState

Fields:

- `available`: boolean.
- `sections`: list of `NoteSection`.
- `unavailable_reason`: `not_requested`, `processing`, `generation_future`,
  `partial_transcript`, or `policy_blocked`.

016 default:

- `available=false` unless seeded/demo fixtures provide explicitly marked
  non-private sample sections.
- Do not generate summaries or action items from transcript content in 016.

### GovernanceActionSummary

Fields:

- `share`: `GovernanceActionState`.
- `export`: `GovernanceActionState`.
- `download`: `GovernanceActionState`.
- `retention`: `GovernanceActionState`.
- `delete`: `GovernanceActionState`.

### GovernanceActionState

Fields:

- `state`: `available`, `disabled`, `planned`, `policy_blocked`,
  `browser_handoff`, or `out_of_scope`.
- `label`: localized display label.
- `reason`: safe display reason.
- `destructive`: boolean.

016 default:

- `share`, `export`, `download`, `retention`, and `delete` are not mutating.
- Deletion copy must use "Delete this meeting everywhere 2brain Rec controls"
  or a Russian equivalent that avoids universal erasure claims.

### EmbeddedCabinetRouteState

Fields:

- `route_id`: `cabinet.meetings.recent`, `cabinet.meeting.review`,
  `cabinet.meeting.speakers`, or `cabinet.processing.status`.
- `web_path`: browser route.
- `embedded_path`: desktop route.
- `allowed_shells`: list including `macos`; future `windows`, `linux`.
- `native_capture_required`: boolean.
- `offline_fallback`: safe fallback label/state.
- `blocked_reason`: optional safe reason.

Validation rules:

- Embedded web routes never expose start/stop recording controls.
- Desktop native shell remains responsible for active capture indicator, Stop,
  permission recovery, local upload queue truth, and diagnostics.

## Relationships

- `MeetingListItem.meeting_id` maps to `meetings.id`.
- `MeetingReview.processing` maps to latest matching processing workflow/job/
  result state for the same `workspace_id` and `meeting_id`.
- `TranscriptReviewState.segments` maps to `transcript_segments` for the latest
  imported `processing_result`.
- `SpeakerReviewState.speakers` derives from `diarization_segments` and meeting
  duration.
- `GovernanceActionSummary` derives from current feature scope plus existing
  meeting policy placeholder fields.

## Out-Of-Scope Persistent State

No persistent state is added for:

- public links or share invites;
- downloads/exports;
- retention schedules;
- deletion execution reports;
- generated AI notes or assistant conversations;
- contact identity mapping;
- speaker assignment persistence beyond existing labels.
