# 051 Installed App Check

All values are metadata-only.

- app_path: `/Applications/2brain Rec.app`
- version: `2026.06.25.6`
- bundle_identifier: `pro.2brain.rec`
- executable_name: `2brain Rec`
- codesign: `pass`
- codesign_signature: `adhoc`
- launch_state: `running`
- frontmost: `false`
- window_count: `1`
- active_recording_open_media_files: `0`
- cabinet_truth_state: `not_checked_in_T017`
- result: `pass`

## Notes

- `/Applications/2brain Rec.app` exists.
- Bundle version and short version both report `2026.06.25.6`.
- `codesign --verify --deep --strict --verbose=2` reports the bundle is valid
  on disk and satisfies its designated requirement.
- Process inspection found a running app process and no open recording media
  files matching `Recordings`, `.wav`, `.m4a`, `.caf`, `mic.wav`, or
  `incoming.wav`.
- This check does not start, stop, pause, resume, upload, or mutate a
  recording.
