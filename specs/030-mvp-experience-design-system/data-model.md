# Data Model: MVP Product Experience And Design System

This feature defines product/design entities, state models, and handoff
artifacts. It does not create production database tables.

## MVP Experience Map

**Purpose**: Classify the first-launch product surface and connect each surface
to implementation readiness.

**Fields**:

- `surface_id`: Stable identifier such as `desktop.home` or `web.meeting.detail`.
- `surface_name`: Human-readable name.
- `surface_type`: `native_desktop`, `embedded_cabinet`, `browser_cabinet`, `handoff_entry`, or `deferred`.
- `launch_classification`: `implemented_foundation`, `required_for_first_launch`, `deferred`, or `out_of_scope`.
- `owner_user_story`: Related spec user story.
- `dependencies`: Related specs or future slices.
- `validation_gate`: Checklist or quickstart scenario that proves readiness.

**Validation rules**:

- Every launch-critical surface has exactly one launch classification.
- Capture-critical surfaces must be `native_desktop`.
- Deferred surfaces must include user impact and reason.

## Desktop Trust Shell

**Purpose**: Define native macOS surfaces that own local recording trust.

**Fields**:

- `recording_state`: Idle, permission-blocked, ready, active, stopping,
  saved-local, degraded, failed.
- `recording_start_policy`: Manual available, policy-blocked, signed-out local
  allowed, assisted auto-start unavailable, or future assisted auto-start
  policy-gated.
- `capture_indicator`: Visible state and location.
- `stop_control`: One-action stop availability.
- `local_artifact_truth`: Saved, degraded, failed, local-only, queued.
- `server_status_summary`: Signed-out, connected, stale, offline, blocked.
- `embedded_subset_entry`: Allowed entry points into server-loaded subset.

**Validation rules**:

- Stop and active recording indicator remain visible during server outage.
- Server-loaded content cannot hide, restyle, replace, or contradict
  capture-critical controls.
- Signed-out states may block upload but must not falsely imply local recording
  deletion.
- Assisted auto-start, when shown as a future setting or policy marker, must be
  visible, auditable, scoped to approved meetings or explicit user selection,
  and never described as arbitrary hidden system-audio recording.

## Server Web Cabinet

**Purpose**: Full browser product surface for uploaded meetings and account/
workspace workflows.

**Fields**:

- `route_id`: Stable route identifier.
- `primary_actor`: Owner, workspace admin, reviewer, or future shared viewer.
- `content_scope`: Meetings, upload, review, settings, admin, billing, audit,
  deletion, help/legal, sharing, downloads, or deferred.
- `desktop_visibility`: Relationship to embedded subset.
- `status_dependencies`: Upload, processing, transcription, notes, access,
  deletion, policy, or external dependency state.

**Validation rules**:

- Full browser cabinet may include routes not present in desktop.
- Browser-only routes must have a desktop handoff, hidden, or disabled behavior.
- Browser cabinet may not claim active local recording authority.

## Embedded Desktop Cabinet Subset

**Purpose**: Allowlisted server-loaded product subset inside the desktop app.

**Fields**:

- `route_id`
- `allowed_in_desktop`: Boolean.
- `allowed_reason`: Account, workspace status, recent meetings, upload,
  processing, review, basic settings, or re-auth.
- `disallowed_reason`: Browser-only, admin-heavy, legal/help, broad billing,
  public sharing, export/download management, detailed audit, or unsafe near
  capture controls.
- `native_boundary_requirements`: Persistent recording indicator, Stop, and
  local status requirements.

**Validation rules**:

- Embedded subset cannot include capture-critical controls.
- Embedded subset must expose current meeting/upload/review status truth.
- Any unknown route defaults to browser handoff or hidden in desktop.

## Browser-Only Cabinet Route

**Purpose**: Route that belongs in the full browser cabinet but not inside the
desktop recorder app.

**Fields**:

- `route_id`
- `route_name`
- `browser_url_pattern`
- `desktop_behavior`: `hidden`, `disabled`, or `handoff_to_browser`.
- `handoff_copy`: User-facing reason/action when exposed from desktop.

**Validation rules**:

- Browser-only route must never silently render inside desktop.
- Handoff copy must avoid implying that desktop app is broken.

## Cross-Surface Status Model

**Purpose**: Keep desktop and web status meanings consistent.

**States**:

- `local_recording_saved`
- `local_only`
- `queued`
- `uploading`
- `uploaded`
- `audio_extraction`
- `transcription`
- `transcript_ready`
- `notes_ready`
- `partial_degraded`
- `failed`
- `deleted`
- `access_denied`

**Fields per state**:

- `user_label_ru`
- `user_label_en`
- `meaning`
- `desktop_rendering`
- `web_rendering`
- `allowed_primary_action`
- `forbidden_claims`
- `terminality`: `non_terminal`, `terminal_success`, `terminal_failure`, or
  `terminal_deleted`.

**Validation rules**:

- Desktop and web cannot use the same label for different meanings.
- Upload success cannot imply transcript or notes readiness.
- Deleted state must say what `2brain Rec` controls and what may remain outside
  its control.

## Media Upload Flow

**Purpose**: Define uploading existing user-owned files.

**Fields**:

- `accepted_media_category`: Audio file, video/meeting file with usable audio,
  unsupported, encrypted, corrupted, duplicate, oversized, or no usable audio.
- `track_provenance`: Desktop separate microphone/system tracks, uploaded mixed
  audio, uploaded extracted audio, no usable audio, or unknown/unavailable
  speaker separation.
- `upload_state`
- `audio_extraction_state`
- `processing_state`
- `ownership_label`
- `retention_deletion_implication`

**Validation rules**:

- Common video/meeting files may be accepted only with audio-first copy.
- Full video playback and video timeline review are deferred.
- Unsupported/no-audio states must be explicit and recoverable where possible.
- Uploaded media must not imply separate microphone/system tracks or speaker
  separation unless that provenance is known.

## Owner Value Loop

**Purpose**: Prototype path proving useful end-to-end MVP value.

**Steps**:

1. First-run/sign-in or signed-out local policy state.
2. Desktop idle/ready state.
3. Record and stop in native trust shell.
4. Upload queue/current status.
5. Embedded cabinet subset or browser cabinet status.
6. Manual media upload alternative.
7. Transcription in progress.
8. Completed meeting review.
9. Degraded/failure path.
10. Deletion/access entry point.

**Validation rules**:

- The path must work from desktop and web entry points.
- The path must include at least one degraded or failure state.
- Completion must show transcript, playback context, summary, decisions, action
  items, provenance/status, and next actions.

## Meeting Review Surface

**Purpose**: Review an uploaded/processed meeting.

**Fields**:

- `meeting_identity`
- `processing_status`
- `transcript_segments`
- `playback_context`
- `summary`
- `decisions`
- `action_items`
- `source_status_provenance`
- `access_state`
- `deletion_entry_point`

**Validation rules**:

- Complete review includes transcript, playback context, summary, decisions,
  action items, source/status provenance, and clear next actions.
- Partial review distinguishes transcript-ready from notes-ready.
- Failed review explains what exists, what failed, and what the user can do.

## Design System Contract

**Purpose**: Shared design language for desktop and web.

**Fields**:

- `design_principles`
- `typography_roles`
- `spacing_density`
- `color_roles_light`
- `color_roles_dark`
- `component_families`
- `icon_rules`
- `state_badge_rules`
- `copy_tone`
- `localization_keys`
- `accessibility_rules`

**Validation rules**:

- Light/dark themes preserve contrast and non-color status communication.
- Compact desktop controls use stable dimensions and avoid text overflow.
- Icons and copy remain original to `2brain Rec`.

## Prototype Source

**Purpose**: Record visual/prototype source of truth and fallback evidence.

**Fields**:

- `source_type`: `figma` or `stitchflow`.
- `source_url_or_project_id`
- `screen_ids`
- `prototype_link_status`
- `design_system_status`
- `export_paths`
- `warnings`
- `repo_handoff_reference`

**Validation rules**:

- External prototype artifacts must have matching repo references.
- StitchFlow fallback must record project id, screen ids, DESIGN.md status,
  screenshots, HTML/code checkpoint, linking status, and warnings.
- No prototype artifact may contain secrets or real private meeting content.

## Brand-Distance Gate

**Purpose**: Prove category inspiration remains clean-room.

**Fields**:

- `allowed_category_lessons`
- `forbidden_krisp_elements`
- `screen_review_notes`
- `copy_review_notes`
- `icon_asset_review_notes`
- `verdict`: `pass`, `needs_revision`, or `blocked`.

**Validation rules**:

- Zero copied Krisp assets, UI expression, copy, icons, or proprietary behavior.
- Any benchmark screenshot/reference must be used only as internal research and
  must not be embedded into product artifacts.

## Launch Backlog Map

**Purpose**: Convert design output into follow-up implementation slices.

**Fields**:

- `candidate_feature_id`
- `feature_name`
- `priority`
- `dependencies`
- `acceptance_gate`
- `validation_evidence`
- `deferred_reason`

**Validation rules**:

- At least six implementation-ready follow-up candidates are produced.
- Each candidate maps to one or more spec requirements and success criteria.
- Deferred items include user impact and reason.
