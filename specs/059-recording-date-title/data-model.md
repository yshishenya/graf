# Data Model: Recording Date And Smart Title

## Recording Time Metadata

Represents when the recording was made.

- `recording_started_at`: required for new recordings when the local manifest has a valid start instant.
- `recording_stopped_at`: required for new recordings when the local manifest has a valid stop instant.
- `recording_duration_seconds`: existing duration rounded up to at least one second.
- `display_time_zone`: optional user/workspace timezone used only for display labels.
- `time_status`: `recorded`, `missing`, or `legacy_fallback`.

Validation rules:

- Start must be at or before stop.
- Upload/create/processing time must not replace recording start time.
- Missing or invalid time must render as a truthful fallback instead of invented data.
- Canonical recording instants remain stable when the user's display timezone changes.

## Meeting Title

Represents the visible meeting name.

- `title`: sanitized visible title, maximum 500 characters in the current server contract.
- `title_status`: `generated` or `user_confirmed`; suppressed candidates are recorded in `suppressed_sources`, and legacy server rows render a fallback without a persisted title status.
- `title_updated_at`: optional timestamp for user rename or generated replacement.

Validation rules:

- Empty generated titles fall back to app/date or generic date.
- User-confirmed title wins over generated title.
- Title changes do not change local recording id, media revision id, upload session id, playback, transcript, outcome, export, or deletion identity.
- Feature 059 does not require a new rename UI/API; `user_confirmed` is accepted only from an explicit existing or future title update path.

## Title Source Candidate

Represents one potential source for the visible title.

- `source`: `app_context` or `generic`.
- `raw_available`: boolean metadata; raw private value is not required to be stored.
- `sanitized_title`: candidate after safety filtering.
- `confidence`: `high` or `medium`; rejected candidates are represented by metadata-only suppression reasons, not by a selected confidence value.
- `reason`: short metadata-only reason such as `app_context`, `generic_fallback`, `policy_suppressed`, `unsafe_pattern`, or `missing_permission`.

Validation rules:

- Browser/window candidates are not produced in feature 059; a later privacy-sensitive slice must own window title collection and filtering.
- Calendar candidates are not produced in feature 059; feature 060 owns calendar source modeling.
- `app_context` may only come from already-available approved capture/upload metadata; if discovery would require a new observer or permission prompt, use `generic`.
- Rejected raw values must not be committed in evidence.

## Title Provenance

Records why the title was chosen.

- `selected_source`: one of the candidate sources.
- `selected_confidence`: confidence of the selected source.
- `generated_at`: when title resolution ran.
- `suppressed_sources`: metadata-only list of source/reason pairs.
- `policy_reference`: optional workspace/user policy id or setting name.

Validation rules:

- Provenance must be metadata-only.
- Provenance must survive upload retries for the same local package.
- Provenance should not block meeting creation; if provenance cannot be stored server-side, local manifest/queue provenance remains the source for diagnostics.
- In feature 059, `suppressed_sources` must not imply that calendar or window data was inspected.

## Safe Filename Basename

Represents a human-readable basename for future exports/downloads/local labels.

- `basename`: sanitized pattern: `<YYYY-MM-DD>_<HH-MM>_<title-slug>_<suffix>`.
- `title_slug`: lowercase ASCII-ish slug where practical; non-ASCII may be transliterated or safely replaced.
- `suffix`: short stable suffix derived from existing stable identity, not random per render.
- `basename_status`: `generated`, `generic`, or `suppressed_by_policy`.

Validation rules:

- Must not contain `/`, `\`, `:`, control characters, raw URLs, emails, credentials, or invite links.
- Must have a maximum length safe for common filesystems.
- Must not rename required local files or storage object keys.

## Stable Recording Identity

Existing identities that must remain independent from title and filename.

- Local recording directory/session identity.
- Initial local media revision identity.
- Server meeting id.
- Server media revision id.
- Upload session id.
- Track roles and required package filenames.

Validation rules:

- Generated title or basename changes must not affect these identities.
- Retry idempotency must use persisted stable metadata, not freshly recomputed live desktop state.
