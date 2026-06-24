# Data Model: Cabinet Runtime Truth

## Cabinet Configuration

Represents static desktop knowledge of where the cabinet should load.

Fields:

- `baseURL`: normalized HTTP(S) origin for the cabinet.
- `headers`: desktop metadata headers already used by embedded cabinet requests.
- `source`: packaged default, environment, or persisted source.

Rules:

- Configuration may select cabinet mode and route construction.
- Configuration alone does not prove reachability, authentication, processing
  readiness, transcript availability, or server health.

## Cabinet Runtime State

Represents current user-safe truth learned from embedded navigation.

States:

- `notConfigured`: no cabinet route is configured.
- `loading`: cabinet request is in progress or being checked.
- `ready`: an allowed authenticated meeting list/detail route finished.
- `offline`: network/server failure.
- `timeout`: navigation timed out.
- `expiredSession`: login or sign-up route loaded, or server returned auth
  required.
- `accessDenied`: server denied the current session.
- `notFound`: the requested review route cannot be confirmed.
- `malformedResponse`: unexpected non-HTTP or unclassified response.
- `blockedRoute`: route is outside the embedded cabinet boundary.

Rules:

- Only `ready` may use success tone.
- `loading` is neutral.
- `offline` and `timeout` are unavailable server states.
- Auth routes are not ready even if HTTP navigation succeeds.

## Native Shell Status Presentation

Represents user-facing shell copy, icon, and tone derived from configuration
and runtime state.

Fields:

- `sidebarSubtitle`: short sidebar context.
- `menuStatusText`: profile/menu status line.
- `tileTitle`: cabinet status tile title.
- `tileDetail`: cabinet status tile detail.
- `systemImage`: safe system icon name.
- `tone`: success, neutral, warning, or error.

Rules:

- Success tone requires `Cabinet Runtime State = ready`.
- Server-unavailable states must not be translated into ordinary logged-out
  copy.
- Local recording controls remain independent of this presentation model.

## Review Surface Parity Case

Represents a metadata-safe web/embedded cabinet validation scenario.

Fields:

- `surface`: web or desktop-embedded route.
- `state`: ready, processing, failed, unavailable, deleted, auth-required, or
  policy-blocked.
- `transcriptAvailable`: boolean.
- `diarizationAvailable`: boolean.
- `playbackAvailable`: boolean.
- `visibleUnavailableReason`: safe string category.
- `horizontalOverflow`: count or boolean from runtime check.

Rules:

- Web and embedded surfaces must agree for the same meeting/viewer state.
- Evidence must not include transcript text, raw audio, credentials, signed
  URLs, private local paths, or private meeting content.
