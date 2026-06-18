# Contract: Web And Desktop Review Surfaces

Date: 2026-06-18

## Scope

Defines the user-visible review behavior after upload and processing. The web
cabinet owns review content. The desktop app embeds the server-owned desktop
routes and keeps native capture/upload controls authoritative.

## Routes

Browser routes:

- `GET /meetings`
- `GET /meetings/{meeting_id}`

Embedded desktop routes:

- `GET /desktop/meetings`
- `GET /desktop/meetings/{meeting_id}`

API routes:

- `GET /api/v1/cabinet/meetings`
- `GET /api/v1/cabinet/meetings/{meeting_id}`
- `GET /api/v1/meetings/{meeting_id}/processing`

## Required Review Fields

Meeting list item MUST expose:

- `meeting_id`
- `title`
- `status`
- `status_label`
- `status_reason`
- `primary_action`
- `transcript_available`
- `diarization_available`
- `notes_action_truth`
- `media_revision`
  - `media_revision_id`
  - `revision_number`
  - `status`
  - `source_kind`

Meeting detail MUST expose:

- meeting summary;
- provenance;
- processing state;
- transcript state;
- speaker state;
- playback availability state;
- notes/action truth;
- governance/deletion truth;
- media revision provenance.

## Status Mapping

- `local_only`: desktop has local package but server review does not exist.
- `uploading`: upload accepted partially or in progress.
- `submitted`: upload finalized but processing not started.
- `processing`: workflow/MediaScribe/import is running.
- `ready`: transcript and diarization are available.
- `partial`: transcript or diarization is available, but not both.
- `blocked`: policy, dependency, revision, or validation state blocks progress.
- `failed`: upload or processing failed with visible safe reason.
- `unavailable`: no authorized reviewable content exists.
- `deleted_future`: deletion flow owns the meeting state.

## Desktop Embedding Rules

- Native Record/Pause/Resume/Stop controls stay outside embedded content.
- Embedded review may show server status, transcript, and governance truth.
- Embedded review must not expose capture controls, local file paths, or local
  upload internals.
- Review links from local queue items require a server meeting id.
- Processing-only items may open status detail but must not claim transcript is
  ready.
- The desktop shell may show a persistent native recording indicator while the
  user browses list/detail review content. That indicator is not owned by the
  embedded review route and must not be hidden by review navigation.

## Reference-Informed Review Boundaries

- Meeting list may expose type/status hints and safe filters such as
  transcript/audio/video/notes availability, but `042` closure depends on
  truthful upload, processing, ready, partial, blocked, failed, deleted, and
  out-of-sync states rather than a full filter system.
- Meeting detail may use separate Notes and Recording/Transcript regions when
  existing cabinet behavior supports it, but the `042` requirement is
  transcript/revision/provenance parity between browser and embedded desktop.
- Speaker labels, timestamps, playback controls, timeline/speaker contribution
  indicators, and transcript quality prompts are allowed only when backed by
  existing authorized synthetic or product data. Transcript editing, speaker
  editing, media trimming, summarization expansion, and richer sharing are not
  introduced by `042`.

## Accessibility And Responsive Requirements

- Queue rows, retry controls, review links, processing states, transcript
  sections, speaker sections, and conflict notices must have stable accessible
  names and role/state semantics.
- Russian MVP copy must be mapped from stable reason/status codes rather than
  ad hoc strings in multiple surfaces.
- Future English/admin copy must be able to use the same reason/status codes.
- Browser review and embedded desktop review must define compact-width behavior
  for meeting list, detail header/actions, transcript segments, right-side
  governance/status panels, and playback/status areas.
- Large upload progress must use safe labels, byte counts, and status copy
  without private filenames or local absolute paths.

## Forbidden Content

Tests and evidence MUST prove these are absent from logs, diagnostics,
screenshots, and committed artifacts:

- raw audio;
- transcript text except inside authorized product response tests with synthetic
  fixtures;
- credentials, tokens, secrets;
- signed object URLs;
- private local paths;
- real private meeting identifiers or Krisp private captures.
