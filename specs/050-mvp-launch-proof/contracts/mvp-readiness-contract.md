# Contract: MVP Readiness Proof

## Required Gates

The 050 closeout must classify each gate as `pass`, `fail`, `blocked`, or
`unproven`.

| Gate ID | Surface | Required Evidence |
|---|---|---|
| `release-deployed` | production_infra | GitHub Release, deployed SHA, production health ready |
| `installed-app-current` | macos_native | Installed app identity and launch proof |
| `record-stop-upload` | macos_native | Visible Record/Stop path and upload/queue state |
| `finalize-processing` | server_backend | Accepted finalization and automatic processing start/reuse |
| `transcript-diarization` | web_cabinet | Ready review has transcript and speaker/diarization state |
| `playback-seek-timeline` | web_cabinet | Playback route, timestamp seek, and speaker timeline are visible and usable |
| `stored-outcomes` | web_cabinet | Stored outcomes or truthful category states are visible |
| `embedded-parity` | desktop_embedded_web | Embedded macOS review matches web review state |
| `processing-time-target` | server_backend | Representative timing measured against 3 minutes per 1 hour audio |
| `truth-docs-current` | docs_status | Status/readiness docs match deployed 045-049 truth |
| `forbidden-content-scan` | security | Evidence contains no forbidden private content |

## Claim Rules

- `internal_pilot_candidate` requires all P1 gates to pass.
- `pilot_blocked` is required if any P1 gate fails, is blocked, or is unproven.
- `production_ready` and broad `user_rollout_ready` are out of scope for 050.

## Evidence Safety

Committed evidence must not contain raw audio, transcript text, generated
private outcome text, private meeting titles, account identifiers, cookies,
tokens, credentials, signed URLs, storage object keys, or local private paths.
