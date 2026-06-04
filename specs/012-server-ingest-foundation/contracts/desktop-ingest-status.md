# Desktop Ingest Status Contract

## Purpose

This contract defines the status vocabulary that a future desktop uploader can display after local recording finalization. 012 does not implement the desktop uploader or recording UI.

## Status Values

| API status | Desktop meaning | User-facing truth rule |
|------------|-----------------|------------------------|
| `pending` | Server created an upload session but no bytes are accepted yet. | Do not imply backup or processing has started. |
| `uploading` | Server is accepting package bytes. | Show upload progress only from accepted bytes returned by API. |
| `retrying` | Previous request failed or timed out and session can resume. | Keep local recording until finalize succeeds or user deletes it locally. |
| `finalizing` | Server is validating checksums, manifest, and completeness. | Do not show transcript/summary readiness. |
| `finalized` | Upload session is terminal and meeting is durably ingested. | Meeting may be shown as uploaded and waiting for processing. |
| `ingested_pending_processing` | Meeting objects and metadata are ready for future processing. | Processing has not necessarily started in 012. |
| `degraded` | Some data is stored, but normal processing readiness is blocked or incomplete. | Explain the exact recoverable/non-recoverable issue from API error code. |
| `failed` | Server rejected or could not safely store the package. | Local recording should remain the source of truth if available. |
| `aborted` | User/client cancelled the upload session. | Do not imply server-side deletion beyond the session/object cleanup outcome returned by API. |
| `expired` | Upload session TTL elapsed. | Client may create a new session for the same local recording if policy allows. |

## Truth Rules

- `finalized` / `ingested_pending_processing` means backend ingest succeeded; it does not mean Temporal workflow creation, MediaScribe transcription, summary generation, or dashboard availability.
- 012 must never expose MinIO credentials, direct object URLs, MediaScribe credentials, or workflow IDs to the desktop.
- Clients must keep local deletion wording separate from server deletion wording.
- Cross-tenant or revoked-device failures must not reveal whether a foreign meeting/session exists.
- Over-limit failures must state which configured limit was exceeded without exposing secrets or internal storage paths.
