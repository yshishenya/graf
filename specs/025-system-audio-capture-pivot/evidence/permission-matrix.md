# Permission Matrix

Feature: `025-system-audio-capture-pivot`

This matrix records expected permission outcomes. It is metadata-only: do not
paste raw audio, transcripts, meeting content, credentials, tokens, signed URLs,
or personal contact details.

| Microphone | Screen/System Audio | Normal Recording Outcome | Visible Copy | Manifest Outcome | Result | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| granted | granted | accepted start allowed | no permission blocker | eligible for `saved` if tracks are complete and aligned | passed | Manual permission run reported by product owner on 2026-06-10; no false blocker observed |
| denied | granted | blocked before accepted start | microphone access required | `permission_denied` if explicit degraded attempt is recorded | passed | Manual permission run reported by product owner on 2026-06-10; microphone blocker observed |
| granted | denied/restricted/unknown | blocked before accepted start | Screen/System Audio access required | `permission_denied` if explicit degraded attempt is recorded | passed | Manual permission run reported by product owner on 2026-06-10; Screen/System Audio blocker observed |
| denied | denied/restricted/unknown | blocked before accepted start | Microphone and Screen/System Audio access required | `permission_denied` if explicit degraded attempt is recorded | passed | Manual permission run reported by product owner on 2026-06-10; combined blocker observed |
| permission revoked while recording | any required permission missing | stop/finalize as degraded or failed, not saved | permission changed/retry copy required | `permission_denied` or specific capture failure reason | passed | Manual permission run reported by product owner on 2026-06-10; revoked permission did not produce false saved success |

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

## 2026-06-10 Permission Matrix Acceptance

- Decision: accepted for T071 / issue #307.
- Acceptance source: product owner reported that Permission matrix (T071) was checked manually.
- Scope: granted/granted, microphone denied, Screen/System Audio denied or restricted, both denied/restricted/unknown, and permission revoked while recording.
- Result: all five required permission scenarios are recorded as `passed`.
- Safety note: this entry is metadata-only and records no audio, transcripts, meeting content, credentials, tokens, signed URLs, or personal contact details.

## Metadata Validator Run

- Run ID: `20260610T112753Z`
- Timestamp: `2026-06-10T11:27:53Z`
- Commit: `3fca17e`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--permission-matrix`
- Validator result: `blocked`
- Reason: Manual TCC grant/deny/revoke rows are still required before acceptance.
- Safe checks: required rows present; blocked/degraded/not-tested rows are not counted as acceptance; this helper avoids HAL probes and driver reinstall steps.
