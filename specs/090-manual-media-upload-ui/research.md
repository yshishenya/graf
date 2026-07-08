# Research: Manual Media Upload UI

## Decision: Keep Upload As A Meetings Workspace Sheet

**Decision**: The browser and embedded desktop entry points open a compact
upload sheet from the existing meetings workspace header and empty state. The
feature does not add `/upload` as a separate primary product destination.

**Rationale**: Feature `030` defines upload as contextual to the meetings list,
then represented as a normal meeting row/status. The existing desktop route
policy also blocks broad `upload` path segments as local file/diagnostic risk.
Staying inside `/meetings` and `/desktop/meetings` avoids route-policy churn and
preserves the meeting-first product model.

**Alternatives considered**:

- Dedicated upload page: rejected because it creates a separate product
  destination and conflicts with the V8 route matrix.
- Native macOS upload action: rejected for this slice because it would create a
  second upload owner and require a separate file picker/auth/custody review.

## Decision: Add A CSRF-Protected Cabinet Upload Wrapper

**Decision**: Add a cabinet-facing upload route that validates unsafe-action
CSRF proof for cookie/session uploads and reuses the `087` one-file upload
helper. Keep the public `/api/v1/media-uploads` contract available for
API/device callers without changing its auth semantics.

**Rationale**: Cookie-authenticated cabinet mutations must require CSRF proof.
Adding the existing CSRF dependency directly to the public `087` endpoint would
also affect Bearer/session API clients because the current principal model does
not distinguish auth transport. A cabinet route preserves public API
compatibility while giving the web UI the same unsafe-action protection as
deletion and other cabinet mutations.

**Alternatives considered**:

- Submit the UI directly to `/api/v1/media-uploads`: rejected because it lacks
  the cabinet CSRF boundary for cookie-authenticated browser actions.
- Add global CSRF to `/api/v1/media-uploads`: rejected because it could break
  non-browser clients and existing contract expectations.
- Store upload credentials in the desktop app: rejected by the constitution and
  product gates.

## Decision: Reuse Backend Custody Through A Small Helper

**Decision**: Extract the upload acceptance logic introduced by `087` into an
ingest helper used by both public and cabinet routes.

**Rationale**: Route-to-route calls couple auth and request parsing. A helper
keeps custody logic single-sourced without duplicating storage, manifest,
finalize, processing-dispatch, and response mapping behavior.

**Alternatives considered**:

- Duplicate the route body in `api/cabinet.py`: rejected because it risks
  divergence in validation, lifecycle accounting, and processing dispatch.
- Keep everything only in `api/ingest.py`: rejected because cabinet CSRF and UI
  routing are separate API boundary concerns.

## Decision: Use Browser Media Metadata Plus Manual Duration Fallback

**Decision**: On file selection, the cabinet JS attempts to read media duration
through a temporary audio/video metadata element. If duration is unavailable,
the upload sheet requires the user to enter a positive approximate duration in
seconds before transfer starts.

**Rationale**: The `087` backend contract requires `duration_seconds`.
Server-side probing/transcoding would add dependency, CPU, privacy, and failure
surface. Browser metadata is cheap when supported, while a manual fallback keeps
the requirement explicit and truthful.

**Alternatives considered**:

- Make duration optional in the backend: rejected because it broadens `087`
  ingest contract and limit semantics.
- Add server-side ffprobe/transcoding: rejected as a new dependency and out of
  scope.
- Guess duration from file size: rejected as inaccurate and misleading.

## Decision: Use Vanilla XMLHttpRequest For Transfer Progress

**Decision**: Implement upload transfer with a small vanilla JS controller
using `XMLHttpRequest` so progress, abort-before-acceptance, response parsing,
and CSRF headers are explicit.

**Rationale**: HTMX is already vendored and useful for fragments, but file
upload progress and abort control are clearer with direct XHR. The repository
has no frontend build pipeline and 058 explicitly avoids new frameworks.

**Alternatives considered**:

- HTMX-only multipart form: rejected because progress/abort and multipart CSRF
  form handling would be less explicit.
- `fetch` only: rejected because standardized upload progress is not broadly
  available.
- Add a SPA/component framework: rejected by 058 and Ponytail guidance.

## Decision: Embedded Desktop Uses Session-Capable Cabinet Path

**Decision**: Embedded upload is enabled when the cabinet has an owner session
and CSRF token. Header-only desktop cabinet states without an unsafe-action
session show sign-in or unavailable copy instead of attempting upload.

**Rationale**: WebKit request policy injects desktop headers for safe main-frame
GET navigations only. It deliberately does not add desktop headers to POST or
subresource requests. Relying on hidden legacy headers for upload would fail in
embedded WebView and could encourage unsafe auth workarounds.

**Alternatives considered**:

- Extend WebKit to inject headers into POST/subresource uploads: rejected
  because it affects a broad trust boundary and needs a separate slice.
- Create a native desktop upload bridge: rejected because the feature is
  server-owned cabinet UI, not a native file-picker/custody feature.
- Allow `/desktop/upload` as a main route: rejected because current route policy
  treats upload segments as local-file/diagnostic risk and the product design
  keeps upload contextual.

## Decision: Refresh Existing List/Detail After Acceptance

**Decision**: After the user presses `Загрузить`, close the sheet, show an
upload activity row above the existing meeting list, provide progress and
hover/focus controls there, and refresh the existing meeting list region after
server acceptance.

**Rationale**: Upload is part of the meetings workspace, not a modal task the
user must babysit. The modal owns only file choice and metadata validation.
The workspace row keeps progress visible while the user continues scanning the
list, and the existing cabinet list rendering still owns accepted meeting
provenance, processing states, and polling rules after acceptance.

**Alternatives considered**:

- Keep progress and accepted state inside the modal: rejected after stakeholder
  review because it blocks the list context and makes upload controls feel
  detached from the record that will appear in the workspace.
- Navigate immediately to detail every time: rejected because the user may want
  to stay in list context, especially in embedded desktop.
- Add a separate upload dashboard: rejected because this slice is
  meeting-first and does not approve upload queue management as a separate
  product destination.

## Decision: Same-Tab Continue Uses Retained File Resubmission

**Decision**: `Продолжить` is available after a user stop/interruption while
the same page still retains the selected File object. It restarts the retained
file submission through the existing single multipart cabinet route and reuses
the same local upload identity.

**Rationale**: The approved cabinet route is `POST
/api/v1/cabinet/media-uploads` with one multipart file. It does not expose
chunk ranges, accepted byte ranges, or browser-resumable session state. A
truthful same-tab continue gives the user the requested recovery control
without changing backend custody contracts or pretending byte-level resume
exists.

**Alternatives considered**:

- Implement byte-range resumable browser upload now: rejected because it needs a
  separate API/backend slice, OpenAPI contract changes, storage range
  semantics, retry limits, and new validation evidence.
- Hide continue until true byte resume exists: rejected because the user needs a
  visible recovery control after stopping an in-progress upload.

## Decision: Error Copy Is Code-Mapped And Metadata-Only

**Decision**: Map known problem codes to bounded Russian copy and avoid
rendering raw server details unless they have been explicitly reviewed as safe.

**Rationale**: Upload failures can involve storage, limits, dependency state,
auth, and private file names. Safe copy must explain action without leaking
object keys, private paths, dependency IDs, or content.

**Alternatives considered**:

- Display server `detail` verbatim: rejected because future details may contain
  implementation values.
- Use only a generic error: rejected because users need distinct recovery
  actions for auth, file, duration, network, and processing readiness failures.
