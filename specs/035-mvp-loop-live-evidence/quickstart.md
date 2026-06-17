# Quickstart: MVP Loop Live Evidence

Feature: `035-mvp-loop-live-evidence`

## Prerequisites

- Current branch: `035-mvp-loop-live-evidence`.
- Accepted baseline includes feature `022-meeting-mute-truth`.
- Permissioned desktop runtime path: `/Applications/2brain Rec.app`.
- Web owner review can be opened with safe live metadata or fixture data.
- Reference observations must remain clean-room and commit-safe.

## 1. Spec And Evidence Safety

```sh
rg -n "NEEDS CLARIFICATION|ACTION REQUIRED|TODO|TBD|TKTK|\\?\\?\\?" \
  specs/035-mvp-loop-live-evidence

rg -n -i "raw audio|transcript text|private email|signed url|signed_url|password|api[_-]?key|token|credential|private Krisp|meeting content" \
  specs/035-mvp-loop-live-evidence docs/evidence/035-mvp-loop-live-evidence
```

Expected: no unresolved placeholders; forbidden-content matches are policy
wording only.

## 2. Installed Desktop Runtime

```sh
TWO_BRAIN_REC_ALLOW_ADHOC_APP_SIGNING=1 sh apps/macos/Installer/Scripts/build-local-installer.sh
TWO_BRAIN_REC_USER_APP_DEST="/Applications/2brain Rec.app" sh apps/macos/Installer/Scripts/install-user-app.sh
open -n "/Applications/2brain Rec.app"
ps -axo pid,command | rg '/Applications/2brain Rec.app/Contents/MacOS/2brain Rec'
```

Manual flow:

1. Start recording.
2. Capture active state.
3. Pause.
4. Capture paused state.
5. Resume.
6. Capture resumed state.
7. Stop.
8. Capture stopped/list state.

Expected: visible local indicator, one-action Stop, truthful Pause/Resume state,
and no hidden recording.

## 3. Latest Artifact Validation

```sh
apps/macos/Scripts/validate-meeting-mute-truth.sh --latest-artifact-directory
```

Expected: PASS for the artifact created by the installed desktop run, or a
recorded blocker that prevents any stronger claim.

## 4. Web Owner Review Evidence

Open the owner web/cabinet list and detail surfaces with safe metadata or safe
fixtures. Capture only commit-safe screenshots or write blocker notes when live
private content cannot be committed.

Expected: meeting list/detail/governance and notes/action truth are represented
as ready, blocked, or deferred.

## 5. Server And macOS Validation

```sh
cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q \
  tests/integration/test_mvp_loop_readiness_report.py \
  tests/unit/test_mvp_loop_readiness_matrix.py

infra/scripts/ci-local.sh

swift build --package-path apps/macos

swift test --package-path apps/macos --filter 'SystemAudioLocalization|SystemAudioPermission|CaptureControl|DesktopUploadQueue|SystemAudioDriverParked|AppControlAccessibility|MeetingMuteTruth'
```

Expected: all commands pass, or failures are recorded as blockers.

## 6. Readiness Outputs

Generate or refresh:

- `docs/evidence/035-mvp-loop-live-evidence/readiness-report.json`
- `docs/evidence/035-mvp-loop-live-evidence/readiness-report.md`
- `docs/evidence/035-mvp-loop-live-evidence/launch-gap-register.md`
- `docs/evidence/035-mvp-loop-live-evidence/validation-log.md`
- `docs/evidence/035-mvp-loop-live-evidence/clean-room-reference.md`

Expected: no stale next-slice recommendation and exactly one strongest claim.

## 7. Tracker And Closeout

```sh
gh issue list --repo yshishenya/crisp --state open --label feature:035 --limit 120 --json number,title
git diff --check
```

Expected: GitHub issue sync matches `tasks.md`, whitespace check passes, and
open/closed tracker state matches task completion.
