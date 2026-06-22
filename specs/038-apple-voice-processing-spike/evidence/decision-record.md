# Decision Record: Apple Voice Processing Spike

Status: Completed

## Decision

Select exactly one primary outcome at closeout:

- [ ] `accepted_for_builtin_speakerphone`
- [ ] `accepted_for_guidance_only`
- [ ] `accepted_for_headset_routes_only`
- [ ] `blocked_route_topology`
- [ ] `blocked_quality`
- [ ] `blocked_stability`
- [x] `defer_to_webrtc_aec3`

## Evidence Summary

| Gate | Required Proof | Result | Notes |
|------|----------------|--------|-------|
| Built-in speakerphone route | Built-in mic plus built-in speakers tested with baseline and candidate rows. | Deferred | Metadata-only app candidate exists, but no accepted Apple runtime route was proven. |
| Far-end leakage | Candidate improves leakage enough for the accepted threshold. | Not accepted | No Apple-processed candidate passed leakage acceptance. |
| Near-end speech | Local speech remains usable in near-end-only rows. | Not accepted | Speech-preservation remains unproven for Apple processing. |
| Double-talk | Local speech and residual far-end leakage are both classified. | Not accepted | Double-talk acceptance is not proven for Apple processing. |
| Lineage | Candidate signal maps to live behavior, persisted package truth, incoming reference, and manifest metadata. | Passed for package truth only | Candidate metadata is traceable and cannot overwrite `mic.wav`, `incoming.wav`, or leakage finalization. |
| Alignment | Accepted package remains within `durationDifferenceSeconds <= 3` or the current accepted tolerance. | Preserved | Existing package alignment stays authoritative; Apple candidate metadata cannot bypass it. |
| Stop/quit safety | Active capture clears and candidate resources release on Stop and quit. | Passed | Feature-gated candidate lifecycle releases on Stop, failed start, and app quit. |
| CPU/no-hang | Candidate does not regress accepted realtime safety gates. | Deferred | No live Apple DSP path is promoted; CPU/no-hang acceptance remains pending runtime evidence. |
| Diagnostics | Exported diagnostics are metadata-only after redaction. | Passed | Bundle and redaction tests cover Apple outcome, validation rows, route, lineage, CPU, lifecycle, and failure fields. |

## Product Truth

- Original `mic.wav`, `incoming.wav`, and `manifest.json` remain authoritative:
  Yes.
- Existing leakage finalization remains the authority for clean/leakage/
  unproven package status: Yes.
- No user-facing or release-facing clean speakerphone claim is allowed unless
  `accepted_for_builtin_speakerphone` is selected with all gates passing:
  Yes.

## Next Step

If the primary outcome is not `accepted_for_builtin_speakerphone`, choose the
next action:

- [x] Continue with `039-webrtc-aec3-speakerphone-spike`.
- [ ] Continue with `040-speakerphone-recording-fallback-decision`.
- [ ] Continue with guidance/onboarding work only.
- [ ] No follow-up; record why the route is out of scope.

Reason: 038 proved metadata-only lineage, diagnostics, fail-closed handling, and
capture-control safety for Apple candidate evidence, but it did not prove an
accepted Apple built-in speakerphone processing route. Move to `039` for a
product-owned WebRTC AEC3 candidate.

## Links

- Spec: `specs/038-apple-voice-processing-spike/spec.md`
- Plan: `specs/038-apple-voice-processing-spike/plan.md`
- Tasks: `specs/038-apple-voice-processing-spike/tasks.md`
- Manual matrix: `specs/038-apple-voice-processing-spike/evidence/manual-runtime-matrix.md`
- Test results: `specs/038-apple-voice-processing-spike/evidence/test-results.md`
