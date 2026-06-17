# Launch Gap Register

Feature: `036-owner-review-live-polish`

| Gap | Severity | Journey | Missing Evidence | Next Action |
|-----|----------|---------|------------------|-------------|
| `notes-action-output` | `P1` | notes-action-output | Notes/action output availability or truthful blocked/deferred state in review surfaces. | Implement notes/action truth states and keep readiness bounded if generated output remains unavailable. |
| `production-user-rollout-evidence` | `P1` | production-deployment-smoke | Internal pilot or user rollout validation with live app journey evidence. | Keep production claim capped until a pilot runbook or live loop validation passes. |
| `web-owner-live-auth-context` | `P1` | meeting-list | Commit-safe authenticated owner review proof on `rec.2brain.pro` for list, detail, and governance states. | Implement or validate the owner auth/session path for `rec.2brain.pro`, then capture metadata-safe owner review evidence. |
| `browser-target-gaps` | `P2` | capture-target-coverage | Target matrix decision for browser coverage before pilot promises. | Keep unsupported targets explicit or run a browser target hardening slice. |
| `desktop-product-surface-polish` | `P2` | desktop-embedded-cabinet | Accepted desktop/web product surface polish against the clean-room V8 implementation baseline. | Use the accepted 030 V8 baseline in this UI implementation slice. |
| `signed-installer-evidence` | `P2` | desktop-distribution | Signed installer evidence for broader pilot distribution. | Plan installer signing/notarization as a follow-up slice if pilot distribution needs it. |

P0/P1 gaps block `mvp_loop_ready` and `internal_pilot_candidate` until closed
or explicitly deferred with accepted owner guardrails.
