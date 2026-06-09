# Permission Matrix

Feature: `025-system-audio-capture-pivot`

This matrix records expected permission outcomes. It is metadata-only: do not
paste raw audio, transcripts, meeting content, credentials, tokens, signed URLs,
or personal contact details.

| Microphone | Screen/System Audio | Normal Recording Outcome | Visible Copy | Manifest Outcome | Result | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| granted | granted | accepted start allowed | no permission blocker | eligible for `saved` if tracks are complete and aligned | not-tested | Manual permission run pending |
| denied | granted | blocked before accepted start | microphone access required | `permission_denied` if explicit degraded attempt is recorded | not-tested | Manual permission run pending |
| granted | denied/restricted/unknown | blocked before accepted start | Screen/System Audio access required | `permission_denied` if explicit degraded attempt is recorded | not-tested | Manual permission run pending |
| denied | denied/restricted/unknown | blocked before accepted start | Microphone and Screen/System Audio access required | `permission_denied` if explicit degraded attempt is recorded | not-tested | Manual permission run pending |
| permission revoked while recording | any required permission missing | stop/finalize as degraded or failed, not saved | permission changed/retry copy required | `permission_denied` or specific capture failure reason | not-tested | Manual permission run pending |

Blocked, failed, degraded, and not-tested rows are not acceptance.

## Manual Run Rules

- Do not reset TCC from a script.
- Change microphone and Screen/System Audio permissions only through System
  Settings.
- Relaunch the packaged app after each permission change before pressing Record.
- Record only visible blocker copy, recovery action, manifest status/failure
  reason, and whether the app blocked before false success.
- Do not paste raw audio, transcripts, screen contents, meeting names, personal
  details, credentials, tokens, or signed URLs into this file.

## 2026-06-08 Metadata Validator Run

- Run ID: `20260608T174858Z`
- Timestamp: `2026-06-08T17:48:58Z`
- Commit: `967c381`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--permission-matrix`
- Validator result: `blocked`
- Reason: Manual TCC grant/deny/revoke rows are still required before acceptance.
- Safe checks: required rows present; blocked/degraded/not-tested rows are not counted as acceptance; this helper avoids HAL probes and driver reinstall steps.

## 2026-06-08 Metadata Validator Run

- Run ID: `20260608T230809Z`
- Timestamp: `2026-06-08T23:08:09Z`
- Commit: `f7a7454`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--permission-matrix`
- Validator result: `blocked`
- Reason: Manual TCC grant/deny/revoke rows are still required before acceptance.
- Safe checks: required rows present; blocked/degraded/not-tested rows are not counted as acceptance; this helper avoids HAL probes and driver reinstall steps.

## Metadata Validator Run

- Run ID: `20260609T012802Z`
- Timestamp: `2026-06-09T01:28:02Z`
- Commit: `6395360`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--permission-matrix`
- Validator result: `blocked`
- Reason: Manual TCC grant/deny/revoke rows are still required before acceptance.
- Safe checks: required rows present; blocked/degraded/not-tested rows are not counted as acceptance; this helper avoids HAL probes and driver reinstall steps.

## Metadata Validator Run

- Run ID: `20260609T043348Z`
- Timestamp: `2026-06-09T04:33:48Z`
- Commit: `716f3be`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--permission-matrix`
- Validator result: `blocked`
- Reason: Manual TCC grant/deny/revoke rows are still required before acceptance.
- Safe checks: required rows present; blocked/degraded/not-tested rows are not counted as acceptance; this helper avoids HAL probes and driver reinstall steps.

## Metadata Validator Run

- Run ID: `20260609T052529Z`
- Timestamp: `2026-06-09T05:25:29Z`
- Commit: `62616bb`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--permission-matrix`
- Validator result: `blocked`
- Reason: Manual TCC grant/deny/revoke rows are still required before acceptance.
- Safe checks: required rows present; blocked/degraded/not-tested rows are not counted as acceptance; this helper avoids HAL probes and driver reinstall steps.
