# Launch Gap Register

Feature: `052-mvp-live-ui-proof`

| Gap | Severity | Journey | Missing Evidence | Next Action |
|-----|----------|---------|------------------|-------------|
| `fresh-owner-journey-evidence` | `P1` | fresh-owner-journey | Fresh installed-app record, stop, upload, finalization, processing, and review proof on the current production release. | Run the installed app owner journey and record metadata-only gate states in the active closeout report. |
| `production-stored-outcomes-evidence` | `P1` | stored-outcomes-production | Stored outcome category states and counts on a current installed-app production candidate. | Run the production owner journey probe and record outcome category states without private text. |
| `browser-target-gaps` | `P2` | capture-target-coverage | Target matrix decision for browser coverage before pilot promises. | Keep unsupported targets explicit or run a browser target hardening slice. |
| `signed-installer-evidence` | `P2` | desktop-distribution | signed installer evidence for broader pilot distribution. | Plan installer signing/notarization as a follow-up slice if pilot distribution needs it. |

P0/P1 gaps block `mvp_loop_ready` and `internal_pilot_candidate` until closed.
