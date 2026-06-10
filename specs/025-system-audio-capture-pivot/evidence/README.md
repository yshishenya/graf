# System Audio Capture Pivot Evidence

This directory stores validation evidence for feature `025-system-audio-capture-pivot`.

Evidence files must be metadata-only by default. Do not store raw audio,
transcript text, meeting content, credentials, tokens, signed URLs, personal
contact details, or secrets here.

Required evidence files are created by later tasks:

- `test-results.md`
- `cpu-gates.md`
- `no-hal-probe.md`
- `development-30-minute.md`
- `release-75-minute.md`
- `permission-matrix.md`
- `artifact-matrix.md`
- `driver-parked.md`
- `scope-review.md`

Acceptance evidence must distinguish `accepted`, `degraded`, `blocked`,
`failed`, and `not-tested`. Blocked, failed, degraded, or not-tested rows are
not acceptance.
