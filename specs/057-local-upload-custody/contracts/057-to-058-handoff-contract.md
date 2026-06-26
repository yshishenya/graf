# Contract: 057 To 058 Handoff

Date: 2026-06-26

## Scope

Feature `057` defines custody truth and stable machine-readable fields. Feature
`058` owns server cabinet presentation and may render these fields in the
refactored web interface.

Feature `057` MUST NOT edit:

- `apps/server/src/twobrain_rec_server/cabinet/web.py`
- server cabinet templates
- server cabinet CSS/static files
- meeting-list/detail HTML markup
- status-chip rendering

## Producer Responsibilities For 057

`057` may add or stabilize fields in API/read-model layers:

- `apps/server/src/twobrain_rec_server/api/ingest.py`
- `apps/server/src/twobrain_rec_server/api/cabinet.py`
- `apps/server/src/twobrain_rec_server/api/schemas.py`
- `apps/server/src/twobrain_rec_server/domain/statuses.py`
- `apps/server/src/twobrain_rec_server/ingest/desktop_sync.py`
- `apps/server/src/twobrain_rec_server/ingest/meetings.py`
- `apps/server/src/twobrain_rec_server/cabinet/queries.py`, only for
  structured read-model fields
- `apps/server/src/twobrain_rec_server/cabinet/view_models.py`, only for
  structured read-model fields

## Consumer Responsibilities For 058

`058` renders:

- list/detail layout;
- status chips;
- cabinet copy;
- responsive presentation;
- visual hierarchy;
- server cabinet accessibility and browser QA.

`058` MUST NOT parse Russian text or local queue internals to determine
custody state.

## Shared Field Contract

Where a server-known recording needs custody status in a server read model,
the read model must expose structured fields equivalent to:

```json
{
  "custody": {
    "state": "partial_uploaded",
    "upload_state": "partial_uploaded",
    "processing_state": "pending_processing",
    "owner": "product_automatic",
    "retry_class": "automatic",
    "normal_user_action": "none",
    "display_priority": 5,
    "review_available": false,
    "review_desktop_url": null,
    "safe_incident_available": false,
    "retention_deadline": "2026-07-03T00:00:00Z",
    "copy_key": "custody.uploading",
    "metadata_safety": "metadata_only"
  }
}
```

This object MUST be a structured field on the API/read-model response, for
example `MeetingListItem.custody` or an equivalent nested field. Feature `057`
MUST NOT use `status_label`, `status_reason`, `primary_action`, server-rendered
copy, or visual status-chip labels as the machine contract for feature `058`.

Required enum values:

- `state`: `server_registered`, `upload_session_created`, `partial_uploaded`,
  `finalized`, `processing`, `delivered`, `retained_awaiting_condition`,
  `cannot_send`, `terminal_undelivered`.
- `upload_state`: `not_started`, `session_created`, `partial_uploaded`,
  `finalized`, `blocked`, `terminal`.
- `processing_state`: `not_submitted`, `pending_processing`, `processing`,
  `processed`, `blocked`, `failed_retryable`, `failed_terminal`, `canceled`.
- `owner`: `product_automatic`, `meeting_owner`, `workspace_admin`, `support`,
  `policy_lifecycle`.
- `retry_class`: `automatic`, `paused_until_user_action`,
  `paused_until_admin_action`, `not_retryable`, `terminal`.
- `normal_user_action`: `none`, `sign_in`, `choose_workspace`,
  `grant_permission`, `open_review`, `open_diagnostics`, `copy_safe_report`,
  `delete_local_copy`.
- `metadata_safety`: `metadata_only`.

## Copy Key Catalog

`copy_key` is a stable machine-readable hint. Feature `058` owns final Russian
copy and visual rendering, but it MUST use keys from this catalog or add a new
key to this contract before rendering a new custody state.

Initial keys:

| Key | Intended meaning | Default owner/action |
|-----|------------------|----------------------|
| `custody.all_synced` | No local custody needs attention | `product_automatic` / `none` |
| `custody.saving_local` | Local package is being prepared after stop | `product_automatic` / `none` |
| `custody.saved_will_send` | Local recordings are safe and will send automatically | `product_automatic` / `none` |
| `custody.uploading` | One or more recordings are uploading or partially uploaded | `product_automatic` / `none` |
| `custody.known_by_server` | Server meeting exists; server list owns the row | `product_automatic` / `open_review` when available |
| `custody.needs_sign_in` | Authentication must be refreshed | `meeting_owner` / `sign_in` |
| `custody.needs_workspace` | Workspace/account must be selected or fixed | `meeting_owner` / `choose_workspace` |
| `custody.needs_admin` | Workspace policy, quota, access, legal hold, or device state blocks delivery | `workspace_admin` / `copy_safe_report` |
| `custody.cannot_send` | Local artifact cannot become a valid upload | `support` / `open_diagnostics` or `delete_local_copy` |
| `custody.retention_warning` | Local retention/purge deadline is approaching | `policy_lifecycle` / context-specific safe action |
| `custody.terminal_undelivered` | Delivery ended without server review content | `policy_lifecycle` / `copy_safe_report` |
| `custody.unknown_blocked` | Conservative fallback for unknown enum or absent optional fields | `support` / `copy_safe_report` |

Feature `058` MUST NOT parse Russian copy, status-chip labels, queue filenames,
or desktop-only enum names to choose rendering.

## Problem Codes

Problem responses for registration, sync-state, upload session, part upload,
finalize, reconcile, and purge endpoints must expose stable `Problem.code`
values by class:

| Class | Example codes |
|-------|---------------|
| Auth | `auth_required`, `session_expired` |
| Access/policy | `access_revoked`, `policy_blocked`, `legal_hold_blocked` |
| Quota | `quota_blocked`, `storage_quota_exceeded` |
| Deletion | `server_meeting_deleted`, `media_revision_deleted` |
| Device | `stale_device_identity`, `device_revoked` |
| Conflict | `idempotency_conflict`, `media_revision_conflict`, `checksum_conflict`, `range_conflict` |
| Dependency | `dependency_unavailable`, `sync_state_dependency_unavailable` |
| Payload | `payload_too_large`, `unsupported_package` |
| Unknown transient | `unknown_transient` |
| Server unknown | `recording_not_found` |

Human-readable `title` and `detail` are not contract fields for UI decisions.

When a problem response affects desktop custody, it must expose one of these
machine-readable shapes:

```json
{
  "code": "policy_blocked",
  "custody_owner": "workspace_admin",
  "retry_class": "paused_until_admin_action",
  "normal_user_action": "copy_safe_report",
  "metadata_safety": "metadata_only"
}
```

or an equivalent nested extension:

```json
{
  "code": "policy_blocked",
  "custody": {
    "owner": "workspace_admin",
    "retry_class": "paused_until_admin_action",
    "normal_user_action": "copy_safe_report",
    "metadata_safety": "metadata_only"
  }
}
```

If an older endpoint cannot return those fields yet, the desktop may map
stable `Problem.code` values through this contract, but feature `058` MUST NOT
derive owner/action from human copy.

Legacy action names such as `manual_review`, `stop_upload`, `retry_later`,
`retry_future`, `open_desktop_queue`, and `contact_operator` are not 057/058 UI
contract values. They must be mapped to the normalized `owner`,
`retry_class`, and `normal_user_action` fields before reaching the desktop
custody projection or 058 read model.

## Fallback Behavior

If `058` sees an unknown enum value:

- render a non-ready, non-destructive state;
- use `owner=support`;
- use `normal_user_action=copy_safe_report`;
- do not show review as ready unless `review_available=true`;
- do not show Retry or transport controls.

If optional custody fields are absent:

- preserve existing server list/detail rendering;
- do not infer local-only rows;
- do not parse raw queue state;
- use the existing processing/upload status as a conservative wait/block state.

## Cross-Feature Validation

Before implementation tasks that add 057 behavior begin, `057` foundation tasks
must create fixture or API/read-model tests proving the contract expectations.
Those tests may fail until the corresponding schema/read-model implementation is
complete, but they must pass before feature closeout:

- one offline recording that later registers and partially uploads has one
  server-known read-model row;
- native shell shows aggregate custody only;
- no native local row is injected into WebView;
- opening a WebView route while upload continues does not force route jumps;
- `058` can render the structured fields without importing desktop custody
  logic.

## Forbidden Content

The handoff contract and fixtures MUST NOT include raw audio, transcript text,
private local paths, bearer tokens, cookies, signed URLs, credentials, secret
values, or private meeting content.
