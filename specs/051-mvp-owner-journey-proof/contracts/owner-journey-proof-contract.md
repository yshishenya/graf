# Contract: Owner Journey Proof

## Required P1 Gates

051 closeout must classify each P1 gate as `pass`, `fail`, `blocked`, or
`unproven`.

| Gate ID | Surface | Required Evidence |
|---|---|---|
| `release-deployed` | production_infra | GitHub Release, deployed SHA, production health ready |
| `installed-app-current` | macos_native | `/Applications/2brain Rec.app` version, launch, and codesign verification |
| `fresh-record-stop-upload` | macos_native | Fresh installed-app record/stop/upload or exact blocker |
| `finalize-processing` | server_backend | Accepted finalization and automatic processing start/reuse |
| `transcript-diarization` | web_cabinet | Production candidate has transcript and diarization/speaker state |
| `playback-seek-timeline` | web_cabinet | Playback route, timestamp seek, and speaker timeline are visible and usable |
| `stored-outcomes-production` | web_cabinet | Stored outcome category states and counts on production candidate |
| `embedded-parity` | desktop_embedded_web | Embedded macOS review matches web review state |
| `processing-time-target` | server_backend | Representative timing measured against 3 minutes per 1 hour audio |
| `interface-quality` | web_cabinet, desktop_embedded_web, macos_native | No P1 overlap, overflow, stale-ready, or hidden-control finding |
| `truth-docs-current` | docs_status | Status/readiness docs match deployed 045-051 truth |
| `forbidden-content-scan` | security | Evidence contains no forbidden private content |

## Claim Rules

- `internal_pilot_candidate` requires all P1 gates to pass.
- `pilot_blocked` is required if any P1 gate fails, is blocked, or is unproven.
- `production_ready` and broad `user_rollout_ready` are out of scope for 051.

## Evidence Safety

Committed evidence must not contain raw audio, transcript text, generated
private outcome text, private meeting titles, account identifiers, cookies,
tokens, credentials, signed URLs, storage object keys, or local private paths.
