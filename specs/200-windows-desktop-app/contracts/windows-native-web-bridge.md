# Contract: Windows WebView2 navigation and native bridge

Дата: 2026-08-23

## 1. Trusted origin

The production origin is the normalized HTTPS origin configured by the same
cabinet configuration as macOS. The packaged default is:

```text
https://rec.2brain.pro
```

Allowed paths are the existing server-owned desktop route kinds, including:

- `/desktop/meetings`;
- `/desktop/meetings/{meeting_id}`;
- approved meeting share/deletion-report routes;
- approved `/desktop/settings/...` and auth recovery routes already accepted by
  the cabinet route policy.

The implementation must port the existing exact route-kind decision model. It
must not use a broad `contains("desktop")` or `contains("meeting")` check.

Unknown scheme/host/port, `file:`, `data:`, `javascript:`, local filesystem,
loopback not explicitly enabled for local development, downloads requiring native
file access and native-only capture routes are denied or opened externally by a
bounded policy.

## 2. WebView2 settings

For the remote cabinet:

- use WebView2 Evergreen Runtime and check runtime availability before creating
  the control;
- set `AreHostObjectsAllowed = false`;
- enable web messages only when the specific bridge is configured;
- do not expose COM host objects, arbitrary native methods or filesystem APIs;
- disable default script dialogs and unneeded capabilities;
- keep host process standard-user/non-elevated;
- remove or invalidate bridge state when the document/session boundary changes.

## 3. Envelope

Every message uses:

```json
{
  "protocol": "graf.desktop.bridge",
  "version": 1,
  "direction": "native_to_web|web_to_native",
  "message_id": "opaque-id",
  "session_nonce": "ephemeral-nonce",
  "type": "capture_state|custody_summary|runtime_state|open_native_settings|ack|error",
  "payload": {},
  "sent_at_monotonic_ms": 12345
}
```

Limits for the first version:

- maximum serialized message: 64 KiB;
- maximum payload nesting: 8 levels;
- maximum string length: bounded per message type;
- no arrays of audio samples, file paths, cookies, tokens or transcript text;
- one in-memory nonce per WebView session, rotated on navigation/auth boundary.

Native rejects malformed JSON, unknown version/type, wrong direction, invalid
nonce, duplicate/expired message id, unapproved source or oversized payload
without a local side effect.

## 4. Native-to-web events

### `capture_state`

Bounded fields:

```json
{
  "state": "idle|ready|starting|recording|paused|degraded|stopping|finalizing",
  "indicator": "visible|error|hidden",
  "stop_available": true,
  "source_scope": "default_render_mix_plus_microphone",
  "reason_code": null
}
```

This is a display hint only. WebView cannot make the native state active or
stopped from this event.

### `custody_summary`

Contains only aggregate counts and product-owned projection states. It does not
include local paths, raw upload session tokens, signed URLs or private meeting
content.

### `runtime_state`

Contains WebView/runtime/cabinet health class and safe recovery action, not
cookies, response bodies or headers.

## 5. Web-to-native intents

The initial allowlist is intentionally small:

| Type | Effect | Allowed while capture active |
|---|---|---:|
| `open_native_settings` | focus/open native permission or capture settings | yes |
| `open_native_diagnostics` | open bounded diagnostics view | yes |
| `request_runtime_repair` | show/launch supported WebView2 repair path | yes |
| `ack` | acknowledge display delivery only | yes |

`start_recording`, `stop_recording`, `pause_recording`, `resume_recording`,
`read_file`, `write_file`, `run_process`, `set_audio_device`, `get_token`,
`get_cookie` and generic method names are rejected. User control remains native.

## 6. Navigation lifecycle

1. On `NavigationStarting`, normalize and evaluate origin/route before allow.
2. On accepted new document, create a fresh nonce and clear old bridge state.
3. On `ContentLoading`/document-created, do not inject a generic privileged
   script; only the reviewed bridge bootstrap for the exact trusted origin may
   be installed.
4. On auth expiry, route block, WebView recreation or origin change, invalidate
   nonce and stop sending sensitive state.
5. On `WebMessageReceived`, compare the message source with the current WebView
   source/origin, then parse and validate the typed envelope.
6. On runtime or network error, leave native capture/custody state untouched and
   show bounded UI outside the document.

## 7. Security tests

The contract is not complete until tests cover:

- untrusted origin posting a valid-looking message;
- trusted origin with stale nonce;
- malformed JSON and unknown type/version;
- oversized/deep payload;
- replayed message id;
- attempted native control/file/token commands;
- cross-frame/redirect navigation;
- WebView close/recreate during active recording;
- missing runtime and runtime repair failure.

