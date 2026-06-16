# Launch Gap Register

Feature: `034-mvp-loop-readiness`

| Gap | Severity | Journey | Missing Evidence | Next Action |
|-----|----------|---------|------------------|-------------|
| `live-desktop-evidence` | `P1` | desktop-embedded-cabinet | Fresh metadata-safe live desktop screenshots or explicit product-owner acceptance of the blocker. | Capture desktop first-surface and embedded detail screenshots without private content. |
| `notes-action-output` | `P1` | notes-action-output | Notes/action output availability or truthful blocked state in review surfaces. | Decide whether the next slice is assistant notes/actions or explicit MVP deferral. |
| `production-user-rollout-evidence` | `P1` | production-deployment-smoke | Internal pilot or user rollout validation with live app journey evidence. | Keep production claim capped until a pilot runbook or live loop validation passes. |
| `browser-target-gaps` | `P2` | capture-target-coverage | Target matrix decision for browser coverage before pilot promises. | Keep unsupported targets explicit or run a browser target hardening slice. |
| `signed-installer-evidence` | `P2` | desktop-distribution | signed installer evidence for broader pilot distribution. | Plan installer signing/notarization as a follow-up slice if pilot distribution needs it. |

P0/P1 gaps block `mvp_loop_ready` and `internal_pilot_candidate` until closed.
