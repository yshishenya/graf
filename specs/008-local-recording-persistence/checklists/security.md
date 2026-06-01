# Security Checklist: Local Recording Persistence

**Purpose**: Validate privacy, local artifact, egress, and diagnostics requirements
before implementation.

- [x] Requirements explicitly forbid upload, MediaScribe, Langfuse content traces,
  dashboard publication, and external egress in this slice.
- [x] Requirements distinguish local artifact creation from retention and
  deletion promises.
- [x] Requirements require metadata-only diagnostics and evidence.
- [x] Requirements forbid raw audio, transcript text, meeting content,
  credentials, tokens, signed URLs, passwords, API keys, and live secret paths in
  diagnostics.
- [x] Manifest contract uses generated ids and safe filenames rather than live
  absolute paths for diagnostics.
- [x] Track status must be truthful when local artifacts are missing, empty,
  degraded, or failed.
- [x] Directory creation or write failure has a concrete blocked/fail-closed
  behavior.
- [x] Local files are explicitly scoped as MVP-local artifacts; encrypted buffer,
  retention, deletion, and upload are separate future slices.
- [x] Validation includes forbidden-content scan across code, fixtures, QA, and
  specs.

## Notes

- No open security requirement gaps before task generation.
