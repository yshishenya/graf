# Recording-Assisted Acceptance (Deferred)

This checklist is a future release gate. It is intentionally blocked until local
recording exists and the recording slice defines retention, deletion, and
content-review rules.

## Blocked Until

- [ ] Local recording support exists.
- [ ] Recording retention policy exists.
- [ ] Recording deletion policy exists.
- [ ] Recorded evidence review rules avoid uncontrolled egress and secrets.

## Future Evidence

- [ ] Long-duration call replay covers the local microphone path.
- [ ] Long-duration call replay covers the remote speaker path.
- [ ] Recorded evidence proves channel separation.
- [ ] Recorded evidence proves no remote-to-mic loopback.
- [ ] Recorded evidence allows distortion and dropout review.
- [ ] Route state timeline is captured alongside recording evidence.
- [ ] Upload, transcription, MediaScribe, and Langfuse behavior match the
  future recording feature policy.

## Current Slice Rule

- [x] 005 pre-recording hardening may reference this checklist but must not
  require recording-derived evidence before local recording exists.
