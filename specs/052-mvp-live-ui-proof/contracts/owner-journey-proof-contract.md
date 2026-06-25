# Contract: Owner Journey Proof

## Required P1 Gates

052 closeout must classify each gate as `pass`, `fail`, `blocked`,
`unproven`, or `out_of_scope`.

| Gate ID | Surface | Required Evidence |
|---|---|---|
| `release-deployed` | production_infra | GitHub Release, deployed SHA, production health ready |
| `installed-app-current` | macos_native | `/Applications/2brain Rec.app` version, launch, and code-sign verification |
| `fresh-record-stop-upload` | macos_native | Current installed-app record, stop, upload, or exact blocker |
| `finalize-processing` | server_backend | Accepted finalization and processing start/reuse for the same candidate |
| `transcript-diarization` | web_cabinet | Production candidate has transcript and diarization/speaker state |
| `playback-seek-timeline` | web_cabinet | Playback, timestamp seek, and speaker timeline visible and usable |
| `stored-outcomes-production` | web_cabinet | Stored outcome category states and counts on current production candidate |
| `embedded-parity` | desktop_embedded_web | macOS embedded review matches web review state for the same candidate |
| `processing-time-target` | server_backend | Representative timing measured against 180 seconds per one hour audio |
| `interface-quality` | web_cabinet, desktop_embedded_web, macos_native | No P1 overlap, overflow, false-ready, or hidden-control finding |
| `truth-docs-current` | docs_status | Status, readiness docs, changelog, and release notes share one claim |
| `forbidden-content-scan` | security | Evidence contains no forbidden private content |

## Claim Rules

- `internal_pilot_candidate` requires all P1 gates to pass.
- `pilot_blocked` is required if any P1 gate fails, is blocked, or is
  unproven.
- `production_ready` and broad `user_rollout_ready` are out of scope for 052.

## Evidence Safety

Committed evidence must not contain raw audio, transcript text, generated
private outcome text, private meeting titles, account identifiers, cookies,
tokens, credentials, signed URLs, storage object keys, or local private paths.
