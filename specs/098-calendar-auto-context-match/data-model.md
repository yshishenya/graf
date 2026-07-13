# Data Model: Calendar Auto Context Match

**Feature**: `098-calendar-auto-context-match`

**Date**: 2026-07-13

## Overview

Feature 098 reuses the 060/063 calendar source, calendar, event, participant, conference-link, audit and context-link tables. It adds only the missing durable truth:

1. a bounded recording-start attempt that proves automatic matching ran live;
2. one authoritative context state per meeting, built by extending the existing `RecordingCalendarContextLink`;
3. immutable safe title/roster/recurrence fields on that context state;
4. server-side meeting title provenance.

Provider event snapshots remain mutable future-sync inputs. Match-time context is copied into the meeting-owned context state so later provider edits cannot rewrite recording history.

## Entities

### Meeting *(existing, extended)*

Existing meeting identity and recording timestamps remain unchanged.

New fields:

- `title_source`: required string enum:
  - `user_confirmed`;
  - `calendar`;
  - `app_context`;
  - `generic`;
  - `upload_provided`;
  - `file_name_derived`;
  - `legacy_unknown`.
- `title_updated_at`: optional timestamp for the last visible title change.
- `create_request_fingerprint_sha256`: nullable SHA-256 of the canonical original
  create request, including the requested calendar attempt ID. New rows use it
  for stable idempotency after a safe calendar title replaces the submitted
  app-context title; legacy rows remain nullable and use the pre-098 comparison.

Validation rules:

- Desktop `RecordingDisplayMetadata.titleSource` maps to `user_confirmed`, `app_context` or `generic`.
- Manual upload assigns `upload_provided` when the user supplied a title and `file_name_derived` when the upload filename supplied it.
- Existing titled rows backfill to `legacy_unknown`; existing untitled rows backfill to `generic`.
- A safe calendar title may replace only `app_context` or `generic`.
- `user_confirmed`, `upload_provided`, `file_name_derived` and `legacy_unknown` are never automatically overwritten.
- A user-selected calendar correction may replace a previous `calendar` title.
- Clearing calendar context does not silently rewrite the visible title.
- Title changes never change meeting, local recording, media revision, upload session, storage object or deletion identity.
- Calendar title replacement never changes the canonical create-request
  fingerprint, so an identical retry remains idempotent while a changed title,
  timing, media identity or attempt ID conflicts.

### RecordingCalendarMatchAttempt *(new)*

A bounded server record created by the non-blocking recording-start resolve call before a server `Meeting` exists.

Fields:

- `id`: UUID primary key and opaque attempt ID returned to the desktop.
- `workspace_id`: FK to `workspaces.id`.
- `owner_user_id`: FK to `user_identities.id`.
- `device_id`: FK to `registered_devices.id`.
- `local_recording_id`: stable desktop recording identity.
- `idempotency_key_sha256`: SHA-256 of the required `Idempotency-Key`; the raw key is never stored.
- `request_fingerprint_sha256`: SHA-256 over the normalized resolve input used to reject same-key/different-payload retries.
- `recording_started_at`: client-recorded start instant used as the time anchor.
- `decision_intent`: `automatic`, `user_selected`, or `user_declined`.
- `selected_event_snapshot_id`: nullable FK, allowed only for `user_selected`.
- `attempt_state`: one of:
  - `matched_auto`;
  - `matched_user`;
  - `provisional_prestart`;
  - `ambiguous`;
  - `no_context`;
  - `skipped_private`;
  - `skipped_all_day`;
  - `skipped_stale_calendar`;
  - `calendar_unavailable`;
  - `declined_by_user`.
- `safe_reason_code`: bounded product reason enum; never provider text.
- `context_confidence`: `high`, `selected`, `ambiguous`, or `none`.
- `candidate_event_ids_json`: ordered list of at most 10 same-owner/same-workspace safe candidate UUID strings.
- `candidate_count`: integer count before the response projection is capped.
- `matched_event_snapshot_id`: nullable FK for a clear automatic or selected result.
- `matched_event_starts_at`, `matched_event_ends_at`: match-time schedule copy.
- `matched_title`: nullable safe title only.
- `matched_title_state`: `available`, `policy_hidden`, or `unavailable`.
- `matched_roster_json`: bounded list of safe roster projections; no raw email.
- `matched_roster_state`: `available`, `not_available`, or `hidden`.
- `matched_roster_count`: non-negative integer.
- `recurring_series_key_sha256`: nullable SHA-256 over workspace/source/series identity.
- `source_version_fingerprint_sha256`: nullable fingerprint of provider version evidence.
- `freshness_class`: `current`, `stale`, `latest_sync_failed`, `never_synced`, or `unavailable`.
- `matcher_version`: stable algorithm version such as `calendar_auto_match_v1`.
- `evaluated_at`: server evaluation time.
- `expires_at`: exactly `evaluated_at + 24 hours`; consumption is forbidden at or after this instant and an unconsumed attempt becomes purge-eligible.
- `consumed_by_meeting_id`: nullable FK to `meetings.id`.
- `consumed_at`: nullable timestamp.
- `created_at`, `updated_at`.

The server attempt is the only durable owner of `decision_intent`. The desktop
queue persists the opaque attempt ID used by meeting creation and does not
duplicate intent that the create transport never reads.

Constraints and indexes:

- Unique `(workspace_id, owner_user_id, local_recording_id)`.
- Unique `(workspace_id, owner_user_id, idempotency_key_sha256)`.
- Index `(workspace_id, owner_user_id, expires_at)` for bounded cleanup.
- Index `(workspace_id, attempt_state, evaluated_at)` for metadata-only operations.
- `candidate_event_ids_json` and roster JSON are capped in application validation.

Validation rules:

- Only the authenticated owner/device in the active workspace can create or consume an attempt.
- The same idempotency-key hash plus the same request fingerprint returns the existing attempt; a different request fingerprint is a conflict.
- `automatic` requests do not accept an event ID.
- `user_selected` requires a selected event owned by the same user in the same workspace and selected calendar.
- `user_declined` has no candidate or matched event and becomes `declined_by_user`; it never masquerades as a later clear operation.
- Matching performs no provider network I/O.
- Private/free-busy attempts never copy title, roster, description, location or links.
- An attempt may be consumed only once and only by a meeting with the same workspace, owner and local recording ID.
- Missing, expired, foreign or already-consumed attempts never trigger fallback automatic matching.
- Unconsumed attempts are purged after their bounded expiry.

State transitions:

```text
automatic resolve -> matched_auto | provisional_prestart | ambiguous | no_context
                  -> skipped_private | skipped_all_day | skipped_stale_calendar | calendar_unavailable
user-selected resolve -> matched_user
user-declined resolve -> declined_by_user
unconsumed -> expired/purged
resolved -> consumed_by_meeting
```

### RecordingCalendarContextLink *(existing, extended into authoritative meeting context)*

One current calendar-context truth row per meeting. The table name remains for compatibility, but the row may represent a no-link/skip/clear state with a null event FK.

Existing fields retained:

- `id`, `workspace_id`, `meeting_id`;
- `calendar_event_snapshot_id` (made nullable);
- `context_confidence`;
- `context_reasons_json`;
- `title_source`, `roster_source`;
- `manual_override_state`;
- `linked_at`, `unlinked_at`, `created_at`, `updated_at`.

New fields:

- `match_attempt_id`: nullable FK to `recording_calendar_match_attempts.id`.
- `context_state`:
  - `matched_auto`;
  - `matched_user`;
  - `ambiguous`;
  - `no_context`;
  - `skipped_private`;
  - `skipped_all_day`;
  - `skipped_stale_calendar`;
  - `calendar_unavailable`;
  - `skipped_offline_or_unknown`;
  - `skipped_manual_upload`;
  - `declined_by_user`;
  - `cleared_by_user`;
  - `deleted`;
  - `legacy_linked`.
- `safe_reason_code`: bounded product reason.
- `decision_source`: `automatic`, `user`, `system_skip`, or `legacy`.
- `matcher_version`: nullable for legacy rows.
- `evaluated_at`: match decision time.
- `candidate_event_ids_json`: at most 10 safe candidate UUID strings for owner correction.
- `candidate_count`: non-negative integer.
- `matched_event_starts_at`, `matched_event_ends_at`.
- `matched_title`: nullable safe calendar title snapshot.
- `matched_title_state`: `available`, `policy_hidden`, or `unavailable`.
- `matched_roster_json`: bounded safe roster snapshot.
- `matched_roster_state`: `available`, `not_available`, or `hidden`.
- `matched_roster_count`: non-negative integer.
- `recurring_series_key_sha256`: nullable series hash.
- `source_version_fingerprint_sha256`: nullable source evidence hash.

Constraints and indexes:

- Unique `(workspace_id, meeting_id)`; every later decision updates the same row.
- Unique nullable `match_attempt_id`; one attempt cannot be consumed into two meeting contexts.
- Index `(workspace_id, context_state, updated_at)` for list/read-model loading.
- Index `(workspace_id, recurring_series_key_sha256, matched_event_starts_at)` for previous-occurrence lookup.
- Candidate and roster arrays are bounded by service validation.

Migration reconciliation:

- Existing active rows become `legacy_linked`.
- Existing historical rows for one meeting are collapsed deterministically to the newest active row, otherwise the newest row. A retained already-unlinked row becomes `cleared_by_user` with no active event/snapshot projection; a retained row whose meeting is already in deletion becomes `deleted`. The migration records only aggregate reconciliation counts in operator evidence.
- Existing linked event/title/roster values may be backfilled into safe snapshot fields when they pass current display rules. Missing legacy snapshot values remain unavailable rather than fabricated.

Validation rules:

- `matched_auto` and `matched_user` require a non-null event FK and immutable event-time snapshot.
- Non-match/skip/clear states have no active event relationship; `unlinked_at` is set where appropriate.
- `matched_user`, `declined_by_user` and `cleared_by_user` are terminal against automatic overwrite.
- An explicit owner selection may replace any non-deleted state.
- An explicit owner clear removes candidate and roster projections, sets `cleared_by_user`, and blocks automatic reattachment.
- Calendar sync never updates immutable fields on this row.
- Raw attendee emails, descriptions, links, passcodes and provider payloads are forbidden in JSON fields.
- Meeting deletion scrubs snapshot/candidate data and moves the row to `deleted` or purges it under the deletion lifecycle.

State transitions:

```text
no row + consumed attempt -> matched_auto | matched_user | ambiguous | no_context | declined_by_user | skip state
no row + manual upload -> skipped_manual_upload
no row + missing/invalid attempt -> skipped_offline_or_unknown
matched_auto -> matched_user | cleared_by_user | deleted
ambiguous/no_context/skip -> matched_user | cleared_by_user | deleted
matched_user -> matched_user (correction) | cleared_by_user | deleted
declined_by_user -> matched_user | deleted
cleared_by_user -> matched_user | deleted
automatic retry -> no change when a row already exists
```

### CalendarRosterSnapshotItem *(JSON value object)*

Fields allowed inside `matched_roster_json`:

- `participant_kind`;
- `response_status`;
- `display_name`: nullable, already authorized/safe display value;
- `email_present`: boolean only;
- `workspace_relation`;
- `recipient_candidate_class`.

Forbidden fields:

- raw email;
- provider user ID;
- meeting access/share state;
- message/delivery state;
- transcript speaker identity;
- description, URL, passcode or attachment content.

Validation rules:

- The list is capped at 100 items; `matched_roster_count` can represent the full count when provider data was truncated.
- Rooms, resources and groups remain distinct.
- Snapshot participants never create access, recipients, delivery or speaker labels.

### CalendarContextCandidateView *(derived API/UI projection)*

Not persisted separately. For an authorized owner, resolve candidate IDs against current same-owner/same-workspace snapshots and expose only:

- `event_id`;
- `safe_title` or generic hidden label;
- localized `starts_at`/`ends_at`;
- `safe_source_label`;
- `roster_state` and count only when safe;
- `selection_reason` such as `overlaps_recording_start` or `starts_within_grace`.

Private/free-busy events never appear as choices. Missing/deleted candidates disappear without exposing why.

### PreviousRecurringMeetingView *(derived API/UI projection)*

Fields:

- `meeting_id`;
- `safe_title`;
- `started_at`;
- `readiness_state`: `notes_ready`, `transcript_ready`, `processing`, or `unavailable`.

Validation rules:

- Derived only from an earlier `matched_auto`/`matched_user` context row with the same workspace and series hash.
- The existing meeting access decision must authorize the current viewer for the previous meeting.
- Deleted, inaccessible or cross-workspace predecessors return no projection and no placeholder.
- No transcript/summary excerpt is copied into calendar state.

## Matching Invariants

- Time anchor is `recording_started_at`, never upload, processing or review time.
- Candidate window is five minutes before event start through event end.
- A recently ended event is a boundary blocker only; it is not a sole automatic candidate.
- A provisional pre-start match is consumed only if the final recording interval overlaps event start.
- Exactly one strong deduplicated eligible candidate is required for `matched_auto`.
- Any relevant stale selected source vetoes automatic matching.
- Automatic filtering is stricter than preview/prompt preferences.
- Event descriptions and title similarity are never matching evidence.
- Duplicate evidence uses a conference-link hash or same-source provider identity plus recurrence instance.
- Same provider ID across different sources is not enough to dedupe.

## Title Precedence

```text
user_confirmed / upload_provided / file_name_derived / legacy_unknown
    > user-selected calendar correction
    > automatic calendar
    > app_context
    > generic
```

The ordering describes automatic replacement permission, not a general editing API. Explicit user rename remains authoritative.

## Lifecycle And Retention

- Unconsumed match attempts are unmatched future calendar data, expire exactly 24 hours after `evaluated_at`, cannot be consumed at or after expiry, and purge on expiry or source disconnect.
- Consumed attempt content is copied into the meeting context row; the attempt can then retain only minimal correlation fields until normal audit retention or be purged after consumption.
- Matched context rows and safe snapshots follow the meeting's retention/deletion policy.
- Meeting deletion removes/scrubs title/roster/candidate/series context and reports a calendar-context artifact state.
- Calendar source disconnect stops future matching, purges unresolved candidate references and credentials, and retains only already matched safe context under meeting retention.
- External provider events remain outside GRAF deletion control because the feature is read-only.

## Audit Model

Allowed audit metadata:

- matcher version;
- context state/outcome;
- safe reason code;
- candidate count;
- freshness class;
- decision source;
- roster count;
- booleans such as `title_applied` and `user_override_preserved`.

Forbidden audit metadata:

- event title/description/location;
- attendee names or emails;
- meeting URLs/passcodes;
- raw provider identifiers/payloads;
- transcript text/audio;
- credentials or secret paths.

## RLS And Portability

- `recording_calendar_match_attempts` is workspace scoped and requires the same tenant isolation policy/inventory as other calendar tables.
- The authoritative context table remains workspace scoped.
- Migration `0021` is based on `0020_user_scoped_recording_ids`.
- Existing-table changes use Alembic `batch_alter_table`.
- Unique and composite index behavior must be proven on both SQLite and PostgreSQL; 098 introduces no partial index.
- Upgrade, reconciliation, downgrade and RLS checks are required before implementation closeout.
