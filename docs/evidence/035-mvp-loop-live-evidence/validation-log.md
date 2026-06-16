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
| prod-root-route | web | `curl -I -L --max-time 15 https://rec.2brain.pro` | blocked | `HTTP 404` JSON root | Root is not the web cabinet route. |
| prod-meetings-route | web | `curl -i -L --max-time 15 https://rec.2brain.pro/meetings` | blocked | `HTTP 401 missing_auth_context` | Route exists but requires auth context; no private session evidence committed. |
| chrome-meetings-route | web | Open `https://rec.2brain.pro/meetings` in Chrome automation | blocked | `net::ERR_BLOCKED_BY_CLIENT` | Browser-side blocker observed while preserving private Chrome data. |
| web-list-evidence | web | Document metadata-safe list route evidence | pass | `screenshots/web-meeting-list-evidence.md` | Fixture-backed coverage, live owner proof blocked by auth context. |
| web-detail-evidence | web | Document metadata-safe detail route evidence | pass | `screenshots/web-meeting-detail-evidence.md` | Detail route family covered locally; private live detail not committed. |
| web-governance-evidence | web | Document metadata-safe governance evidence | pass | `screenshots/web-governance-evidence.md` | No destructive production action performed. |
| readiness-output-generation | readiness | `cd apps/server && PYTHONPATH=src uv run python scripts/generate_mvp_loop_readiness.py --feature 035-mvp-loop-live-evidence --output-dir ../../docs/evidence/035-mvp-loop-live-evidence` | pass | `readiness-report.json`, `readiness-report.md`, `launch-gap-register.md` | Output closes stale desktop gap and keeps web auth, notes/actions, and production user journey as blockers. |
| current-status-update | docs | Update `docs/current-product-status.md` | pass | `docs/current-product-status.md#next-product-slice` | Next slice is now `036-owner-review-live-polish`; 035 is no longer recommended as next. |
| changelog-update | docs | Update `CHANGELOG.md` | pass | `CHANGELOG.md#unreleased` | Records 035 validation-only evidence and metadata-safe web blocker. |

Further entries are added as tasks T011-T040 complete.
