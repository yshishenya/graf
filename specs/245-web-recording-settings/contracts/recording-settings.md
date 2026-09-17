# Web ↔ Mac contract
Handler: grafRecordingSettings (WKScriptMessageHandlerWithReply).
Request: {version:1, nonce:string, action:"read"|"set"|"setAll", targetID?:string,
rule?:"always"|"ask"|"never"}.
Exact keys/types required for each action. Unknown fields/actions/versions are rejected.
set requires a known verified targetID. setAll patches current verified targets only.
Reply: {version:1, targets:[{id,name,rule}], error?: user-facing safe message}.
Read/store failure rejects with a fixed user-facing message; no raw error/path leaks.
Mutation success replies only after atomic persistence and native notification.
Failed mutation returns confirmed current values with an error, or rejects when unreadable.

Main frame only; source URL AND current webView URL must be same-origin allowed
/desktop/settings/recording (no query). Native document nonce must match; inactive,
loading, detached views are rejected. Rotate/revoke on navigation/session boundary.
WebKit promise reply belongs to requesting context. Native notification requests refresh.
Web uses timeout for missing reply, disables pending controls, discards late responses,
announces error, and retains local fallback. No settings fetch/save to server.

Existing /desktop/settings/meeting-detection is a local-form fallback only.
