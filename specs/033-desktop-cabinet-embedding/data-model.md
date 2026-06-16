# Data Model: Desktop Cabinet Embedding

## DesktopCabinetConfiguration

Represents the desktop app's configured route into the server-owned cabinet.

Fields:

- `baseURL`: HTTP(S) server origin for the Rec cabinet.
- `workspaceId`: Optional active workspace identifier used only when provided
  by existing auth/config context.
- `headers`: Metadata-only request headers allowed for development and
  existing auth handoff. Must not be logged with secret values.
- `loadTimeoutSeconds`: Maximum initial load time before bounded unavailable
  state.
- `source`: Configuration source such as environment, UserDefaults, or
  unavailable.

Validation rules:

- `baseURL` must use `http` or `https`.
- No hard-coded bearer token, session token, password, signed URL, private
  account identifier, or live filesystem path may appear in defaults.
- Missing configuration maps to `notConfigured`, not to a crash.

## DesktopCabinetRoute

Represents a candidate embedded route.

Fields:

- `path`: Normalized path.
- `meetingId`: Optional meeting identifier for detail route.
- `query`: Optional safe query items for server-owned review context.
- `kind`: `meetingList`, `meetingDetail`, `unsupported`, `external`, or
  `forbiddenAction`.

Validation rules:

- Allowed list route: `/desktop/meetings`.
- Allowed detail route: `/desktop/meetings/{meeting_id}` where the identifier
  is non-empty and path-safe.
- Unsupported governance routes such as share/export/download/delete are not
  allowed in this slice.
- Capture, device, permission, local file, local purge, diagnostics, driver, or
  system-audio routes are forbidden inside the embedded surface.

## DesktopCabinetRouteDecision

Represents how the native shell handles a candidate route.

Fields:

- `route`: The normalized route.
- `decision`: `allow`, `blockWithMessage`, or `openExternally`.
- `reason`: Stable metadata-safe reason.
- `userMessage`: Short user-facing message for bounded states.

Validation rules:

- Meeting list and detail routes may be allowed.
- Unsupported future product routes are blocked with a planned/policy message.
- External help/legal/account routes may open in the system browser only when
  explicitly classified as external-safe.
- Forbidden capture/local routes are blocked and must not execute.

## DesktopCabinetState

Represents the embedded area's current load/result state.

States:

- `notConfigured`
- `loading`
- `ready`
- `offline`
- `timeout`
- `expiredSession`
- `accessDenied`
- `notFound`
- `malformedResponse`
- `blockedRoute`

Validation rules:

- Every non-ready state has a bounded recovery message.
- Non-ready states do not alter active recording, stop availability, local
  upload queue truth, or local diagnostics.
- Access-denied and not-found states do not confirm foreign meeting content.

## UploadReviewLink

Represents a review destination derived from a local upload queue item.

Fields:

- `itemId`: Local upload queue item identifier.
- `meetingId`: Optional server meeting identifier.
- `state`: Local upload item state at the time the link is evaluated.
- `destination`: Optional `DesktopCabinetRoute`.
- `availability`: `available`, `processingOnly`, or `unavailable`.
- `reason`: Metadata-safe reason for unavailable links.

Validation rules:

- A review link is available only when `meetingId` is present and the local item
  has server truth compatible with review.
- Queued/uploading/failed/blocked/local-only items keep local status and do not
  imply a server review exists.
- The link must never include live local paths or signed storage URLs.

## NativeShellInvariant

Represents required native state outside the embedded surface.

Fields:

- `recordVisible`: Whether the native Record affordance is visible when idle.
- `stopVisible`: Whether native Stop is visible during active recording.
- `uploadTruthVisible`: Whether native upload state remains visible.
- `focusCanReachStop`: Whether keyboard focus can reach Stop from embedded
  context.
- `embeddedSurfaceLoaded`: Whether the web-owned surface is ready.

Validation rules:

- During active recording, `stopVisible` and `focusCanReachStop` must be true
  for every embedded route and error state.
- Embedded readiness must not be a prerequisite for local recording controls.
