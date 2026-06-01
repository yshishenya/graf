# Checklist: Diagnostics Requirement Quality

**Purpose**: Validate diagnostic requirements for route failures without leaking
meeting content or secrets.

- [x] CHK001 Are allowed diagnostic fields listed separately from forbidden fields?
- [x] CHK002 Are raw audio, transcript text, credentials, tokens, and signed URLs forbidden?
- [x] CHK003 Are route evidence, failure reason, and recovery action represented?
- [x] CHK004 Are passthrough start/degraded/stop events represented?
- [x] CHK005 Are track evidence and degraded finalization represented?
- [x] CHK006 Is diagnostic output local-only for this feature?
- [x] CHK007 Are browser validation failures represented without storing meeting content?
- [x] CHK008 Does the spec avoid Langfuse, MediaScribe, or server egress in this feature?
- [x] CHK009 Are stream-health counters represented without storing raw audio?
- [x] CHK010 Are loopback leakage and speaker-reference metrics represented as metadata only?

## Notes

Diagnostics requirements are complete enough for task generation. Implementation
must keep logs status-first and content-free, including capturability, frame,
empty-buffer, dropout, and leakage metrics.
