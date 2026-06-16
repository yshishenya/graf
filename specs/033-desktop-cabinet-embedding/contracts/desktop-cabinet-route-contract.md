# Desktop Cabinet Route Contract

## Purpose

Define which server-owned product routes the macOS app may embed and how the
native shell handles everything else.

## Allowed Embedded Routes

| Route | Meaning | Allowed In 033 |
|---|---|---|
| `/desktop/meetings` | Embedded meeting list | Yes |
| `/desktop/meetings/{meeting_id}` | Embedded meeting review detail | Yes |

Allowed routes may include safe query parameters that do not contain secrets,
signed URLs, raw transcript content, raw audio references, or live local paths.

## Blocked Or Future-Gated Routes

The desktop shell must not execute these inside the embedded surface in `033`:

- share link creation or share settings;
- export/download actions;
- delete/retention execution;
- account/admin/billing settings;
- local diagnostics bundles;
- local file picker/upload picker;
- recording start/stop;
- microphone/speaker/device routing;
- permission recovery;
- driver/system-audio recovery.

Blocked routes should show a bounded message such as "This action opens in a
future browser-owned release" or "This local control stays in the app shell."
The message must not imply the action has executed.

## External Links

External URLs are not embedded by default. The policy may classify a destination
as `openExternally` only for non-mutating help or legal/documentation links. Any
unknown destination is blocked.

## Route Decision Reasons

Stable metadata-safe reason values:

- `allowed_meeting_list`
- `allowed_meeting_detail`
- `blocked_future_governance`
- `blocked_native_capture_control`
- `blocked_local_file_or_diagnostic`
- `blocked_unknown_route`
- `open_external_safe_link`
- `invalid_url`

## Acceptance

- Allowed list/detail routes open in the embedded area.
- Blocked routes never mutate server, local files, capture state, upload state,
  deletion state, share state, or export/download state.
- Route decision logs/evidence contain reason values and sanitized route kinds,
  not tokens, signed URLs, transcript text, raw audio references, or live paths.
