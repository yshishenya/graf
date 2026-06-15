# Contract: Embedded Product UI For Desktop Shells

## Purpose

Define how one server-owned product UI is embedded into platform desktop shells
without duplicating product workflows in native macOS, Windows, or Linux code.

## Ownership Model

Native desktop shells own platform-critical capabilities:

- recording start/stop and visible capture indicator;
- system audio and microphone permissions;
- local recording buffer and local package truth;
- local upload queue truth and retry/recovery;
- tray/menu status surfaces;
- local diagnostics and support bundles;
- embedded-web host, auth/session holder, route guard, and native bridge.

Server/web owns variable product UI:

- meeting library and filters allowed in the desktop subset;
- manual upload metadata and server upload status;
- processing and transcript/notes status;
- meeting review, transcript, notes, decisions, actions, and speaker assignment;
- account/workspace summaries and basic settings;
- copy, localization, status wording, feature flags, and route evolution.

## Required Route Fields

Every embedded route must declare:

- `route_id`
- `web_path`
- `embedded_path`
- `allowed_shells`: `macos`, `windows`, `linux`
- `owner`: `server_product_ui` or `platform_native`
- `auth_required`
- `status_dependencies`
- `native_shell_requirements`
- `native_bridge_methods`
- `browser_handoff_reason` when not embedded
- `offline_fallback`
- `csp_and_webview_policy`

## Initial Embedded Route Manifest

All route rows must include the required fields above. `browser_handoff_reason`
uses `n/a: embedded` when the route is allowed inside the desktop shell.

| route_id | web_path | embedded_path | allowed_shells | owner | auth_required | status_dependencies | native_shell_requirements | native_bridge_methods | browser_handoff_reason | offline_fallback | csp_and_webview_policy |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `cabinet.meetings.recent` | `/meetings` | `/desktop/meetings` | `macos`, `windows`, `linux` | `server_product_ui` | yes, except explicit local-policy read mode | session, workspace, meeting status, upload status | Keep native capture strip visible when recording; native owns only route host and minimal connection/session/policy badge. | `openExternal(url)`, `showLocalQueue(meetingId)` | n/a: embedded | Show cached recent rows if available; otherwise show sync-unavailable empty state while recording/local queue remains usable. | Rec server origin only; no arbitrary navigation; server CSP enforced; bridge disabled until route manifest matches. |
| `cabinet.meeting.review` | `/meetings/:id` | `/desktop/meetings/:id` | `macos`, `windows`, `linux` | `server_product_ui` | yes | meeting access, transcript status, notes status, deletion/access state | Web cannot show record or stop controls; native strip owns capture truth and remains above embedded content. | `openExternal(url)`, `copyText(value)`, `showLocalQueue(meetingId)` | n/a: embedded | Show read-only cached title/status or sync-unavailable state; never invent transcript truth. | Rec server origin only; disable new-window navigation except allowlisted browser handoffs. |
| `cabinet.meeting.speakers` | `/meetings/:id/speakers` | `/desktop/meetings/:id/speakers` | `macos`, `windows`, `linux` | `server_product_ui` | yes | diarization status, speaker map, segment evidence, save/conflict state | Server owns speaker names, merge state, per-speaker lane segments, confidence, save conflicts, and retries; native hosts route only. | `openExternal(url)`, `copyText(value)` | n/a: embedded | Show offline speaker panel unavailable state with current saved speaker labels if cached; editing disabled offline. | Rec server origin only; bridge cannot access audio files or raw local paths. |
| `cabinet.upload.manual` | `/upload` | `/desktop/upload` | `macos`, `windows`, `linux` | `server_product_ui` | yes or explicit local upload staging policy | account quota/policy, upload endpoint readiness, local queue availability | Native shell may provide file picker bridge only after a user click; upload copy remains server-owned. | `pickMediaFile()`, `showLocalQueue(meetingId)`, `openExternal(url)` | n/a: embedded | Show local-staging unavailable/queued state; do not expose direct object-storage credentials. | Rec server origin only; file picker bridge user-initiated and typed. |
| `cabinet.processing.status` | `/meetings/:id/status` | `/desktop/processing/:id` | `macos`, `windows`, `linux` | `server_product_ui` | yes | upload accepted, server stored, audio extraction, transcription, notes, degraded/failure state | Uses shared product statuses; cannot claim local capture state or hide native queue truth. | `showLocalQueue(meetingId)`, `openExternal(url)` | n/a: embedded | Show last known server stage with stale marker; native local queue remains separately visible. | Rec server origin only; server CSP enforced; no polling outside configured API origin. |
| `cabinet.account.status` | `/settings/account` | `/desktop/account` | `macos`, `windows`, `linux` | `server_product_ui` | yes | session, workspace, plan/policy summary, device/session list | Shows product account/workspace summary; native shell stores no product secrets in UI docs and only displays minimal route-guard badge outside the web route. | `openExternal(url)`, `copyText(value)` | n/a: embedded | Show signed-out/sync-unavailable route with local recording policy preserved. | Rec server origin only; no credential display; no payment/admin routes embedded. |
| `cabinet.settings.basic` | `/settings` | `/desktop/settings/basic` | `macos`, `windows`, `linux` | `server_product_ui` | yes | session, language/theme preference, basic workspace policy | Basic language/theme/session controls only; advanced admin/billing/team routes hand off to browser. | `openExternal(url)` | n/a: embedded | Show cached preferences as read-only with retry. | Rec server origin only; navigation allowlist excludes admin/billing/team/help/legal by default. |
| `cabinet.deletion.entry` | `/meetings/:id/delete` | `/desktop/deletion/:id` | `macos`, `windows`, `linux` | `server_product_ui` | yes plus destructive confirmation | deletion eligibility, retention state, local buffer/package state, backup/egress truth | Server shows deletion truth; local buffer purge requires native confirmation and result callback. | `requestLocalPurge(meetingId)`, `openExternal(url)` | n/a: embedded | Show sync-unavailable deletion blocked state; local purge may be requested only with clear native confirmation. | Rec server origin only; destructive bridge call audited and deny-by-default. |

## Native Bridge Allowlist

Embedded web may request only these shell actions:

- `openExternal(url)` for approved browser handoffs;
- `pickMediaFile()` after a user click on an upload route;
- `showLocalQueue(meetingId)` for local queue/status surfaces;
- `requestLocalPurge(meetingId)` for deletion workflows, returning pending,
  confirmed, failed, or device-unreachable status;
- `openSystemSettings(permissionKind)` for permission recovery;
- `copyText(value)` for explicit user copy actions.

Embedded web must not call:

- `startRecording`;
- `stopRecording`;
- raw filesystem reads;
- raw audio device access;
- diagnostics export without native confirmation;
- arbitrary shell commands or unrestricted URL navigation.

## Route Guard Behavior

- Unknown embedded routes fail closed to a handoff page.
- Browser-only governance routes open the browser, not hidden desktop admin UI.
- Active recording keeps native stop above every embedded route.
- Embedded web cannot visually obscure or restyle the native capture strip.
- If the server is unavailable, the desktop shell keeps recording/local queue
  usable and shows a sync-unavailable embedded fallback.

## Speaker Assignment Contract

Speaker assignment in desktop is server-owned product UI:

- data source: backend diarization/speaker model;
- visible state: loading, ready, low confidence, saving, saved, conflict,
  failed, retrying;
- allowed edits: rename speaker, merge speaker, assign segment speaker;
- save result: backend response updates speaker labels across browser and
  embedded desktop;
- conflict behavior: show which segments changed and require user confirmation;
- native role: host route, preserve capture strip, and show offline fallback.

Native shells must not implement separate speaker editing state machines.

## Security And WebView Policy

- Embedded routes require authenticated session or local policy state.
- Use a restricted WebView origin allowlist for the configured Rec server.
- Disable arbitrary navigation inside embedded views.
- Apply CSP from the server; desktop shell should not inject product scripts.
- Bridge calls must be user-initiated, typed, audited, and deny-by-default.
- No MediaScribe, object storage, or backend credentials are stored in the
  desktop UI layer.
