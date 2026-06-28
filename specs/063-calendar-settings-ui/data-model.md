# Data Model: Calendar Settings UI

**Feature**: 063-calendar-settings-ui

This model describes user-facing settings/read-model entities and preference state. It reuses the persisted calendar entities from feature 060 unless explicitly noted.

## Entity: Calendar Settings Surface

**Purpose**: One settings page where users manage calendar integrations.

**Fields**:

- `location_label`: `Настройки / Интеграции / Календари`
- `read_only_boundary_copy`: safe Russian explanation of what 2brain Rec reads and does not do
- `provider_presets`: list of Provider Presets
- `connected_sources`: list of Calendar Source Settings Summaries
- `prompt_preferences`: Calendar Prompt Preferences
- `event_category_preferences`: Event Category Preferences
- `upcoming_preview`: list of Upcoming Preview Items or empty/loading/error state

**Relationships**:

- Has many Provider Presets.
- Has many Calendar Source Settings Summaries.
- Has one preference set per authenticated user/workspace policy scope.

**Validation rules**:

- Must not render raw provider credentials, raw provider payloads, private event text, attendee email dumps, signed links, passcodes, or full meeting URLs.
- Must remain usable when no calendar sources exist.
- Must remain usable while native macOS recording is active.

## Entity: Provider Preset

**Purpose**: A supported provider choice shown in plain Russian.

**Fields**:

- `provider_family`
- `label`
- `connection_method_category`: `app_password`, `manual_url`, or `provider_specific_limited`
- `supported`
- `capability_state`
- `plain_explanation`
- `policy_limitation_copy`

**Validation rules**:

- Must include every provider named in the spec.
- Must explain read-only access before the user submits credentials or starts authorization.
- Must show provider limitations without promising unsupported behavior.

## Entity: Calendar Source Settings Summary

**Purpose**: User-facing state for one connected calendar source.

**Fields**:

- `source_id`
- `provider_family`
- `provider_label`
- `safe_account_label`
- `connection_state`
- `credential_state`
- `sync_state`
- `sync_health_state`
- `selected_calendar_count`
- `readable_calendar_count`
- `last_successful_sync_at`
- `last_sync_attempt_state`
- `safe_error_code`
- `available_actions`: connect, reconnect, manual sync, choose calendars, disconnect, view details
- `policy_state`

**Relationships**:

- Belongs to authenticated workspace/user context.
- Has many Selectable Calendars.
- Contributes Upcoming Preview Items only when at least one calendar is selected.

**Validation rules**:

- `selected_calendar_count` may be zero.
- `connected, selection needed` is valid when the source is connected and readable calendars exist but none are selected.
- `stale` is true when the last successful sync is older than 24 hours or the latest sync attempt failed.
- Safe error display uses categories, not raw provider payloads.

## Entity: Selectable Calendar

**Purpose**: One readable calendar inside a connected source.

**Fields**:

- `calendar_id`
- `display_label`
- `selected`
- `source_id`
- `visibility`: available, selected, hidden, unavailable, private, shared, delegated, removed, duplicate_label
- `color`
- `safe_detail_state`

**Relationships**:

- Belongs to one Calendar Source Settings Summary.

**Validation rules**:

- User can select or deselect each calendar independently.
- Empty selected list is allowed.
- Identical display labels must remain distinguishable by source/safe context.
- Labels must be sanitized before display.

## Entity: Calendar Selection Interface

**Purpose**: The settings area where users choose calendars after a source connects.

**Fields**:

- `source_id`
- `calendars`
- `selected_count`
- `empty_selection_warning`
- `save_state`
- `policy_state`

**State transitions**:

```text
not_loaded -> loading -> loaded
loaded -> saving -> saved
loaded -> saving -> error
loaded -> policy_blocked
```

**Validation rules**:

- No calendars are selected automatically after source connection.
- Empty selection warns that no future meetings or prompts are pulled from that source.
- Saving empty selection must not disconnect the source.

## Entity: Calendar Settings Preferences

**Purpose**: User/workspace-scoped choices that determine prompt and preview behavior.

**Fields**:

- `join_prompt_enabled`
- `record_prompt_enabled`
- `show_upcoming_time`
- `show_upcoming_title`
- `include_events_without_participants`
- `include_events_without_link_or_location`
- `include_all_day_events`
- `include_private_free_busy_prompt_candidates`
- `policy_overrides`

**Defaults**:

- `join_prompt_enabled`: on unless policy blocks it.
- `record_prompt_enabled`: on unless policy blocks it.
- `include_events_without_participants`: off by default unless the event has a meeting link/location.
- `include_events_without_link_or_location`: off by default unless the event has participants and is treated as a meeting-like timed event.
- `include_all_day_events`: off.
- `include_private_free_busy_prompt_candidates`: off.

**Validation rules**:

- Preferences do not enable auto-record.
- Manual recording remains available when workspace policy permits it.
- Policy-constrained controls remain readable and explain the policy source.

## Entity: Upcoming Preview Item

**Purpose**: Safe preview of how selected settings affect upcoming meetings.

**Fields**:

- `event_id`
- `source_ids`
- `calendar_labels`
- `starts_at`
- `ends_at`
- `title`
- `title_state`
- `meeting_link_present`
- `attendee_count_state`
- `privacy_class`
- `prompt_eligibility`
- `sync_confidence_state`

**Validation rules**:

- Private/free-busy events show only safe minimum information.
- Preview must reflect selected calendars and event-category preferences.
- Preview must show stale confidence when affected by stale source data.

## Entity: Overlap Conflict Group

**Purpose**: A safe group of different selected events that overlap in time.

**Fields**:

- `conflict_id`
- `overlap_starts_at`
- `overlap_ends_at`
- `events`
- `available_actions`: choose event, continue without calendar context

**Validation rules**:

- Conflict exists only during the shared interval.
- The UI must not silently choose an event.
- Active recording context must not switch automatically.

## Entity: Duplicate Calendar Event

**Purpose**: One logical meeting that appears through multiple calendars.

**Fields**:

- `canonical_event_id`
- `source_event_ids`
- `source_ids`
- `dedupe_reason`: `stable_provider_event_id` or `same_meeting_link`

**Validation rules**:

- Title similarity, organizer similarity, or close start time alone must not deduplicate.
- Duplicate events may be shown as one meeting with multiple sources.

## Entity: Disconnect Confirmation

**Purpose**: Destructive action confirmation for removing a source.

**Fields**:

- `source_id`
- `provider_label`
- `safe_account_label`
- `future_sync_stops_copy`
- `credential_removal_copy`
- `retention_boundary_copy`
- `confirm_action`
- `cancel_action`

**Validation rules**:

- Must explain future sync stops.
- Must not promise deletion outside 2brain Rec control.
- Already linked meeting context follows meeting retention/deletion policy.

## State Summary

### Source State

```text
not_connected -> connecting -> connected_selection_needed
connected_selection_needed -> connected_selected
connected_selected -> syncing -> synced
synced -> stale
synced -> needs_action
synced -> error
connected_selected -> disconnecting -> disconnected
```

### Prompt State

```text
off
on
blocked_by_policy
not_available_no_selected_calendars
not_available_no_eligible_event
needs_event_choice_overlap
shown
dismissed
expired
opened_meeting_link
manual_recording_started
```

### Sync Health

```text
never_synced
queued
syncing
synced
partial_sync
stale
provider_unavailable
rate_limited
credential_failed
failed_closed
```
