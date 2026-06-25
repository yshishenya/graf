# 052 Installed App Check

All values are metadata-only.

- app_path: `/Applications/2brain Rec.app`
- version: `2026.06.25.14`
- bundle_identifier: `pro.2brain.rec`
- executable_name: `2brain Rec`
- codesign_verify: `pass`
- signature: `adhoc`
- process_state: `running`
- frontmost: `false`
- window_count: `0`
- active_recording_media_handles: `0`
- result: `pass`
- mutation: rebuilt app-only bundle from current master and installed over
  `/Applications/2brain Rec.app`

## Notes

- `/Applications/2brain Rec.app` exists.
- Bundle short version reports `2026.06.25.14`.
- Bundle identifier reports `pro.2brain.rec`.
- `codesign --verify --deep --strict` exits successfully.
- Process inspection found a running app process from `/Applications`.
- Active open media handles matching recording/audio patterns: `0`.
- Frontmost app during the check was Codex, not `2brain Rec`; terminal-driven
  UI inspection could not read the app window, while the app log reported one
  visible main window and an expired cabinet session.
- After relaunch, the embedded cabinet still navigated to auth login with
  expired session state; no fresh recording was created during this check.
- This check does not start, stop, pause, resume, upload, or mutate a
  recording.
