# 052 Installed App Check

All values are metadata-only.

- app_path: `/Applications/2brain Rec.app`
- version: `2026.06.25.6`
- bundle_identifier: `pro.2brain.rec`
- executable_name: `2brain Rec`
- codesign_verify: `pass`
- signature: `adhoc`
- process_state: `running`
- frontmost: `false`
- window_count: `0`
- active_recording_media_handles: `0`
- result: `pass`
- mutation: `none`

## Notes

- `/Applications/2brain Rec.app` exists.
- Bundle short version reports `2026.06.25.6`.
- Bundle identifier reports `pro.2brain.rec`.
- `codesign --verify --deep --strict` exits successfully.
- Process inspection found a running app process.
- Active open media handles matching recording/audio patterns: `0`.
- Frontmost app during the check was Codex, not `2brain Rec`; the app had no
  visible window at that instant.
- This check does not start, stop, pause, resume, upload, or mutate a
  recording.
