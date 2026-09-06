# F243 UI/native contract

## Confirmation

Only configured-origin main frame on allowed cabinet route may ask. No window,
duplicate pending request, foreign frame, navigation, process exit or dismantle
resolves false. Sheet has Cancel default, explicit continue and Escape dismissal.
Callback exactly once; no message content logs; server reauth/CSRF/tenant stay.

## Routes

Exact settings tails account/preferences, account/close, account/close/cancel.
Shared detail and shared audio download require UUID and exactly one valid
workspace_id query. Shared page full/summary/unavailable renders use existing
X-GRAF-Client presentation hint for embedded layout and return links; this hint
never authorizes access. Meetings
recovery links are surface-aware. Terms/privacy/offer open via safe external
handoff. Unknown siblings/children, bad UUID, foreign origin, schemes, userinfo
and sensitive queries remain blocked on new shared routes; legal handoff strips
all query/fragment values through existing sanitizer. Auth continuation remains
unchanged. No blanket prefix allowlisting.

Exact paths and classifications:
- `/shared-meetings/{UUID}?workspace_id={UUID}` → meetingDetail.
- `/api/v1/cabinet/shared-meetings/{UUID}/downloads/audio?workspace_id={UUID}` → artifactDownload.
Both keep existing native desktop header propagation and download response handling.
Shared detail accepts only its existing tab fragments `#outcomes` / `#recording`
in addition to no fragment, so native reload remains possible after switching tabs.
Shared audio download accepts no fragment; arbitrary fragments remain blocked.
Full/summary/unavailable server responses are tested with and without the hint;
summary-only cannot become full access by sending the header.

## Browser

Presence of data-account-preferences-auto-save enables existing validated form
submission, preserving other fields. Accepted-summary focus targets an existing
tabindex=-1 result after reload. Tooltips retain role/aria-describedby, pointer,
keyboard/Escape access without hidden overflow. Submenu falls inline if neither
side fits; recalculates on open/resize, with focus traversal intact.

Tooltips use native popover button behavior for no-JS click/Enter/Space/Escape
and light dismissal; hidden text remains aria-describedby. JS adds hover/focus
and bounded positioning, never reopens after Escape until a new entry/action.
Theme preview is not persistence confirmation; failures remain errors and reload
uses last server-saved preference. No immediate automatic preview rollback is
required. The locale preference does not control transcription or summary language.

## Presentation

OS light/dark × system/light/dark choice; text4.5:1, large text3:1, essential
borders/focus3:1.375/550/768/1200px, short height and200% zoom. Warning border
survives cascade. No deletion of production template, live selector arm, dynamic
state or privacy marker. Existing locale persists, unsupported translation is
stated honestly. Capture/deletion/auth contracts unchanged.
