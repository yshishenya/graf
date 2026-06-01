# Contract: Release Hardening Evidence

Release-hardening evidence is metadata-only. It must not include raw audio,
transcript text, meeting content, credentials, tokens, signed URLs, or secrets.

## Common Result Values

- `passed`
- `blocked`
- `not_accepted`

## Release Hardening Run Record

Required fields:

- `run_id`
- `created_at`
- `macos_version`
- `app_build`
- `driver_build`
- `result`
- `notes`

## Evidence Rules

- Evidence may include device display names and local route state.
- Evidence may include timing, CPU, process names, and pass/block reasons.
- Evidence must redact paths or values that expose credentials or tokens.
- Evidence must mark skipped targets as `not_accepted`, not `passed`.
- Evidence must distinguish short smoke evidence from future recording-assisted
  long-duration acceptance.
