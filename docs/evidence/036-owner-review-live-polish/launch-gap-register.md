# Launch Gap Register

Feature: `036-owner-review-live-polish`

| Gap | Severity | Journey | Missing Evidence | Next Action |
|-----|----------|---------|------------------|-------------|
| `notes-action-output` | `P1` | notes-action-output | Stored/generated launchable notes and action output, or explicit owner-approved pilot deferral. | Either implement stored generated notes/actions or record an accepted narrower pilot deferral. |
| `production-user-rollout-evidence` | `P1` | production-deployment-smoke | Internal pilot or user rollout validation with live app journey evidence. | Keep production claim capped until a pilot runbook or live loop validation passes. |
| `web-owner-live-auth-context` | `P1` | meeting-list | Commit-safe authenticated owner review proof on rec.2brain.pro for list, detail, and governance states. | Use an approved temporary owner session, capture metadata-only list/detail/governance state evidence, and clean up the session without committing private values. |
| `browser-target-gaps` | `P2` | capture-target-coverage | Target matrix decision for browser coverage before pilot promises. | Keep unsupported targets explicit or run a browser target hardening slice. |
| `desktop-runtime-walkthrough-evidence` | `P2` | desktop-embedded-cabinet | Installed /Applications app idle, active, paused, resumed, stopped, configured, missing-auth, and local-only walkthrough evidence in one final pack. | Run the installed-app walkthrough and commit metadata-safe screenshots or a blocker note. |
| `signed-installer-evidence` | `P2` | desktop-distribution | signed installer evidence for broader pilot distribution. | Plan installer signing/notarization as a follow-up slice if pilot distribution needs it. |

P0/P1 gaps block `mvp_loop_ready` and `internal_pilot_candidate` until closed.
