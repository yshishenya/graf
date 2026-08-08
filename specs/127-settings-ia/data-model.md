# Data model: представление настроек

Эта feature не добавляет таблицы, миграции или новые persisted settings. Ниже
описаны только presentation entities и их источники истины.

## Settings category

| Field | Meaning | Source | Rule |
|---|---|---|---|
| `key` | Stable category key | route/template constant | One canonical page per supported category |
| `label` | Russian UI label | presentation map | Same label in global and inner navigation |
| `scope` | User-visible ownership | existing membership/session/platform state | Must be shown before mutation |
| `href` | Canonical category path | route map | Browser and desktop variants mirror semantics |
| `availability` | `available`, `owner_only`, `native_only`, `unavailable` | existing policy/context | Disabled state includes next step |

## Account settings surface

Read-only presentation projection of existing auth data:

- linked provider label and primary marker, without `provider_subject`;
- registered device id for form action only, platform label, client version,
  status, registration state, current-device marker and safe timestamps;
- provider-link start options from the existing workspace policy;
- result copy for provider-link confirmation and device revoke.

The projection is scoped to the current authenticated user and active workspace.
It is a device view, not a browser-session inventory. It must not contain
candidate email/phone, callback state, credential input, access tokens or raw
provider identifiers.

## Workspace settings surface

Existing `WorkspaceAccessView` and `WorkspaceJoinOfferView` remain the source of
truth:

- active workspace and verified accessible workspaces;
- translated role label;
- actionable join offers only;
- safe result copy after activate/accept/reject.

## Summary settings surface

Built-in definitions remain presentation data from `BUILT_IN_TEMPLATES`; personal
formats remain the existing API projection. The UI must keep these groups
separate and must not offer a personal format as workspace default when the API
rejects it.

## Calendar settings surface

`CalendarSettingsSurfaceView` remains authoritative for source state, selected
calendars, sync health, preferences, preview, conflicts and privacy boundary.
IA changes only the surrounding category entry and common settings navigation;
calendar credential storage and lifecycle semantics do not change.

## Recording handoff

Presentation-only entity containing:

- scope: `На этом Mac` / `Только в приложении`;
- native availability copy;
- visible capture and one-action Stop reminder;
- link or instruction to the existing native settings surface.

It does not persist or mutate capture policy from the web.
