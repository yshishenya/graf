# Contract: Desktop Custody

Date: 2026-06-26

## Scope

Defines how the macOS app turns local upload queue state into product custody
truth. This contract refines feature `042`; it does not introduce a new queue
engine, a second meeting list, new capture behavior, or server cabinet
presentation.

## Local Ledger

`DesktopUploadQueueDocument.schemaVersion` remains
`desktop-upload-queue.v2` unless implementation discovers a necessary
forward-compatible successor.

The app MUST preserve:

- immutable local recording identity;
- immutable local media revision id;
- local artifact fingerprints and byte counts;
- server meeting/media revision/upload session ids as soon as learned;
- accepted server range truth;
- retry records;
- retention deadline and decision;
- sync conflict state.

Malformed or partially written queue documents MUST be quarantined
metadata-safely and surfaced as blocked custody truth. They MUST NOT be dropped,
overwritten with an empty document, or treated as all-synced.

## Custody Projection

The normal UI consumes a projection, not raw queue transport state.

Minimum projection fields:

| Field | Values |
|-------|--------|
| `custody_state` | `server_unknown_local_saved`, `server_registered`, `upload_session_created`, `partial_uploaded`, `finalized`, `processing`, `delivered`, `retained_awaiting_condition`, `cannot_send`, `terminal_undelivered` |
| `owner` | `product_automatic`, `meeting_owner`, `workspace_admin`, `support`, `policy_lifecycle` |
| `retry_class` | `automatic`, `paused_until_user_action`, `paused_until_admin_action`, `not_retryable`, `terminal` |
| `normal_user_action` | `none`, `sign_in`, `choose_workspace`, `grant_permission`, `open_review`, `open_diagnostics`, `copy_safe_report`, `delete_local_copy` |
| `display_priority` | integer, lower means more urgent |
| `review_available` | boolean |
| `retention_deadline` | optional timestamp |

The projection MAY be implemented as Swift model/helper code over existing
`DesktopUploadQueueItem`; it MUST be testable without rendering SwiftUI.

## Action Policy

Normal user UI MUST NOT expose:

- Retry
- Stop retry
- manual retry
- manual verification
- queue file inspection
- raw upload session controls

Allowed normal user actions:

- sign in;
- choose workspace/account;
- grant local permissions;
- open known server review;
- open diagnostics;
- copy safe report;
- explicitly delete local copy after destructive confirmation.

Destructive confirmation for `delete_local_copy` MUST say that an undelivered
recording will not appear in `2brain Rec` unless a server copy already exists.
The confirmation must not promise recovery after verified deletion, tombstone,
cryptographic unrecoverability, or policy terminalization.

Automatic states show no primary action. They may show progress, saved-local
truth, and the fact that the app will retry.

## Server Reconciliation

Before upload attempt, finalize, review-open, terminal decision, or purge
acknowledgement, the desktop MUST reconcile with server truth when a server
identity exists.

`404 recording_not_found` from
`GET /api/v1/desktop/recordings/{local_recording_id}/sync-state` means:

- server does not know the recording yet;
- local custody remains active;
- desktop may register/reuse a server meeting when allowed;
- the UI must not fabricate a server row or review route.

`401`, `403`, `409`, `410`, `413`, `429`, and `503` map through stable problem
codes and owner/action policy. Copy must not parse human text to decide action.

## Custody Runner Triggers

The desktop custody runner MUST run on:

- app launch;
- app activation;
- auth/session change, including WebView sign-in;
- network reachability recovery;
- wake from sleep;
- scheduled retry time;
- local recording finalization.

The runner MUST NOT require the meeting WebView to be open.

## Purge Acknowledgement

The desktop may list server local purge tasks through existing desktop APIs.
It MUST acknowledge a task as complete only after local artifacts are:

- actually removed; or
- tombstoned; or
- cryptographically rendered unrecoverable.

If verification fails, the desktop MUST report metadata-safe failure instead of
acknowledging success.

## UI Surface Rules

- The server-owned WebView meeting list remains the only meeting list when the
  cabinet is configured.
- Server-unknown custody appears only as aggregate native shell status and
  optional secondary details outside the server-owned list.
- Server-known recordings are not duplicated by native rows.
- A review route opens only for a server-known recording with review
  availability.
- The default visible native surface has one owner for aggregate custody status.
  Other native views may consume the same projection, but they must not create a
  second primary indicator, second meeting list, or competing disclosure.
- Status must include text and VoiceOver-readable labels; color alone is not
  sufficient.

## Forbidden Content

Normal UI, diagnostics, logs, reports, specs, and evidence MUST NOT expose:

- raw audio;
- transcript text;
- local absolute paths;
- credentials;
- bearer tokens;
- cookies;
- signed URLs;
- secret values;
- private meeting content.
