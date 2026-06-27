# Data Model: Calendar Context Ingestion

**Feature**: 060-calendar-context-ingestion

**Date**: 2026-06-26

## Overview

Calendar data is meeting-adjacent sensitive content. Store enough normalized context to name and prepare recordings, explain recording-time context links, show safe upcoming prompts, and support later recipient policy decisions. Do not store provider credentials directly in readable columns. Do not grant meeting access or send messages from calendar attendees in 060.

## Entities

### CalendarSource

Connected provider account or endpoint under a workspace.

Fields:

- `id`: UUID primary key.
- `workspace_id`: FK to `workspaces.id`.
- `owner_user_id`: FK to `user_identities.id`.
- `provider_family`: enum/string, e.g. `caldav_yandex`, `caldav_mail_ru`, `custom_caldav`, `google_calendar`, `microsoft_graph`, `exchange_ews`, `bitrix24`.
- `provider_label`: safe display label, no private event content.
- `auth_mode`: `oauth`, `app_password`, `service_account_future`, `manual_url`.
- `credential_state`: `pending`, `sealed`, `expired`, `revoked`, `purged`, `invalid`.
- `connection_state`: `active`, `degraded`, `needs_reauth`, `disabled_by_policy`, `disconnecting`, `disconnected`.
- `sync_state`: `never_synced`, `syncing`, `synced`, `partial`, `rate_limited`, `provider_unavailable`, `failed_closed`.
- `sync_horizon_start`: computed current sync lower bound; must not be before now for 060.
- `sync_horizon_end`: rolling 12 months ahead.
- `last_sync_started_at`, `last_sync_finished_at`, `last_successful_sync_at`.
- `last_safe_error_code`: metadata-only error such as `provider_timeout`, `invalid_credentials`, `rate_limited`.
- `capabilities_json`: provider support matrix.
- `selected_calendar_count`.
- `disconnected_at`, `created_at`, `updated_at`.

Relationships:

- One source has many `ExternalCalendar` records.
- One source has many `CalendarEventSnapshot` records through selected calendars.
- One source has one active `CalendarCredentialEnvelope` at most.
- One source has many `CalendarAuditEvent` records.

Validation rules:

- `workspace_id`, `owner_user_id`, and `provider_family` are required.
- Source cannot sync when `connection_state` is disconnected or `credential_state` is not usable.
- API responses must not expose sealed credential material or provider secret paths.

State transitions:

```text
pending -> active -> needs_reauth -> active
active -> degraded -> active
active -> disconnecting -> disconnected
active -> disabled_by_policy -> active
```

### CalendarCredentialEnvelope

Server-owned sealed credential reference for OAuth refresh tokens, app passwords, or provider access tokens.

Fields:

- `id`: UUID primary key.
- `calendar_source_id`: FK to `calendar_sources.id`.
- `workspace_id`: FK to `workspaces.id`.
- `secret_kind`: `oauth_refresh_token`, `oauth_access_token`, `app_password`, `ews_password`, `api_key`.
- `sealed_payload`: encrypted bytes/text envelope.
- `key_version`: server secret/encryption key version.
- `secret_fingerprint_sha256`: hash for rotation/debug correlation, never raw secret.
- `expires_at`: provider credential expiry when known.
- `revoked_at`, `purged_at`, `created_at`, `updated_at`.

Validation rules:

- Raw credential input may exist only in request handling memory.
- No logs, diagnostics, API responses, specs, plans, screenshots, or evidence may contain `sealed_payload` or raw credential values.
- Purge on disconnect unless retained only as revocation evidence without secret material.

### ExternalCalendar

One provider calendar collection selected or available for ingestion.

Fields:

- `id`: UUID primary key.
- `calendar_source_id`: FK.
- `workspace_id`: FK.
- `provider_calendar_id`: provider collection id or CalDAV URL fingerprint.
- `display_label`: safe label shown to authorized user.
- `owner_email_hash`: optional hash of owner email.
- `owner_display_name`: optional safe display name when policy allows.
- `color`: provider color/tag when available.
- `visibility`: `selected`, `available`, `hidden`, `disabled_by_policy`.
- `sync_token`: provider sync token/ctag when available.
- `last_seen_at`, `created_at`, `updated_at`.

Validation rules:

- `(calendar_source_id, provider_calendar_id)` is unique.
- Only `selected` calendars contribute events to prompts/context links.

### CalendarEventSnapshot

Normalized and source-preserving event or recurrence instance snapshot.

Fields:

- `id`: UUID primary key.
- `workspace_id`: FK.
- `calendar_source_id`: FK.
- `external_calendar_id`: FK.
- `provider_event_id`: provider event/item id where available.
- `ical_uid`: iCalendar UID where available.
- `recurring_series_id`, `recurrence_instance_id`, `original_start`.
- `source_version`: ETag, sequence, changeKey, sync token, or provider version.
- `source_status`: `confirmed`, `tentative`, `cancelled`, `deleted`, `private`, `free_busy_only`, `unknown`.
- `starts_at`, `ends_at`, `duration_seconds`.
- `timezone`, `original_start_timezone`, `original_end_timezone`.
- `all_day`, `floating_time`.
- `transparency`: free/busy state.
- `recurrence_rule_json`, `recurrence_exceptions_json`.
- `title`, `description`, `location`: sensitive content; authorization-gated.
- `privacy_class`: `public`, `private`, `confidential`, `free_busy_only`, `unknown`.
- `conference_summary_json`: parsed meeting links and provider family metadata.
- `attachments_metadata_json`: metadata only; no file fetch in 060.
- `provider_extras_json`: bounded provider-specific snapshot.
- `safe_to_show_in_list`, `safe_to_use_as_title`, `sensitivity_reasons_json`.
- `source_created_at`, `source_updated_at`, `source_deleted_at`.
- `created_at`, `updated_at`.

Relationships:

- Has many `CalendarParticipant` records.
- Has many `ConferenceLinkCandidate` records.
- Can be linked to a meeting through `RecordingCalendarContextLink`.
- Can have reminder state through `CalendarReminderState`.

Validation rules:

- In 060, snapshots must belong to the rolling 12-month future horizon unless retained because a meeting was already linked.
- Private/free-busy-only events must not fabricate title, attendees, or links.
- Provider extras must be bounded and pass forbidden-content evidence rules.

### CalendarParticipant

Organizer, creator, attendee, resource, room, or group visible on an event.

Fields:

- `id`: UUID primary key.
- `calendar_event_snapshot_id`: FK.
- `workspace_id`: FK.
- `participant_kind`: `organizer`, `creator`, `required_attendee`, `optional_attendee`, `resource`, `room`, `group`, `unknown`.
- `response_status`: `accepted`, `declined`, `tentative`, `needs_action`, `organizer`, `unknown`.
- `email`: sensitive, authorization-gated.
- `email_hash`: hash for dedupe/diagnostics without exposing address.
- `display_name`: sensitive, authorization-gated.
- `provider_user_id`.
- `workspace_relation`: `internal`, `external`, `resource`, `group`, `unknown`.
- `recipient_candidate_class`: `internal`, `external`, `resource`, `group`, `declined`, `hidden`, `no_email`, `unknown`.
- `created_at`, `updated_at`.

Validation rules:

- Calendar participants are not transcript speakers.
- Calendar participants do not grant access or become recipients in 060.
- Declined/resource/group states must remain distinguishable for later policy.

### ConferenceLinkCandidate

Meeting URL or dial-in metadata parsed from provider fields.

Fields:

- `id`: UUID primary key.
- `calendar_event_snapshot_id`: FK.
- `workspace_id`: FK.
- `source_field`: `location`, `description`, `provider_conference`, `dial_in`, `unknown`.
- `provider_family`: `yandex_telemost`, `mts_link`, `kontur_talk`, `trueconf`, `vk_calls`, `zoom`, `google_meet`, `microsoft_teams`, `webex`, `generic`.
- `url_hash`: hash for correlation without exposing full URL.
- `redacted_url_preview`: optional safe domain/provider preview.
- `contains_passcode`: boolean.
- `sensitivity_class`: `meeting_link`, `passcode`, `dial_in`, `tracking_url`, `unknown`.
- `created_at`.

Validation rules:

- Full meeting URLs and passcodes are sensitive and must not appear in logs/evidence.
- Link candidates do not cause bot auto-join or auto-record in 060.

### RecordingCalendarContextLink

Link between a 2brain Rec meeting and the event context selected at recording time.

Fields:

- `id`: UUID primary key.
- `workspace_id`: FK.
- `meeting_id`: FK to `meetings.id`.
- `calendar_event_snapshot_id`: FK.
- `context_confidence`: `selected`, `high`, `medium`, `low`, `ambiguous`, `none`.
- `context_reasons_json`: `manual_selection`, `current_event`, `event_start_prompt`, `meeting_url_match`, `provider_account_match`, `target_app_hint`.
- `title_source`: `user`, `calendar`, `platform`, `generic`.
- `roster_source`: `calendar`, `manual`, `none`.
- `manual_override_state`: `none`, `selected_by_user`, `cleared_by_user`, `calendar_changed_after_selection`.
- `linked_at`, `unlinked_at`, `created_at`, `updated_at`.

Validation rules:

- No retrospective matching of old recordings.
- User-renamed meeting titles stay primary.
- Deleting a meeting under 2brain Rec control deletes or retention-accounts the linked calendar context.

### CalendarReminderState

Local/desktop reminder state mirrored from server context.

Fields:

- `id`: UUID primary key.
- `workspace_id`: FK.
- `calendar_event_snapshot_id`: FK.
- `device_id`: FK to `registered_devices.id`.
- `join_prompt_due_at`: `starts_at - 1 minute`.
- `record_prompt_due_at`: `starts_at`.
- `join_prompt_state`: `not_due`, `shown`, `dismissed`, `opened`, `not_available`, `blocked_by_policy`.
- `record_prompt_state`: `not_due`, `shown`, `dismissed`, `started`, `not_available`, `blocked_by_policy`.
- `last_client_seen_at`, `created_at`, `updated_at`.

Validation rules:

- Reminder state cannot start recording by itself in 060.
- Reminder copy must be metadata-safe when title/link visibility is denied.

### CalendarAuditEvent

Metadata-only audit event for calendar operations.

Fields:

- `id`: UUID primary key.
- `workspace_id`: FK.
- `calendar_source_id`, `calendar_event_snapshot_id`, `meeting_id`, `actor_user_id`, `device_id`: optional FKs.
- `event_type`: e.g. `calendar_source_connected`, `calendar_sync_succeeded`, `calendar_sync_failed`, `calendar_context_linked`, `calendar_source_disconnected`, `calendar_context_deleted`.
- `outcome`: `success`, `failed`, `skipped`, `blocked`.
- `safe_reason_code`.
- `metadata_json`: redacted metadata only.
- `created_at`.

Validation rules:

- Metadata redaction must treat keys containing token, secret, password, credential, passcode, url, email, description, agenda, attendee as sensitive unless explicitly whitelisted as a count/hash/boolean.

## Lifecycle Rules

- Source disconnect stops future sync, purges credentials, purges unmatched/future cache, and keeps matched meeting context only under the matched meeting retention/deletion policy.
- Provider event deletion/cancellation updates future-event state but does not silently delete already linked meeting context.
- Calendar events outside 2brain Rec are outside deletion control unless a later calendar-write feature is approved.
- Calendar context appears in deletion reports as 2brain-controlled meeting content when stored locally.

## Provider Capability Model

Capability keys:

- `supports_attendees`
- `supports_response_status`
- `supports_recurrence`
- `supports_recurrence_exceptions`
- `supports_private_events`
- `supports_conference_metadata`
- `supports_attachments_metadata`
- `supports_delta_sync`
- `supports_updates_deletes`
- `supports_free_busy_only`
- `supports_rich_provider_extras`

Capability values:

- `supported`
- `unsupported`
- `not_returned`
- `admin_policy_dependent`
- `provider_plan_dependent`
- `unknown`

## Open Questions Deferred To Later Features

- Automatic recording without pre-start prompts.
- Sending summaries/transcripts/reports.
- Calendar invite mutation or provider-side attendee updates.
- Bot auto-join or conference creation.
- Speaker mapping from calendar attendees.
