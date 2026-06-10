# Speaker-To-Mic Leakage Finalization Evidence

Feature: `020-speaker-to-mic-leakage`

## Decision Record

- Built-in Mac microphone plus built-in speakers is `no_go_for_clean_builtin_speakerphone_mvp` in this slice unless a saved package passes `leakage-threshold.v1`.
- The accepted 020 outcome is `go_for_truthful_finalization`: package truth is written after `Stop` and transcription readiness fails closed.
- Mixed audio remains a future fallback decision record only. It is not selected for 020 implementation.
- Apple voice processing, WebRTC AEC3, and custom AEC remain future spike gates. They are not runtime cleanup in 020.

## Controlled Fixture Classes

- `clean_far_end_only`: remote reference present, local mic below leakage threshold, low correlation, no clipping/dropout, enough far-end-only window.
- `leakage_detected_far_end_only`: remote reference appears in `mic.wav` above `leakage-threshold.v1` level or correlation gates.
- `double_talk_unproven`: overlapping local and remote speech downgrades confidence when separation cannot be proven.
- `not_measured_missing_reference`: missing or invalid `incoming.wav` prevents measurement.
- `silence_noise_room_echo_clipping_dropout`: not treated as clean by default; insufficient or corrupted evidence becomes `unproven` or `not_measured`.

## Privacy Boundary

Controlled QA stimuli may be generated locally and must contain no meeting content,
participant speech, secrets, credentials, signed URLs, or absolute user paths.
Real meeting artifact analysis may record only metadata: status, thresholds,
safe levels/correlation, route class facts, failure reasons, and egress flags.

## Derived Track Boundary

Derived cleaned tracks are separate artifacts. They must include source track ids,
processor id/version, residual leakage status, residual threshold version, and
local deletion registration before `eligibleForTranscription=true`.

## Clean-Room Review

- No Krisp assets, binaries, proprietary strings, protected implementation details, or behavior clones are used.
- Public API/dependency decisions are recorded as metadata-only decision records.
- 020 does not claim live speakerphone cleanup.
