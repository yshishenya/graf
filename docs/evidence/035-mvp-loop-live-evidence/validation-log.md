# Validation Log: 035 MVP Loop Live Evidence

Feature: `035-mvp-loop-live-evidence`

## Command And Manual Evidence

| ID | Surface | Command or action | Result | Evidence | Notes |
|----|---------|-------------------|--------|----------|-------|
| setup-evidence-scaffold | docs | Created README, validation log, clean-room note, and screenshot directory | pass | `docs/evidence/035-mvp-loop-live-evidence/` | Metadata-safe scaffold only. |
| runtime-path-check | desktop | `open /Applications/2brain Rec.app`; AppleScript process path check | pass | `/Applications/2brain Rec.app` | Active app process was confirmed from the installed bundle path before implementation evidence capture. |
| focused-readiness-foundation | server | `PYTHONPATH=src uv run --extra dev pytest -q tests/integration/test_mvp_loop_live_evidence.py tests/integration/test_mvp_loop_readiness_report.py tests/unit/test_mvp_loop_readiness_matrix.py tests/contract/test_mvp_loop_readiness_contract.py` | pass | `apps/server/tests/` | 28 tests passed after 035 report/model/test updates. |
| issue-sync | tracker | `gh issue list --repo yshishenya/crisp --state all --label feature:035 --limit 120 --json number --jq 'length'` | pass | `specs/035-mvp-loop-live-evidence/issues.md` | 43 GitHub issues created and mapped: #1064-#1106. |
| installed-app-proof | desktop | `rsync -naci --delete staged-app /Applications/2brain Rec.app`; `codesign --verify --deep --strict /Applications/2brain Rec.app`; process path check | pass | `/Applications/2brain Rec.app` | Dry-run produced no differences; codesign verification passed; active process path was `/Applications/2brain Rec.app`. |
| desktop-idle-ready | desktop | Capture installed idle/ready state | pass | `screenshots/2026-06-16-desktop-idle-ready-applications.png` | Shows stopped state, Start control, upload queue truth, and local mode. |
| desktop-active-recording | desktop | Start recording and capture active state | pass | `screenshots/2026-06-16-desktop-active-recording-applications.png` | Shows visible recording indicator, Pause/Stop controls, and active level meters. |
| desktop-paused-recording | desktop | Pause recording and capture paused state | pass | `screenshots/2026-06-16-desktop-paused-recording-applications.png` | Shows paused state, Continue/Stop controls, and mute-truth limitation copy. |
| desktop-resumed-recording | desktop | Resume recording and capture resumed state | pass | `screenshots/2026-06-16-desktop-resumed-recording-applications.png` | Shows active recording after pause with live level meters. |
| desktop-stopped-list | desktop | Stop recording and capture stopped/list state | pass | `screenshots/2026-06-16-desktop-stopped-list-applications.png` | Shows stopped state and the new local recording row. |
| latest-artifact-validator | desktop | `apps/macos/Scripts/validate-meeting-mute-truth.sh --latest-artifact-directory` | pass | local artifact `directoryId=20260616-163553-91CF43DD-71DA-45BA-9995-0C0788D49D7F` | Full local path intentionally omitted from committed docs; no raw audio copied. |

Further entries are added as tasks T011-T040 complete.
