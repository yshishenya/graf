# Feature Specification: Local Upload Custody

**Feature Branch**: `codex/057-local-upload-custody`

**Created**: 2026-06-26

**Status**: Implemented, merged, and released as the product-owned custody layer

**Input**: User description: "Work through local file queue behavior as a
product problem. Local recordings must be sent to the server automatically. The
user has no useful action for most upload failures, so the app must not show a
task-like queue or ask the user to fix transport. Think through every detail,
every role, and unacceptable outcomes. For the user, irreversible loss of a
recording is unacceptable."

## Product Thesis

Local upload is not a user task. It is a product custody obligation.

When a recording is created locally, `2brain Rec` owns a promise to keep it
safe, send it to the server when allowed, show truthful status, and account for
the final lifecycle outcome. The user must never be asked to manage retries,
inspect transport states, or decide what to do with technical conflicts they
cannot resolve.

The server-owned meeting list remains the source of truth for meetings known to
the workspace. The native desktop shell remains the source of truth for local
capture, local storage safety, offline pending recordings, and custody of local
artifacts before the server can represent them.

This feature refines the existing feature `042` desktop upload queue and
reconciliation contract. It must not replace durable queue, local media
revision, range reconciliation, or diagnostic-redaction guarantees with a
copy-only UX change.

## Clarifications

### Session 2026-06-26

- Q: Does feature 057 implement server cabinet presentation or share `web.py`
  work with feature 058? -> A: No. 057 owns native custody plus stable
  API/read-model contracts; 058 owns cabinet presentation.
- Q: Should normal users manage failed local uploads with retry or manual review
  controls? -> A: No. The product retries automatically and exposes only real
  user, admin, support, or lifecycle actions.
- Q: What happens when server reconciliation returns that a local recording is
  not found? -> A: Treat it as server-unknown local custody, preserve the local
  copy, reconcile or register safely, and never fabricate a server row.
- Q: When may local purge be acknowledged? -> A: Only after verified deletion,
  tombstone, cryptographic unrecoverability, or explicit terminalization with
  metadata-only evidence.
- Q: What bridges this feature to the server web refactor? -> A: Planning must
  produce a 057-to-058 stable API/read-model handoff contract before
  implementation tasks begin.

## Role Perspectives And Non-Negotiables

### Meeting Owner

The meeting owner wants the recording to appear in the meeting list and become
reviewable without manual upload work.

Willing to do:

- start, pause, resume, and stop recording;
- sign in again when the session expires;
- choose the correct workspace/account when required;
- grant required local permissions;
- explicitly delete a local copy when the product makes the consequence clear.

Not willing or expected to do:

- inspect upload sessions, retry modes, checksums, offsets, status codes, or
  queue files;
- press "Retry" repeatedly to fix server, auth, network, or policy failures;
- decide whether server truth or local truth is authoritative;
- copy raw local files into another tool to rescue normal product behavior;
- lose a recording without warning, explanation, and lifecycle accounting.

Unacceptable outcomes:

- a valid recording is lost irreversibly without prior warning or audit trail;
- the UI says "needs review" but offers no action the user understands;
- the UI makes upload failure look like the user's fault;
- a server list and a local list show competing versions of the same meeting;
- the app claims a recording is ready when upload or processing is incomplete.

### Workspace Owner / Admin

The workspace owner wants recordings to follow workspace policy, retention,
storage quotas, access rules, and deletion truth.

Willing to do:

- fix workspace policy, quota, auth/provider configuration, server availability,
  or device enrollment;
- review metadata-safe incidents and diagnostics;
- decide retention and purge policy;
- contact support with a safe report.

Not willing or expected to accept:

- hidden desktop audio retention outside policy;
- local recordings that bypass server access/deletion accounting;
- private paths, raw audio, transcript text, signed URLs, or secrets in support
  evidence;
- duplicate meeting records created by retry or reconnect.

### Desktop App

The desktop app is responsible for local custody.

It must:

- keep local artifacts while custody is active and policy allows retention;
- retry automatically when the blocking condition may clear;
- register a server meeting as early as allowed so the server list can show the
  meeting;
- reconcile against server truth before upload, retry, finalize, or claim
  success;
- show only user-meaningful actions in normal UI;
- create metadata-safe incident evidence for operator/support flows;
- fail closed when privacy, access, deletion, or corruption blocks safe upload.

It must not:

- silently drop audio;
- ask the user to manage the transport queue;
- expose local paths or file names as product status;
- retry against deleted, revoked, or policy-blocked server state;
- convert a technical `manualOnly` state into a user-facing task.

### Server / Workspace Cabinet

The server is responsible for known meeting truth.

It must:

- own the meeting list and meeting detail state for server-known recordings;
- expose early server-registered recordings through stable list/detail read-model
  fields with truthful upload/processing status;
- keep upload truth separate from transcription truth;
- expose admin/support status for custody incidents without exposing content;
- preserve access, deletion, retention, and tenant boundaries.

It must not:

- show local-only recordings it does not know about as if they are server
  meetings;
- hide upload or processing blockers behind a generic "failed" state;
- accept duplicate meetings for the same local recording identity.

### Operator / Support Reviewer

The support reviewer wants enough metadata to understand what happened without
accessing meeting content.

Willing to do:

- inspect safe reason codes, timestamps, device/workspace ids, and lifecycle
  state;
- guide admin/user through auth, workspace selection, permission, policy, or
  quota remediation;
- escalate product bugs with safe incident reports.

Not allowed to do by default:

- read raw audio or transcript content from diagnostics;
- receive secret tokens, signed URLs, cookies, or private local paths;
- ask a normal user to perform engineering recovery steps.

## Authority Model

- The server-owned meeting list answers: "Which meetings does this workspace
  know about?"
- The native shell answers: "Is this Mac currently holding recordings that need
  delivery or lifecycle action?"
- A recording appears in the server-owned list as soon as the server can safely
  register it.
- A server review/detail route may be opened only for a server-known recording
  identity. Local-only custody status must never fabricate a review route.
- A recording that the server cannot know yet must not be inserted into the
  server list through a native overlay, DOM injection, or second local list.
- The native shell may show aggregate custody status and a disclosure for safe
  local details, but it must not present a task queue as the primary workspace.
- When the cabinet is configured, the native shell must not render local custody
  rows above or inside the "My Meetings" WebView content. The default native
  surface is a compact summary or shell indicator; details live in a secondary
  disclosure outside the server-owned list.

## Server Web Refactor Boundary

This feature is designed to run safely alongside feature `058`, the full server
web-interface refactor.

- This feature MUST NOT require edits to
  `apps/server/src/twobrain_rec_server/cabinet/web.py`, server cabinet templates,
  server cabinet CSS, or meeting-list/detail HTML markup.
- Server meeting list/detail presentation changes, status chips, visual layout,
  and copy changes belong to feature `058`, not to this local custody feature.
- This feature MAY add or consume stable desktop API/read-model contract fields
  for registration, sync-state, owner/action mapping, or review URL availability
  when those fields are missing; such work should live in API/ingest/read-model
  layers, not in server web presentation files.
- Acceptable server write scope for this feature is limited to stable contracts
  such as `api/ingest.py`, `api/cabinet.py` desktop purge endpoints,
  `api/schemas.py`, `domain/statuses.py`, `ingest/desktop_sync.py`,
  `ingest/meetings.py`, and narrowly `cabinet/queries.py` or
  `cabinet/view_models.py` when a structured read-model field is required for
  later `058` rendering. HTML, CSS, templates, page scripts, and status-chip
  rendering remain out of scope.
- If feature `058` is active at the same time, validation for this feature should
  prove: native custody does not inject rows into WebView, desktop
  upload/reconciliation works through stable APIs, and server routes remain
  reachable. Pixel/layout parity for the server cabinet is validated by `058`,
  not here.
- If a desired server-visible status requires new cabinet UI, this feature should
  record it as an integration dependency and avoid implementing it in `web.py`.
- Planning for this feature MUST create a 057-to-058 handoff contract that names
  the stable read-model/API fields, enum values, copy-key expectations, and
  fallback behavior that feature `058` can render without touching native
  custody logic.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Valid Local Recording Is Never Lost Silently (Priority: P1)

As a meeting owner, I want every valid stopped recording to be kept safely until
it is either delivered to the server or reaches a truthful policy-governed
lifecycle outcome, so I do not lose a meeting because upload failed.

**Why this priority**: This is the core promise. If a valid recording can vanish
without warning and evidence, the product is not trustworthy.

**Independent Test**: Complete valid recordings under online, offline, app
restart, and server outage conditions. Confirm the recording remains accounted
for, visible through user-safe custody status, and either appears in stable
server read-model truth or reaches an explicit retained/purged lifecycle
outcome.

**Acceptance Scenarios**:

1. **Given** a valid recording is stopped while the server is reachable and the
   user is authenticated, **When** upload starts, **Then** the recording is
   registered with the server and stable meeting/list read-model fields expose
   truthful upload or processing status before transcription is ready; any
   cabinet rendering of that state belongs to feature `058`.
2. **Given** a valid recording has just been stopped, **When** local packaging
   completes before server registration is visible, **Then** the desktop confirms
   within the normal shell that the recording is saved on this Mac.
3. **Given** a valid recording is stopped while the server is unreachable,
   **When** the app remains offline or restarts, **Then** the native shell shows
   that local recordings are safely held and will be sent automatically without
   showing a retry task.
4. **Given** the user quits, sleeps the Mac, relaunches the app, or opens it the
   next day, **When** undelivered custody items still exist, **Then** the desktop
   resumes custody processing and shows the same truthful owner/action state.
5. **Given** local disk pressure reaches warning, critical, or reserve
   thresholds while recordings remain undelivered, **When** the user opens the
   app, **Then** the shell warns that local safety is at risk and offers only
   meaningful storage, sign-in, report, or deletion actions.
6. **Given** a valid local recording remains undelivered near the retention
   deadline, **When** the user opens the app, **Then** the app warns before the
   policy deadline and explains what condition must change without asking the
   user to manage upload mechanics.
7. **Given** policy eventually requires local purge before delivery succeeds,
   **When** the purge happens, **Then** the product records metadata-only
   lifecycle evidence and no longer implies that review content will appear.

---

### User Story 2 - Server Meeting List Stays Authoritative (Priority: P1)

As a meeting owner, I want "My Meetings" to be one coherent server-owned list,
so I do not see duplicate or competing local/server versions of the same
recording.

**Why this priority**: A hybrid WebView/native UI can easily create double truth.
The product must preserve a clear authority boundary.

**Independent Test**: Create recordings in online, offline, expired-auth, and
server-conflict states. Confirm server-known recordings are represented only by
server API/read-model truth, while server-unknown recordings appear only as
native custody status, not as a second meeting list.

**Acceptance Scenarios**:

1. **Given** the server has accepted or registered the recording identity,
   **When** the meeting list is open, **Then** the server read-model exposes the
   recording and status for the server-owned list, and the native shell does not
   duplicate it.
2. **Given** the server does not yet know about the recording, **When** the
   meeting list is open, **Then** no fake meeting row is injected into the
   server list and the native shell shows only aggregate custody truth.
3. **Given** the user navigates from list to detail while upload continues,
   **When** background status changes, **Then** the app does not disrupt the
   current review route with a forced list refresh.
4. **Given** the server registered a meeting but the desktop quit before upload
   session, partial ranges, or finalize state was persisted, **When** the app
   relaunches, **Then** desktop reconciliation restores the server-known identity
   instead of creating a local-only duplicate.

---

### User Story 3 - User Sees Only Real Actions (Priority: P1)

As a meeting owner, I want the UI to ask me only for actions I can actually
perform, so I am not made responsible for server or transport failures.

**Why this priority**: "Retry", "manual review", and "needs verification" are
misleading when the user cannot fix the condition.

**Independent Test**: Simulate network outage, expired auth, wrong workspace,
missing permissions, server quota/policy block, server deletion, local file
corruption, and processing failure. Confirm the UI offers only meaningful user,
admin, or support actions for each state.

**Acceptance Scenarios**:

1. **Given** upload is blocked by missing network or temporary server
   dependency, **When** the user opens the native shell, **Then** the UI says the
   app will retry automatically and shows no "Retry" button.
2. **Given** upload is blocked by expired authentication, **When** the user opens
   the native shell, **Then** the UI offers "Войти" as the primary action.
3. **Given** upload is blocked by workspace policy, access, quota, deleted
   server state, or stale device identity, **When** the user opens the native
   shell, **Then** the UI explains that the workspace/admin must resolve it and
   offers a safe report action, not a transport retry.
4. **Given** upload is blocked by local artifact corruption or missing required
   content, **When** the user opens details, **Then** the UI says the recording
   cannot be sent and routes the user to diagnostics or deletion, not to a
   fake retry loop.
5. **Given** the user explicitly deletes an undelivered local copy, **When** the
   confirmation is shown, **Then** the copy states that this recording will not
   appear in `2brain Rec` unless a server copy already exists.

---

### User Story 4 - Custody Status Is Calm, Compact, And Honest (Priority: P2)

As a meeting owner, I want local custody status to be visible but not dominate
the workspace, so I can keep using the meeting list while the app works in the
background.

**Why this priority**: The current large local block visually turns background
sync into a user workload.

**Independent Test**: Open the desktop app with zero, one, and many local
custody items across idle, uploading, offline, auth-required, admin-blocked,
and terminal states. Confirm the main workspace remains the meeting list and
native custody UI stays compact, readable, and non-alarming unless a real user
action exists.

**Acceptance Scenarios**:

1. **Given** all recordings are delivered and processed or no local custody
   items exist, **When** the user opens the app, **Then** no local queue card is
   shown in the main meeting workspace.
2. **Given** recordings are uploading automatically, **When** the right panel is
   visible, **Then** it shows a compact synchronization status such as
   "2 из 5 отправляются. Остальные сохранены на этом Mac." with progress, not a
   list of technical queue items.
3. **Given** recordings are waiting for network or server recovery, **When** the
   right panel is visible, **Then** it says "Записи сохранены на этом Mac.
   Отправим автоматически, когда сервер будет доступен."
4. **Given** the user expands details, **When** local items are listed, **Then**
   rows are framed as storage/custody facts, not as tasks.
5. **Given** several custody states exist at once, **When** the summary is
   compact, **Then** it shows the highest-risk user-relevant state by priority
   while still preserving an aggregate count.

---

### User Story 5 - Admin And Support Can See Safe Incident Truth (Priority: P2)

As a workspace owner or support reviewer, I want metadata-safe incident details
for undelivered recordings, so I can resolve conditions that the meeting owner
cannot fix.

**Why this priority**: Hiding all failures protects the user from burden, but
operators still need accountable evidence.

**Independent Test**: Force each non-user-resolvable blocker and confirm a
metadata-only incident exists with reason category, responsibility, timestamps,
affected recording identity, and lifecycle state, without raw audio, transcript
text, local paths, tokens, or signed URLs.

**Acceptance Scenarios**:

1. **Given** a recording cannot be delivered because of workspace policy, quota,
   server dependency, or access state, **When** diagnostics are opened, **Then**
   the report identifies the owner of the next action as admin/support.
2. **Given** an undelivered recording reaches a terminal lifecycle outcome,
   **When** the admin/reviewer inspects the report, **Then** they can see
   whether local media was retained, purged, or still awaiting a policy action.
3. **Given** support evidence is copied or exported, **When** it is scanned,
   **Then** it contains only metadata-safe fields.

---

### User Story 6 - Upload, Processing, And Deletion Truth Stay Separate (Priority: P2)

As a workspace owner, I want upload success, transcription success, local
custody, deletion, and purge states to remain separate, so the product never
overstates what happened.

**Why this priority**: Upload can succeed while transcription fails; server
deletion can exist while local media still needs purge; local custody can exist
before server truth exists.

**Independent Test**: Simulate successful upload with failed processing,
server deletion while local buffers remain, local purge while server records
remain, and processing-ready states. Confirm each surface labels the state
without collapsing it into a generic success/failure.

**Acceptance Scenarios**:

1. **Given** upload succeeds but transcription is delayed, **When** server
   meeting/list read-model fields are queried, **Then** they expose processing
   truth rather than ready transcript truth; visual cabinet rendering belongs to
   feature `058`.
2. **Given** a server meeting is deleted while local artifacts remain, **When**
   the desktop reconciles, **Then** upload does not restart against policy and
   local purge/deletion truth is shown separately.
3. **Given** local custody is active before server registration, **When** the
   user opens the app, **Then** the product does not claim server review exists.

### Edge Cases

- No network before, during, or after recording.
- Server reachable but authentication expired.
- User is signed into the wrong workspace or no workspace can be resolved.
- Server accepts meeting registration but upload parts fail afterward.
- Server accepts some ranges and then the app quits, sleeps, or is force-quit.
- Server upload session expires after partial acceptance.
- Server reports terminal session or already accepted ranges for a recording.
- Server meeting was deleted or access was revoked while local artifacts remain.
- Workspace quota, retention, or policy blocks upload.
- Device identity is stale, revoked, or belongs to another workspace.
- Local files are missing, unreadable, checksum-changed, malformed, or too short
  to produce useful transcript content.
- Local disk is near warning, critical, or reserve thresholds.
- Local retention deadline approaches while auth/server/policy remains blocked.
- Multiple local recordings wait for delivery at once.
- The user opens a server meeting detail while background custody status
  changes.
- The user disables network, logs out, quits, relaunches, and logs back in.
- Diagnostics or support reports are copied after failure.
- Deletion or purge policy applies while upload is incomplete.
- Processing fails after upload was finalized.
- The local custody ledger is malformed, partially written, or schema
  incompatible after a crash or app update.
- The server returns 401, 403, 409, 410, 413, 429, or 503 during registration,
  session creation, part upload, finalize, or reconciliation.
- The app is foreground, backgrounded, minimized, hidden, or the WebView is not
  currently open when a retry becomes due.
- The user signs in through the WebView after auth expiry and expects uploads to
  resume automatically.
- A server local-purge task is received while local files are missing,
  undeleted, already deleted, or cannot be verified.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The product MUST treat each stopped, valid local recording as a
  custody item until it is delivered to the server or reaches an explicit
  lifecycle terminal state.
- **FR-002**: The product MUST NOT silently delete or lose a valid local
  recording while custody is active and policy still allows retention.
- **FR-003**: The product MUST warn before policy-driven local purge when a
  retained recording has not been delivered, unless the user explicitly chose
  deletion.
- **FR-004**: The product MUST preserve metadata-only evidence for every
  terminal undelivered outcome.
- **FR-005**: The product MUST register or reuse a server meeting as early as
  authentication, workspace policy, and server availability allow.
- **FR-006**: Server-known recordings MUST be queryable through stable server
  API/read-model fields with truthful upload or processing status. This feature
  MUST NOT require new cabinet rendering, status chips, layout, or copy for
  those fields; any cabinet presentation belongs to feature `058`.
- **FR-007**: Server-unknown local recordings MUST NOT be injected into,
  overlaid onto, or visually merged with the server-owned meeting list.
- **FR-008**: The native shell MAY show aggregate custody status for
  server-unknown recordings and MAY expose a secondary details disclosure.
- **FR-009**: The native shell MUST NOT present a local upload queue as the
  primary meeting list when the cabinet is configured.
- **FR-010**: The normal user UI MUST NOT show transport-only actions such as
  "Retry", "Stop retry", "manual retry", or "manual verification" unless the
  action changes a condition the user actually controls.
- **FR-011**: The product MUST map every blocker to an owner:
  `product_automatic`, `meeting_owner`, `workspace_admin`, `support`, or
  `policy_lifecycle`.
- **FR-012**: Meeting-owner actions MUST be limited to sign in, choose workspace,
  grant local permission, open known review, open diagnostics, copy a safe
  report, or explicitly delete a local copy.
- **FR-013**: Network, temporary server dependency, expired upload session, and
  unknown transient failures MUST remain automatic retry states while policy
  allows retention.
- **FR-014**: Expired authentication MUST preserve local custody and request
  re-authentication without creating a new meeting or upload session until auth
  is valid.
- **FR-015**: Access revoked, deleted server meeting, stale device identity, and
  policy-blocked states MUST NOT auto-upload against policy.
- **FR-016**: Local corruption, missing files, missing required audio, or
  checksum drift MUST enter a truthful cannot-send state with diagnostics or
  deletion as the only normal user actions.
- **FR-017**: Quality degradations that do not block structural upload MUST NOT
  be presented as custody blockers.
- **FR-018**: Upload status MUST remain separate from transcription, playback,
  notes, access, deletion, local purge, and diagnostics status.
- **FR-019**: Processing failure after upload success MUST be shown as a server
  processing/review state, not as a local upload queue failure.
- **FR-020**: Local custody UI MUST use calm, non-alarming copy for automatic
  states and reserve warning styling for imminent loss, required sign-in, or
  policy/admin action.
- **FR-021**: If multiple local recordings are held, the default UI MUST show an
  aggregate count and highest-priority user-relevant state, not a full task
  list.
- **FR-022**: Expanded local details MUST describe recordings by safe date/time,
  duration, and status; they MUST NOT expose private local paths or technical
  ids as primary labels.
- **FR-023**: The product MUST offer metadata-safe incident reporting for
  non-user-resolvable blockers.
- **FR-024**: Support/admin reports MUST include reason category, responsible
  role, timestamps, lifecycle state, and safe recording identity, while
  excluding raw audio, transcript text, local absolute paths, credentials,
  tokens, cookies, signed URLs, and secret values.
- **FR-025**: The product MUST not create duplicate server meetings,
  duplicate upload sessions, or duplicate processing jobs for the same local
  recording as a result of retry, relaunch, reconnect, or re-authentication.
- **FR-026**: The product MUST reconcile against server truth before claiming
  delivery, opening review from a local item, or deciding that delivery cannot
  continue.
- **FR-027**: The product MUST distinguish "server does not know this recording
  yet" from "server knows this recording but upload is incomplete".
- **FR-028**: The product MUST distinguish "cannot send because product/admin
  action is needed" from "cannot send because the recording is not valid
  content".
- **FR-029**: The product MUST retain a clear audit trail when retention or
  deletion policy terminalizes an undelivered recording.
- **FR-030**: The feature MUST preserve the existing native authority for
  active capture, Stop availability, local storage safety, local artifact truth,
  offline pending recordings, and diagnostics.
- **FR-031**: The feature MUST preserve the existing server authority for
  meeting list, review, transcript, access, retention, deletion, audit, and
  admin policy views.
- **FR-032**: User-facing copy MUST be Russian-ready, understandable to a
  non-technical user, and must not blame the user for transport or server
  failures.
- **FR-033**: The feature MUST not introduce transcript editing, trimming,
  speaker editing, public links, direct object storage upload, direct
  MediaScribe upload, or new automatic recording behavior.
- **FR-034**: The desktop MUST use `desktop-upload-queue.v2` or a
  forward-compatible successor as the durable local custody ledger.
- **FR-035**: A custody item MUST NOT be considered safely accepted locally until
  manifest identity, artifact fingerprints, local media revision id, retention
  deadline, and custody state are durably persisted together.
- **FR-036**: Malformed, partially written, or schema-incompatible custody state
  MUST be quarantined metadata-safely and surfaced as blocked custody truth; it
  MUST NOT be dropped, overwritten, or treated as all-synced.
- **FR-037**: The desktop MUST persist server meeting id immediately after
  successful registration, upload session id immediately after session creation,
  and accepted range/reconciliation truth after partial progress.
- **FR-038**: Before every upload attempt, finalize, review-open, terminal
  decision, or purge acknowledgement, the desktop MUST reconcile with server
  truth when a server identity exists.
- **FR-039**: The background custody runner MUST run on app launch, app
  activation, auth/session change, network reachability recovery, wake from
  sleep, and scheduled retry time; it MUST NOT depend on the meeting WebView
  being open.
- **FR-040**: Sign-in through the WebView MUST unblock desktop upload custody
  automatically once the session is valid, without requiring a manual retry.
- **FR-041**: Workspace quota, policy, legal-hold, access, and device-revocation
  blockers MUST be admin/support/policy states unless the server explicitly marks
  them as transient retryable dependency states.
- **FR-042**: Local purge acknowledgement MUST be sent only after local artifacts
  are actually removed, tombstoned, or cryptographically rendered unrecoverable;
  failed or unverified purge MUST report a metadata-safe failure state.
- **FR-043**: Local custody artifacts MUST be encrypted at rest according to the
  product baseline; queue, logs, diagnostics, and support reports MUST not expose
  decrypted content, bearer tokens, cookies, signed URLs, raw audio, transcript
  text, or private local paths.
- **FR-044**: Retry, relaunch, reconnect, and re-authentication MUST preserve the
  immutable local recording identity and local media revision fingerprint unless
  explicit future revision flows supersede this feature.
- **FR-045**: The feature MUST keep existing route policy boundaries: local-only
  custody cannot create, spoof, or navigate to a server review/detail route.
- **FR-046**: This feature MUST NOT edit server cabinet presentation files
  (`apps/server/src/twobrain_rec_server/cabinet/web.py`, templates, CSS, or
  meeting-list/detail markup). If cabinet UI changes are desired, they MUST be
  planned in feature `058` or a separate explicitly scoped server-web feature.
- **FR-047**: Any required server-facing custody fields MUST be exposed through
  stable API/read-model contracts so the server web refactor can render them
  independently.
- **FR-048**: Planning and tasks for this feature MUST keep 057 and 058 on
  disjoint write scopes: 057 owns native custody and stable API/read-model
  contracts; 058 owns server cabinet presentation refactoring.
- **FR-048a**: Planning and tasks for 057 MUST reject any task whose write path is
  `apps/server/src/twobrain_rec_server/cabinet/web.py`, a server cabinet
  template, a server cabinet CSS/static file, or meeting-list/detail HTML markup.
  Server-side 057 tasks are limited to API, ingest, reconciliation, persistence,
  purge contracts, and read-model contract fields needed by desktop custody.
- **FR-049**: Desktop sync-state `404` / `recording_not_found` MUST be treated as
  server-unknown local custody truth, not as terminal loss and not as permission
  to fabricate a server meeting row.
- **FR-050**: Server-facing sync/conflict contracts MUST expose stable
  machine-readable owner/action fields, including responsible role, retry class,
  and normal user action kind, so desktop and feature `058` can render consistent
  status without parsing copy.
- **FR-051**: Server problem responses for registration, upload session, part
  upload, finalize, reconcile, and purge endpoints MUST use stable problem codes
  for auth, quota, policy, deletion, stale device, conflict, dependency
  unavailable, payload too large, and unknown transient failure classes.
- **FR-052**: Metadata-safe custody incident/support reporting MUST have a stable
  API/read-model contract when the server participates in incident truth; it
  MUST remain separate from server cabinet presentation.
- **FR-053**: This feature MAY use existing desktop local purge API contracts,
  but MUST not add server UI for purge state; any visible server cabinet purge
  presentation remains feature `058`.
- **FR-054**: This feature MUST define a 057-to-058 handoff contract containing,
  at minimum, server custody state, upload state, processing state, custody
  owner, allowed user action, review URL availability, safe incident
  availability, retention deadline, display priority, enum/fallback behavior, and
  metadata safety requirements.

### Custody State Machine

The product-level custody state MUST be representable without showing these
names to the normal user:

| State | Meaning | Default User Surface |
|-------|---------|----------------------|
| `server_unknown_local_saved` | Local package is durably retained but server cannot represent it yet | Native aggregate only |
| `server_registered` | Server meeting identity exists; upload may still be incomplete | Server read-model owns meeting truth |
| `upload_session_created` | Server upload session exists and can accept parts | Server read-model plus native aggregate progress |
| `partial_uploaded` | Some server ranges are accepted and must be resumed idempotently | Server read-model plus native aggregate progress |
| `finalized` | Upload is finalized; server processing owns next state | Server list/detail |
| `processing` | Transcription/review pipeline is not complete | Server processing status |
| `delivered` | Server can review the recording or truthful processed state | Server list/detail |
| `retained_awaiting_condition` | Local copy is safe but a condition must clear | Native aggregate with owner/action |
| `cannot_send` | Local artifact cannot produce valid upload | Native details with diagnostics/delete |
| `terminal_undelivered` | Local delivery ended by policy, deletion, or unrecoverable failure | Metadata-only report |

### State Priority And Notification Policy

When multiple custody items exist, the default summary MUST use this priority:

1. Imminent local loss: retention deadline, disk critical, or purge due.
2. Cannot send: missing, corrupt, checksum-changed, unreadable, or invalid
   required content.
3. User action required: sign in, choose workspace/account, or grant permission.
4. Admin/support/policy action required: quota, access, legal hold, stale device,
   deleted server state, or server conflict.
5. Uploading or partial upload in progress.
6. Automatic wait: offline, server unavailable, transient dependency, or due
   retry.
7. All synced.

Notification rules:

- Foreground UI should prefer inline shell status over OS notifications.
- Collapsed inspector or narrow windows still need a visible shell indicator for
  states 1-4.
- OS notification may be used only for required user action, imminent local
  loss, terminal undelivered outcome, or completed delivery when the app is not
  foreground.
- Repeated notifications for the same owner/state MUST be throttled and must not
  blame the user for transport or server conditions.
- Status must not be conveyed by color alone; each state needs text and
  VoiceOver-readable labels.

### User-Facing State Model

- **All synced**: No local custody items require user attention. Normal UI may
  omit the sync card.
- **Saving locally**: Recording has stopped and local package is being prepared.
  Copy: "Сохраняем запись на этом Mac."
- **Will send automatically**: Network or temporary server dependency is not
  currently ready, but no user action is required. Copy: "Записи сохранены на
  этом Mac. Отправим автоматически, когда сервер будет доступен."
- **Uploading**: Delivery is in progress. Copy: "2 из 5 отправляются. Остальные
  сохранены на этом Mac."
- **Known by server**: Server meeting exists and the server list owns the row.
  Copy in native shell is optional and aggregate only.
- **Needs sign-in**: User action is required. Copy: "Нужно войти, чтобы
  отправить 5 записей."
- **Needs workspace/admin**: Admin or workspace condition blocks delivery.
  Copy: "Отправка остановлена настройками рабочего пространства. Локальные
  копии сохранены."
- **Cannot send this recording**: Local artifact cannot produce a valid
  upload. Copy: "Не можем отправить эту запись: файл неполный или поврежден.
  Локальная копия сохранена. Отчет не содержит аудио и текст встречи."
- **Retention warning**: Policy deadline approaches. Copy: "Локальная копия
  будет удалена по политике 3 июля, если отправка не восстановится."
- **Terminal undelivered**: Local audio was purged or otherwise terminalized
  before delivery. Copy: "Запись не была отправлена. Локальная копия удалена по
  политике. Метаданные отчета сохранены; восстановление не обещается."

### Action Policy

| State | Normal User Action | Admin/Support Action | Forbidden Normal UI Action |
|-------|--------------------|----------------------|----------------------------|
| Will send automatically | None | None | Retry |
| Uploading | Открыть обзор, если серверная запись уже доступна | None | Stop retry |
| Needs sign-in | Войти | None | Retry |
| Needs workspace/account | Выбрать рабочее пространство или аккаунт | Admin may fix membership | Retry |
| Needs workspace/admin | Скопировать безопасный отчет | Fix policy/quota/device/access | Retry |
| Cannot send this recording | Диагностика, удалить локальную копию | Inspect safe report | Retry as primary action |
| Retention warning | Войти или скопировать безопасный отчет, если это уместно | Fix blocker before deadline | Hide warning |
| Terminal undelivered | Открыть безопасный отчет | Audit lifecycle | Promise recovery |

### Failure Ownership Matrix

| Condition | Owner | Retry Policy | Normal User Action | Copy Direction |
|-----------|-------|--------------|--------------------|----------------|
| Offline, 503, transient 429, temporary dependency | product_automatic | Automatic while retention allows | None | Запись сохранена локально, отправим автоматически |
| Expired auth or 401 | meeting_owner | Pause until sign-in, then automatic | Войти | Нужно войти; локальные копии сохранены |
| Wrong workspace/account | meeting_owner | Pause until workspace is chosen | Выбрать рабочее пространство или аккаунт | Выберите, куда отправить записи |
| 403 access revoked, stale device, policy block, legal hold | workspace_admin/support | Stop until fixed or terminalized | Скопировать безопасный отчет | Администратор должен проверить доступ или политику |
| Workspace quota | workspace_admin/support unless server marks transient | Stop until fixed | Скопировать безопасный отчет | Хранилище рабочего пространства блокирует отправку |
| 409 conflict or server range mismatch | support/product automation | Reconcile automatically when safe; otherwise blocked | Скопировать безопасный отчет | Устройство и сервер не совпали; нужна проверка продукта или поддержки |
| 410 deleted server state | policy_lifecycle/admin | Do not upload against deletion | Открыть отчет или удалить локальную копию | На сервере запись удалена; не отправляем заново |
| 413 too large or unsupported package | support/product automation | No normal retry | Диагностика, отчет или удаление | Сервер не может принять такой пакет записи |
| Missing, corrupt, checksum-changed, unreadable, or too-short files | support/product automation | No normal retry | Диагностика, отчет или удаление | Локальная копия не может стать валидной загрузкой |

### Key Entities *(include if feature involves data)*

- **Custody Item**: Product-level state for a local recording from Stop until
  server delivery or lifecycle terminalization. It carries immutable local
  recording identity, local media revision id, source kind, fingerprints,
  retention deadline, and lifecycle outcome.
- **Server-Known Recording**: A custody item that has a server meeting identity
  and is therefore represented by the server-owned meeting list.
- **Server-Unknown Local Recording**: A custody item retained on the Mac before
  the server can safely register it.
- **Custody Owner**: The role responsible for the next meaningful action:
  product automation, meeting owner, workspace admin, support, or lifecycle
  policy.
- **Custody Incident**: Metadata-only record explaining why a custody item is
  blocked, terminal, or needs non-user intervention.
- **Lifecycle Outcome**: Delivered, retained-awaiting-condition, cannot-send,
  policy-purged, user-deleted, server-deleted, or support-escalated state.
- **Meeting List Row**: Server-owned representation of a server-known recording
  in the workspace meeting list.
- **Native Sync Summary**: Compact desktop shell presentation of aggregate
  local custody state and real user actions.

## Out Of Scope

- Full implementation of a new sync engine beyond the behavior required by this
  custody specification; this feature refines the existing `042` queue and
  reconciliation contract instead of replacing it.
- A second native meeting list when the server cabinet is configured.
- DOM injection or client-side merging of local rows into the server-owned list.
- Server cabinet UI refactoring, including `cabinet/web.py`, templates, CSS,
  status-chip rendering, or meeting-list/detail layout changes; these belong to
  feature `058`.
- User-facing manual upload management, manual queue review, or retry console.
- Audio/video trimming, transcript editing, speaker editing, replace, restore,
  or reprocess flows.
- New capture paths, assisted auto-start, meeting detection, speakerphone
  cleanup, or AEC/noise-suppression claims.
- Public links, external sharing changes, billing, admin retention editor, or
  enterprise policy configuration UI.
- Direct desktop upload to object storage, MediaScribe, or any third-party STT
  provider.
- Exposing raw audio, transcript text, private local paths, signed URLs,
  cookies, credentials, tokens, or secret values in diagnostics or evidence.

## Dependencies

- Existing macOS local recording and local artifact truth.
- Existing desktop upload queue, local media revision identity, and server
  reconciliation from feature `042`; these are mandatory safety contracts for
  this feature, not optional implementation details.
- Existing transcription results pipeline behavior from feature `045`.
- Existing server-owned cabinet list/detail/review surfaces.
- Existing retention/deletion lifecycle and local purge truth from feature
  `018`.
- Existing desktop cabinet runtime truth from feature `047`.
- Existing PRD authority split: native owns capture/local/offline truth, server
  owns review/admin/lifecycle surfaces.
- Feature `058` owns server web-interface refactoring and should consume stable
  API/read-model fields from this feature rather than sharing presentation edits.
- A 057-to-058 handoff contract is required before implementation tasks are
  considered ready; it is the bridge between custody truth and server cabinet
  rendering.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 0 valid local recordings in validation are lost silently across
  offline, restart, expired-auth, server outage, and policy-blocked scenarios.
- **SC-002**: 100% of server-known recordings in validation appear only in the
  server-owned meeting list, with no duplicate native meeting row.
- **SC-003**: 100% of server-unknown local recordings in validation appear only
  as native custody status, not as fake server meeting rows.
- **SC-004**: 100% of simulated blocker states map to exactly one responsible
  owner and one allowed normal user action policy.
- **SC-005**: 0 normal user flows expose "Retry", "Stop retry", "manual retry",
  or "manual verification" for conditions the meeting owner cannot fix.
- **SC-006**: 100% of expired-auth validation cases preserve local custody and
  offer sign-in as the primary action.
- **SC-007**: 100% of policy/admin validation cases preserve local custody or
  lifecycle evidence and offer safe reporting instead of transport retry.
- **SC-008**: 100% of invalid local artifact validation cases show cannot-send
  truth without claiming server review or suggesting automatic recovery.
- **SC-009**: 100% of retention-deadline validation cases warn before
  policy-driven local purge when the user or admin can still change the
  blocking condition.
- **SC-010**: 100% of terminal undelivered outcomes in validation leave a
  metadata-only lifecycle report.
- **SC-011**: A first-time user can correctly answer "Is my recording saved?",
  "Will it be sent automatically?", and "Do I need to do anything?" within 10
  seconds from the desktop UI.
- **SC-012**: Forbidden-content scans over specs, diagnostics, logs, and
  evidence for this feature find no raw audio, transcript text, credentials,
  tokens, cookies, signed URLs, private local paths, or secret values.
- **SC-013**: Crash/relaunch validation after server registration, upload
  session creation, partial part upload, and finalize-response loss preserves
  the correct server-known identity and creates no duplicate meeting/session/job.
- **SC-014**: Background custody validation proves upload resumes on app launch,
  activation, auth change, network recovery, wake from sleep, and scheduled
  retry time without requiring the WebView route to be open.
- **SC-015**: Purge validation proves local purge acknowledgement is sent only
  after verified local deletion, tombstone, or cryptographic unrecoverability;
  failed verification reports a safe failure state.
- **SC-016**: Validation covers 401, 403, 409, 410, 413, 429, and 503 mappings
  and confirms each maps to the intended owner, retry policy, allowed action, and
  copy.
- **SC-017**: Accessibility validation confirms custody states have keyboard
  reachable actions, VoiceOver-readable labels, non-color-only status, and
  readable Russian copy in collapsed inspector, narrow window, and increased
  text-size/zoom conditions.
- **SC-018**: Malformed or partially written custody ledger validation proves
  the item is quarantined as metadata-safe blocked truth and is not dropped or
  treated as all-synced.
- **SC-019**: A 057-to-058 handoff contract exists before implementation tasks
  begin; fixture or API/read-model tests for that contract are created in the
  foundation phase before implementation tasks and must pass before feature
  closeout.
- **SC-020**: Cross-feature validation proves an offline recording that later
  registers, partially uploads, and opens the WebView produces one server-known
  read-model row plus native aggregate custody only, with no duplicate list and
  no forced route jump.

## Assumptions

- A valid stopped recording is more valuable than a clean UI; preserving and
  accounting for it takes priority over hiding all local custody states.
- The normal meeting owner is not a technical operator and should not see
  transport mechanics as work.
- Server registration should happen as early as safely possible, but only when
  auth, workspace, policy, and server availability allow it.
- A server-owned meeting row can represent upload and processing states before
  transcript content exists.
- Native local details are acceptable as a secondary disclosure for trust and
  diagnostics, but not as a primary workspace list.
- Retention/deletion policy may eventually terminalize undelivered local audio,
  but the product must warn when possible and leave metadata-only evidence.
- Existing quality warnings that do not block structural upload remain context,
  not reasons to stop delivery.
- This feature refines product behavior and UX around the existing upload loop;
  detailed technical planning will decide the smallest implementation path.
