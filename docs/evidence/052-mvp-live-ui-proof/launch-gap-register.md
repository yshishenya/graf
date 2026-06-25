# Launch Gap Register

Feature: `052-mvp-live-ui-proof`

| Gap | Severity | Journey | Missing Evidence | Next Action |
|-----|----------|---------|------------------|-------------|
| `fresh-owner-journey-evidence` | `P1` | fresh-owner-journey | Fresh installed-app record, stop, upload, finalization, processing, and review proof on the current production release. | Sign in inside `/Applications/2brain Rec.app`, create a short fresh recording, then record metadata-only gate states in the active closeout report. |
| `production-stored-outcomes-evidence` | `P1` | stored-outcomes-production | Stored outcome category states and counts on a current installed-app production candidate. | After the fresh installed-app candidate exists, run the production owner journey probe and record outcome category states without private text. |
| `mediascribe-large-audio-proxy-ceiling` | `P2` | long-audio-processing | Rec production ingress accepts the 1 GiB-per-track upload contract. MediaScribe is a separate host and only receives audio tracks, but its public proxy returns `413` on large request probes, so very long uncompressed dual-track audio may still fail there. | Do not raise MediaScribe just for 1 GiB Rec/video upload. If real combined audio sent to MediaScribe approaches the proxy ceiling, raise the MediaScribe OpenResty/nginx body limit and repeat a non-sensitive large-audio processing check. |
| `upload-progress-visibility` | `P2` | native-upload-truth | The macOS app shows queued/uploading states but not per-file or overall upload progress, so the user cannot tell slow upload from a stuck upload. | Add native upload progress using accepted bytes vs total bytes, show retry/stalled states, and keep the local recording row understandable during large uploads. |
| `browser-target-gaps` | `P2` | capture-target-coverage | Target matrix decision for browser coverage before pilot promises. | Keep unsupported targets explicit or run a browser target hardening slice. |
| `signed-installer-evidence` | `P2` | desktop-distribution | signed installer evidence for broader pilot distribution. | Plan installer signing/notarization as a follow-up slice if pilot distribution needs it. |

P0/P1 gaps block `mvp_loop_ready` and `internal_pilot_candidate` until closed.
