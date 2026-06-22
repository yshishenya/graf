# Decision Record: Apple Voice Processing Spike

Status: Pending

## Decision

Select exactly one primary outcome at closeout:

- [ ] `accepted_for_builtin_speakerphone`
- [ ] `accepted_for_guidance_only`
- [ ] `accepted_for_headset_routes_only`
- [ ] `blocked_route_topology`
- [ ] `blocked_quality`
- [ ] `blocked_stability`
- [ ] `defer_to_webrtc_aec3`

## Evidence Summary

| Gate | Required Proof | Result | Notes |
|------|----------------|--------|-------|
| Built-in speakerphone route | Built-in mic plus built-in speakers tested with baseline and candidate rows. | Pending | |
| Far-end leakage | Candidate improves leakage enough for the accepted threshold. | Pending | |
| Near-end speech | Local speech remains usable in near-end-only rows. | Pending | |
| Double-talk | Local speech and residual far-end leakage are both classified. | Pending | |
| Lineage | Candidate signal maps to live behavior, persisted package truth, incoming reference, and manifest metadata. | Pending | |
| Alignment | Accepted package remains within `durationDifferenceSeconds <= 3` or the current accepted tolerance. | Pending | |
| Stop/quit safety | Active capture clears and candidate resources release on Stop and quit. | Pending | |
| CPU/no-hang | Candidate does not regress accepted realtime safety gates. | Pending | |
| Diagnostics | Exported diagnostics are metadata-only after redaction. | Pending | |

## Product Truth

- Original `mic.wav`, `incoming.wav`, and `manifest.json` remain authoritative:
  Pending.
- Existing leakage finalization remains the authority for clean/leakage/
  unproven package status: Pending.
- No user-facing or release-facing clean speakerphone claim is allowed unless
  `accepted_for_builtin_speakerphone` is selected with all gates passing:
  Pending.

## Next Step

If the primary outcome is not `accepted_for_builtin_speakerphone`, choose the
next action:

- [ ] Continue with `039-webrtc-aec3-speakerphone-spike`.
- [ ] Continue with `040-speakerphone-recording-fallback-decision`.
- [ ] Continue with guidance/onboarding work only.
- [ ] No follow-up; record why the route is out of scope.

## Links

- Spec: `specs/038-apple-voice-processing-spike/spec.md`
- Plan: `specs/038-apple-voice-processing-spike/plan.md`
- Tasks: `specs/038-apple-voice-processing-spike/tasks.md`
- Manual matrix: `specs/038-apple-voice-processing-spike/evidence/manual-runtime-matrix.md`
- Test results: `specs/038-apple-voice-processing-spike/evidence/test-results.md`
