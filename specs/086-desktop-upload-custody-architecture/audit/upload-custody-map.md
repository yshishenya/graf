# Upload Custody Architecture Map

## Evidence Baseline

086 is anchored from clean `origin/master` after PR #2630:

- Branch: `codex/086-desktop-upload-custody-architecture`
- Base commit: `8e007296`
- Stage: read-only documentation and audit artifacts only

Static evidence highlights:

- `DesktopUploadQueueService.swift`: 1,657 lines.
- `DesktopUploadCustodyProjection.swift`: 1,550 lines.
- `DesktopUploadClient.swift`: 1,112 lines.
- `apps/macos/RecApp/Sources/Upload/`: 4,717 lines.
- Existing tests reference upload client, custody projection, local purge,
  support incident fixtures, support action copy, and artifact profile logic.
- Server surfaces include ingest routes, local purge routes under cabinet API,
  deletion local purge service, support incident route/service/redaction, and
  API schemas.

## Flow 1: Local Package To Queue

**Plain-language goal**: A completed local recording package becomes a desktop
queue item without losing local recording truth.

**Primary paths**:

- `apps/macos/RecApp/Sources/Capture/LocalRecordingWriter.swift`
- `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`
- `apps/macos/Shared/Sources/Models/`

**Current responsibilities**:

- discover completed recording packages;
- validate package/manifest readiness;
- create deterministic queue item identity;
- preserve local artifact profile and upload eligibility;
- persist queue document state.

**Risk**:

- Splitting queue creation away from local package validation can make failed or
  partial packages look uploadable.

**Future boundary**:

- Queue persistence and package discovery may be separated only if queue
  document compatibility and artifact profile tests pin behavior.

## Flow 2: Queue To Server Upload/Ingest

**Plain-language goal**: Desktop sends the package to server-mediated ingest and
can resume missing ranges safely.

**Primary paths**:

- `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`
- `apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift`
- `apps/server/src/twobrain_rec_server/api/ingest.py`
- `apps/server/src/twobrain_rec_server/ingest/`
- `apps/server/src/twobrain_rec_server/api/schemas.py`

**Current responsibilities**:

- create meeting;
- create upload session;
- upload file ranges;
- query missing ranges;
- retry missing ranges;
- finalize upload;
- reconcile server state back into desktop queue state.

**Risk**:

- Transport extraction can change idempotency keys, retry categories,
  missing-range behavior, or server status vocabulary.

**Future boundary**:

- Extract request/DTO helpers before moving orchestration. Keep `upload(_:)`
  behavior pinned with upload client tests and server ingest contract checks.

## Flow 3: Custody Projection And Review Readiness

**Plain-language goal**: Desktop explains who owns the next step: local device,
server ingest, processing, user action, deletion, or support.

**Primary paths**:

- `apps/macos/RecApp/Sources/Upload/DesktopUploadCustodyProjection.swift`
- `apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift`
- `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetConfiguration.swift`

**Current responsibilities**:

- derive custody state;
- derive visible copy keys and actions;
- summarize affected items;
- produce support-safe reports;
- surface review links and local queue status.

**Risk**:

- Presentation-looking code is actually product trust copy. Moving it casually
  can change what users believe about custody/deletion/support.

**Future boundary**:

- Split support report types from user-facing custody copy only after tests
  prove copy keys, safe reports, and accessibility expectations.

## Flow 4: Deletion And Local Purge

**Plain-language goal**: Server deletion can request local desktop purge, and
desktop acknowledges only verified metadata-safe local deletion truth.

**Primary paths**:

- `apps/server/src/twobrain_rec_server/deletion/local_purge.py`
- `apps/server/src/twobrain_rec_server/deletion/service.py`
- `apps/server/src/twobrain_rec_server/api/cabinet.py`
- `apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift`
- `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`

**Current responsibilities**:

- create local purge tasks for deletion requests;
- list local purge tasks for desktop;
- delete local artifacts inside the recordings root;
- acknowledge server task with verification state;
- update deletion report local purge state.

**Risk**:

- Local purge is deletion truth. A refactor can overstate deletion success or
  leak local file paths.

**Future boundary**:

- Local purge acknowledgement can become its own focused PR only with desktop
  local purge tests and server deletion/local purge tests.

## Flow 5: Support Incident Evidence

**Plain-language goal**: Users can submit safe support evidence for custody or
upload blockers without leaking meeting content.

**Primary paths**:

- `apps/macos/RecApp/Sources/Upload/DesktopUploadCustodyProjection.swift`
- `apps/macos/RecApp/Sources/Upload/DesktopSupportIncidentActionStrip.swift`
- `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`
- `apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift`
- `apps/server/src/twobrain_rec_server/api/support_incidents.py`
- `apps/server/src/twobrain_rec_server/support/redaction.py`
- `apps/server/src/twobrain_rec_server/support/incidents.py`

**Current responsibilities**:

- build metadata-only support report;
- enforce safe schema version and safe fields;
- submit or fall back to copy;
- server-side redaction, idempotency, rate limit, and GitHub issue submission.

**Risk**:

- Splitting support types from custody projection can drop redaction or safe
  reason-code constraints.

**Future boundary**:

- Support incident payload/reporting can be split only with fixture tests,
  redaction tests, and no-secret scans.

## Healthy Architecture

- Desktop upload remains server-mediated; desktop does not talk to MediaScribe.
- Local purge is explicit and separate from upload success.
- Support incidents are designed around metadata-only safe reports.
- Existing tests already cover important upload/custody/support/local purge
  behavior and should be reused before adding new tooling.

## Real Pain

- Queue service combines persistence, scan/enqueue, retry scheduling, upload
  orchestration, reconciliation, local purge, support incident submission, and
  artifact profiles.
- Upload client combines transport configuration, HTTP requests, DTOs, upload
  session lifecycle, local purge API, support API, and helper functions.
- Custody projection combines state machine, user copy, support report payloads,
  safe reports, and localization copy.
- Server API schemas are broad contract surfaces; moving client DTOs without
  server checks is risky.

## Delete-Now Result

No `delete now` candidate is approved in stage one.

Potential deletion must wait for a dedicated proof pass because static search
can miss Codable persistence, route/API contracts, test fixtures, and support
or deletion lifecycle roles.
