# Contract: Deferred Recording-Assisted Acceptance

This contract defines the future gate that should run after local recording
exists. It is intentionally not a blocker for this pre-recording hardening
slice.

## Blocked Until

- Local recording exists.
- Recording retention and deletion rules exist.
- Recorded evidence can be reviewed without exposing secrets or uncontrolled
  egress.

## Future Evidence

The future recording-assisted acceptance run should include:

- long-duration call replay;
- recorded local microphone path;
- recorded remote speaker path;
- channel separation confirmation;
- no remote-to-mic loopback confirmation;
- distortion/dropout review;
- route state timeline;
- explicit proof that upload/transcription/MediaScribe/Langfuse behavior matches
  that future feature's policy.

## Current Slice Rule

Tasks for this feature may create the checklist or placeholder artifact, but
must not require recording-derived evidence before recording exists.
