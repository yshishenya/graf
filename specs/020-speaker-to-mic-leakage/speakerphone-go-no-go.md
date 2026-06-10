# Built-In Speakerphone Go/No-Go: Speaker-To-Mic Leakage Control

**Date**: 2026-06-04

## Decision

This slice is **no-go** for claiming built-in Mac microphone plus built-in Mac
speakers are clean dual-track MVP capture by default.

This slice is **go** for truthful package finalization:

- record `mic.wav` and `incoming.wav` as original evidence during the meeting;
- do not clean leakage live;
- do not ask the user to fix routes during the meeting;
- assign leakage truth only after stop/finalization;
- allow `clean` only when persisted evidence passes `leakage-threshold.v1`;
- fail closed as `leakage_detected`, `unproven`, `not_measured`, or
  `not_applicable` when clean evidence is missing.

## Why

The product must support common built-in speakerphone use, but this feature does
not implement live AEC or route-level cleanup. Treating built-in speakerphone
recordings as clean without proof would break local-speaker truth and future
MediaScribe dual-track readiness.

## Threshold

The accepted v1 gates are defined in `research.md` and `data-model.md` as
`leakage-threshold.v1`. The implementation must not reinterpret those values
silently. Any tuning change requires a new threshold version.

## Mixed-Audio Fallback

Mixed or non-separated recording is not selected as the implementation path for
020.

Mixed audio remains a future fallback only after a later plan records that
Apple voice processing, WebRTC AEC3 or equivalent local AEC, and app-side clean
dual-track graph changes failed accepted built-in speakerphone gates.

A future mixed-audio plan must define:

- diarization confidence;
- speaker attribution limits;
- upload eligibility;
- user-facing recording truth;
- MediaScribe input shape;
- why mixed audio is more truthful than labeling separated tracks clean.

## Future Gate

Clean built-in speakerphone dual-track MVP acceptance requires a separate Spec
Kit slice proving live Apple/WebRTC/app-side processing or another architecture
against controlled leakage, double-talk, latency, route-change, realtime-safety,
and alignment gates.

## Constitution Result

This decision prevents false clean claims now. It does not resolve live
speaker-to-mic leakage for built-in speakerphone routes, so MVP planning cannot
depend on built-in speakerphone clean dual-track capture until the future gate
passes.
