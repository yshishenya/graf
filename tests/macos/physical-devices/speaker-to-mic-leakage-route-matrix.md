# Speaker-To-Mic Leakage Route Matrix

Feature: `020-speaker-to-mic-leakage`

020 does not block recording start based on leakage route readiness. This matrix
records finalization-only evidence after stopped packages.

| Route | Browser Target | Live Leakage Readiness Blocks Start | Other Start Safety Blocker | Expected Finalization | Manual Status |
| --- | --- | ---: | --- | --- | --- |
| Built-in mic + built-in speakers | Supported browser/meeting target | No | None from leakage readiness | `clean` only if persisted evidence passes `leakage-threshold.v1`; otherwise `leakage_detected`, `unproven`, or `not_measured` | Not run in this environment |
| Wired headphones | Supported browser/meeting target | No | None from leakage readiness | Finalization evidence or truthful degraded status | Not run in this environment |
| USB headset | Supported browser/meeting target | No | None from leakage readiness | Finalization evidence or truthful degraded status | Not run in this environment |
| Bluetooth/AirPods-class | Supported browser/meeting target | No | None from leakage readiness | Finalization evidence or truthful degraded status; route changes captured as metadata | Not run in this environment |
| Aggregate/multi-output | Supported browser/meeting target | No | None from leakage readiness | Finalization evidence or truthful degraded status; unsupported shapes are `not_measured` | Not run in this environment |
| 2brain Rec virtual device selected as physical mic/output | Any | No | Yes, self-routing rejection | No clean package claim; route evidence records `selfRoutingRejected=true` | Covered by prerequisite regression tests |

## Degraded-State Evidence

- Missing tracks: `not_measured`, not transcription-ready.
- Timeline mismatch: `unproven` with `blocked_timeline_misaligned`, not transcription-ready.
- Route changes: metadata-only evidence; no live remediation prompt.
- Non-recording passthrough continuity: checked by existing passthrough regression gates.
