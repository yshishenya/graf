# Research: Надёжный полный цикл автоматической записи

## Decision 1: Three states are the complete local preference model

**Decision**: runtime policy reads only `automaticRecordingRules`. Missing and
new targets resolve to `ask`. Legacy `detectionMode`,
`targetScopedAutoRecordEnabled`, `autoRecordTargetIds` and acknowledgement keys
may be decoded once for compatibility, but ambiguous legacy data maps to `ask`
and the obsolete keys are not written again.

**Rationale**: the current settings already contain the three-state map, but
global fields can still suppress prompts or gate `always`, creating hidden
fourth and fifth states. A one-way decoder preserves old files without
preserving contradictory runtime behavior.

**Alternatives considered**: keep the global switches hidden (still two sources
of truth); delete old files (loses explicit choices); migrate legacy selected
IDs to `always` (grants recording without proven target-specific intent).

## Decision 2: Server permission is removed in two release steps

**Decision**: first, client models and decision code ignore
`assistedAutoStartPolicy` and acknowledgement while remaining tolerant of the
extra response field. Second, remove the field, builder, settings, environment
variables, OpenAPI schema and dedicated tests from the server.

**Rationale**: removing the field first disables automatic paths in old clients.
Keeping it after the new client is ready leaves dead policy that can accidentally
be reconnected.

**Alternatives considered**: permanent deprecated field (ongoing ambiguity);
simultaneous server-first cut (breaks installed clients); new server version or
endpoint (unnecessary because the registry contract is already tolerant).

## Decision 3: Bundle a baseline registry, keep remote registry updates

**Decision**: ship one validated JSON document in the existing app resources.
Resolution order is valid remote → valid cache → bundled baseline. The baseline
passes the same target/non-target validator, contains no policy field and has no
expiry timestamp; its lifetime is bounded by the signed client version that
contains it.

**Rationale**: settings currently become empty on a clean offline install
because `MeetingTargetRegistryStore` accepts only remote or cache. A static
resource solves first use without inventing a registry service or duplicating
validation logic.

**Alternatives considered**: hard-code targets in Swift (duplicate schema and
harder review); require first network connection (violates local default);
persist a generated cache during installation (more packaging state).

## Decision 4: Preserve one stop intent across startup

**Decision**: app orchestration stores one pending stop request. Any stop call
during `recordingStartInProgress` records the request rather than returning
silently. The start path drains it after clearing the transition flag. A meeting
end may register the request against the in-progress detector target before a
capture session exists.

**Rationale**: `stopManualRecording` currently returns while startup is active,
and the end handler also requires an already visible session. This loses the
only stop signal in the exact race that matters.

**Alternatives considered**: delayed blind retry in the detector (racy and
duplicated); make stop block on startup (deadlock risk on main actor); add a
second capture coordinator (unnecessary).

## Decision 5: Reconcile detector capture at observation boundaries

**Decision**: after a current snapshot is applied, compare the bundle stored in
the active detector-created capture with detector activity. If absent, request
the same meeting-ended stop. Track last trusted evidence for that bundle and use
the existing one-second advance loop to stop after 10 continuous minutes with
no evidence.

**Rationale**: observer reset intentionally clears stale detector state. Without
an explicit post-snapshot comparison, a meeting that ended during sleep or
observer outage can continue recording indefinitely.

**Alternatives considered**: stop immediately on every observer reset (cuts
valid meetings during restart); new watchdog service (duplicate timer/lifecycle);
rely only on app audio silence (can mistake a quiet valid meeting).

## Decision 6: Use the v5 manifest as the recovery marker

**Decision**: write a valid `active` v5 manifest in the recording directory
before sample acceptance. The same file is atomically replaced by the final,
degraded or damaged manifest. Do not add another journal format.

**Rationale**: startup scanning currently ignores directories without a
manifest. The manifest already has active status, track state, failure code and
metadata-safe fields needed to identify and classify the package.

**Alternatives considered**: separate `capture-state.json` (second lifecycle
file and reconciliation); scan every directory heuristically (weak identity and
more false positives); create manifest only on stop (current data-loss hole).

## Decision 7: Checkpoint the existing WAV writer

**Decision**: at intervals no longer than 10 seconds, update the WAV header to
the current frame count, synchronize the file, then resume appending. Final
close still performs the authoritative header write. Recovery validates even
byte length, derives frame count, repairs the header and can rebuild playback
media from the canonical WAV.

**Rationale**: PCM samples are already appended continuously, but an open WAV
has a placeholder header and no explicit durability bound. A small native
checkpoint makes the existing file self-describing after a crash.

**Alternatives considered**: segmented WAV chunks (new assembly format);
continuous manifest rewrite per audio callback (I/O and capture risk); depend on
process-exit cleanup (does not cover crash or power loss).

## Decision 8: Extend the existing queue with `saving`

**Decision**: create or merge the deterministic queue item when stop begins and
mark it `saving`. Final manifest refresh transitions the same item to queued,
retrying or blocked. Startup recovery performs the same merge. `saving` is never
upload-eligible.

**Rationale**: a row is currently created only after all finalization succeeds.
The upload queue already owns durable local identity, sorting, retries and
retention, so it is the smallest truthful place for pre-upload visibility.

**Alternatives considered**: transient view-only row (lost after restart);
second local-recordings store (duplicate truth); represent saving as `blocked`
(misleading user state and retry semantics).

## Decision 9: Damage is a projection, not a second queue state machine

**Decision**: recovery writes a stable metadata-safe failure code such as
`recording_recovery_not_possible`; queue profile remains non-uploadable and the
common-list projection renders `Запись повреждена`, delete only. Sendable
degraded artifacts keep the normal queue lifecycle.

**Rationale**: uploadability already comes from manifest/profile validation.
Adding a parallel damaged-recording entity would duplicate deletion and list
identity.

**Alternatives considered**: add a damaged database/table; expose generic
`Нужна проверка`; offer `Отправить` for an artifact known to be impossible.

## Decision 10: Use one WebView bridge for the common list

**Decision**: serialize bounded local row view models into the existing embedded
meeting-list WebView. `cabinet.js` inserts them into the list container and sends
only item ID for `Отправить` or existing delete handling. Rows with a server
meeting ID merge with matching server markup. Browser-only cabinet receives no
local payload and is unchanged.

**Rationale**: the current shell displays a compact local panel above the WebView
and a second custody list in the inspector. A bridge gives one visual list
without building a new native history or changing server persistence.

**Alternatives considered**: rebuild the full list natively (large duplicate
surface); add server rows for uploads that have not reached the server (false
server truth); retain the two side panels (does not meet the user journey).

## Decision 11: Existing retry is the `Отправить` action

**Decision**: UI calls `DesktopUploadQueueService.retry(itemId:)`, reloads items
and invokes the existing processing loop. The service retains deterministic ID,
attempt history and reconciliation before upload.

**Rationale**: manual retry already exists and correctly refuses non-uploadable
artifacts. Only the user-facing route and label are missing.

**Alternatives considered**: direct upload from UI (bypasses durability and
reconciliation); create a new immediate-upload API (duplicate); label
`Повторить сейчас` (rejected product wording).

## Decision 12: Metadata-only evidence and no new telemetry subsystem

**Decision**: reuse existing `AppLog`, manifest failure codes and queue retry
records. Record bundle/target IDs, session/directory/queue IDs, states, reason
codes and timings only.

**Rationale**: the system already has sufficient bounded diagnostics. The gap is
complete lifecycle coverage, not a new store.

**Alternatives considered**: raw audio fixtures or real meeting screenshots in
git (prohibited); new analytics service (unnecessary); filesystem paths in logs
(privacy and secret-path risk).
