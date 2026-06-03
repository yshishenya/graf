# Driver Checklist: Local Recording Persistence

**Purpose**: Validate driver, shared-memory, passthrough, and realtime safety
requirements before implementation.

- [x] Requirements preserve driver-first macOS MVP and avoid no-driver fallback.
- [x] Plan keeps file IO outside HAL/Core Audio callbacks.
- [x] Writer contract forbids allocation, logging, lock waits, process launches,
  UI work, network calls, and file IO in realtime callbacks.
- [x] Plan uses existing shared memory mic and mirrored speaker capture surfaces.
- [x] Missing remote speaker mirror frames must degrade/fail the track instead of
  claiming a complete recording.
- [x] Stop/finalization must not tear down non-recording passthrough.
- [x] Validation includes existing realtime safety scan.
- [x] Validation includes short local artifact smoke rather than pretending
  publication-only Core Audio visibility proves audio persistence.
- [x] Requirements maintain one active manual recording at a time.

## Notes

- No driver plan blocker before implementation. Realtime code review remains
  required after code changes.
