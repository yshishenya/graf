# Contract: Cross-Surface Status Model

## Purpose

Ensure the macOS app, embedded desktop cabinet subset, and full browser web
cabinet communicate the same user-facing truth for recording, upload,
transcription, review, deletion, and access.

## Status Fields

Each status definition must include:

- `status_id`
- `meaning`
- `desktop_label_ru`
- `desktop_label_en`
- `web_label_ru`
- `web_label_en`
- `desktop_primary_action`
- `web_primary_action`
- `terminality`
- `allowed_claims`
- `forbidden_claims`
- `deletion_or_retention_note`

## Required Statuses

| Status ID | Meaning | Terminality | Key Forbidden Claim |
|---|---|---|---|
| `local_recording_saved` | Local package saved after Stop | `non_terminal` | Must not imply server upload. |
| `local_only` | Meeting exists only on this Mac | `non_terminal` | Must not imply backup/server retention. |
| `queued` | Waiting for upload | `non_terminal` | Must not imply upload completion. |
| `uploading` | Transfer to Rec server in progress | `non_terminal` | Must not imply transcription started. |
| `uploaded` | Server accepted required artifacts | `non_terminal` | Must not imply transcript or notes readiness. |
| `audio_extraction` | Audio extraction from uploaded media is pending/running | `non_terminal` | Must not imply transcript readiness. |
| `transcription` | Transcription is pending/running | `non_terminal` | Must not show empty transcript as failure. |
| `transcript_ready` | Transcript is available | `non_terminal` | Must not imply notes/summary readiness. |
| `notes_ready` | Summary/decisions/action items are available | `terminal_success` | Must still show provenance/status. |
| `partial_degraded` | Some artifacts or generated outputs failed | `terminal_failure` or `non_terminal` by case | Must not hide missing outputs. |
| `failed` | Processing or upload cannot continue automatically | `terminal_failure` | Must not delete local artifacts silently. |
| `deleted` | Deleted where 2brain Rec controls deletion | `terminal_deleted` | Must not promise universal external erasure. |
| `access_denied` | User/session cannot access the meeting | `terminal_failure` for that viewer | Must not reveal private meeting content. |

## Surface Consistency Rules

- Desktop, embedded cabinet, and browser cabinet may use different layouts but
  must use the same meaning for each status.
- Upload success is separate from transcription readiness.
- Transcript readiness is separate from notes readiness.
- Failure and degraded states must explain what exists, what failed, and what
  action is available.
- Deletion copy must use truthful control-bounded language.
- Access denied states must not leak meeting metadata beyond allowed policy.

## Review-Surface Requirements

A complete meeting review must include:

- readable transcript navigation;
- playback context;
- summary;
- decisions;
- action items;
- source/status provenance;
- next actions;
- deletion/access entry points.

When an output is unavailable, the review must show an explicit unavailable or
degraded state rather than leaving the area blank.

## Validation

- Walk the owner value loop from desktop and browser entry points.
- Compare every displayed status across desktop and web.
- Confirm no prototype screen claims transcript, notes, deletion, or upload
  success before the corresponding status allows it.
