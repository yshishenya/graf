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
