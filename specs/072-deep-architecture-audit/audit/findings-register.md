# Findings Register

072 findings are planning evidence only. They do not authorize code deletion or
behavior changes in this stage.

## Summary By Classification

| Classification | Count | Meaning In 072 |
|----------------|-------|----------------|
| delete now | 0 | No deletion is approved in the read-only stage. |
| split soon | 9 | Good candidates for focused behavior-preserving PRs. |
| keep intentionally | 8 | Looks removable or extra, but has contract/runtime evidence. |
| risky / needs spec | 9 | Requires a separate Spec Kit slice before code changes. |

## Delete Now

No `delete now` finding is approved in 072 stage one. Any future delete-now
candidate must first show caller evidence, runtime evidence, focused validation,
and a rollback path in its own PR or slice.

## Split Soon

### F-072-001: Cabinet Web Router Is Too Large

- **Classification**: `split soon`
- **Paths**: `apps/server/src/twobrain_rec_server/cabinet/web.py`
- **Evidence**: Large server-rendered cabinet router/presentation hub.
- **Risk**: A broad edit can mix auth/session, form handling, deletion,
  calendar, meeting review, and presentation behavior.
- **Recommended next step**: Split by route family or form responsibility in a
  focused PR.
- **Pre-refactor checks**: Cabinet route tests, template rendering checks, CSRF
  checks, auth/session checks, no-secret evidence scan.

### F-072-002: Cabinet View/Rendering/Egress Are Review Hotspots

- **Classification**: `split soon`
- **Paths**:
  - `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
  - `apps/server/src/twobrain_rec_server/cabinet/rendering.py`
  - `apps/server/src/twobrain_rec_server/cabinet/egress.py`
- **Evidence**: Large files own view model construction, rendering helpers, and
  export/download behavior.
- **Risk**: Presentation cleanup can accidentally alter export authorization or
  deletion/retention expectations.
- **Recommended next step**: Split by meeting review, playback, access, and
  egress surfaces.
- **Pre-refactor checks**: Cabinet API/web tests, export/download tests,
  deletion wording review where applicable.

### F-072-003: Readiness Matrix Should Be Split By Concern

- **Classification**: `split soon`
- **Paths**: `apps/server/src/twobrain_rec_server/readiness/matrix.py`
- **Evidence**: Large readiness matrix combines multiple readiness sections.
- **Risk**: Refactor can change release-readiness truth or status reporting.
- **Recommended next step**: Extract data definitions from rendering/reporting
  without changing output.
- **Pre-refactor checks**: Readiness snapshot or unit tests, docs/status review.

### F-072-004: Desktop App Entrypoint Mixes Lifecycle And Composition

- **Classification**: `split soon`
- **Paths**: `apps/macos/RecApp/App/TwoBrainRecApp.swift`
- **Evidence**: Large `@main` app file includes lifecycle, window, capture,
  upload, and shell coordination.
- **Risk**: App lifecycle ordering and capture visibility can regress.
- **Recommended next step**: Extract composition helpers only after tests prove
  lifecycle behavior.
- **Pre-refactor checks**: Swift package tests, app launch smoke, capture state
  visibility review.

### F-072-005: Desktop Upload Queue Is A Custody Hotspot

- **Classification**: `split soon`
- **Paths**:
  - `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`
  - `apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift`
  - `apps/macos/RecApp/Sources/Upload/DesktopUploadCustodyProjection.swift`
- **Evidence**: Large upload files own queue, reconciliation, server calls,
  support incidents, and local purge acknowledgements.
- **Risk**: Refactor can break upload retry, custody truth, or local purge.
- **Recommended next step**: Split queue scheduling, server client calls,
  custody projection, and purge acknowledgement in separate PRs.
- **Pre-refactor checks**: Desktop upload queue tests, server ingest contract
  tests, local purge acknowledgement tests.

### F-072-006: Diagnostic Bundle Service Needs Smaller Evidence Families

- **Classification**: `split soon`
- **Paths**: `apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleService.swift`
- **Evidence**: Large metadata/diagnostic assembly service.
- **Risk**: Refactor can leak private content or remove required support
  evidence.
- **Recommended next step**: Split by evidence family while preserving redaction
  tests.
- **Pre-refactor checks**: Diagnostic redaction tests, support payload tests,
  secret/evidence scan.

### F-072-007: Capture Validation Script Is Too Large

- **Classification**: `split soon`
- **Paths**: `apps/macos/Scripts/validate-system-audio-capture-pivot.sh`
- **Evidence**: Large capture validation shell script with many responsibilities.
- **Risk**: Helper extraction can weaken capture acceptance proof.
- **Recommended next step**: Extract reusable helpers with unchanged CLI
  behavior.
- **Pre-refactor checks**: `bash -n`, capture validation script dry run or
  equivalent local proof, documentation update.

### F-072-008: Admin Web/API Can Be Split After Cabinet Work

- **Classification**: `split soon`
- **Paths**:
  - `apps/server/src/twobrain_rec_server/admin/web.py`
  - `apps/server/src/twobrain_rec_server/api/admin.py`
- **Evidence**: Admin web/API files are smaller than cabinet but still mix
  operational surfaces.
- **Risk**: Admin changes can alter operator access or readiness state.
- **Recommended next step**: Defer until cabinet split pattern is proven.
- **Pre-refactor checks**: Admin route tests and auth checks.

### F-072-009: Large Swift Contract Models Need Careful Segmentation

- **Classification**: `split soon`
- **Paths**:
  - `apps/macos/Shared/Sources/Models/SystemAudioCaptureModels.swift`
  - `apps/macos/Shared/Sources/Models/AudioModels.swift`
- **Evidence**: Large shared model files used by app, tools, and tests.
- **Risk**: Model moves can break serialization/contracts.
- **Recommended next step**: Split by model family only with contract tests.
- **Pre-refactor checks**: Swift tests and contract validation tool.

## Keep Intentionally

### F-072-010: Runtime-Only Python Dependencies

- **Classification**: `keep intentionally`
- **Paths**: `apps/server/pyproject.toml`, `infra/server/Dockerfile`,
  `apps/server/tests/`
- **Evidence**: `asyncpg`, `uvicorn[standard]`, `python-multipart`,
  `aiosqlite`, and `ruff` have runtime/test/tooling roles even when not all are
  imported directly.
- **Risk**: Removing them by static import count can break DB URLs, Docker
  launch, FastAPI file/form parsing, tests, or local CI.
- **Recommended next step**: Keep unless a future dependency-audit PR proves
  replacement with focused checks.
- **Pre-refactor checks**: Server tests, Docker launch check, CI lint gate.

### F-072-011: Parked Audio Driver Surface

- **Classification**: `keep intentionally`
- **Paths**: `apps/macos/AudioDriver/`
- **Evidence**: ADRs park virtual-driver routing as future advanced-routing
  work outside MVP acceptance.
- **Risk**: Deleting it can erase future safety/proof scaffolding.
- **Recommended next step**: Keep until a dedicated driver cleanup/retirement
  spec decides its fate.
- **Pre-refactor checks**: Separate Spec Kit slice and driver evidence review.

### F-072-012: Release And Deploy Scripts

- **Classification**: `keep intentionally`
- **Paths**:
  - `infra/scripts/ci-local.sh`
  - `infra/scripts/cd-remote.sh`
  - `infra/scripts/backup-rec-stack.sh`
  - `infra/scripts/rehearse-rec-restore.sh`
  - `infra/scripts/run-production-smoke.sh`
- **Evidence**: Scripts encode local CI, deploy, backup, restore, and smoke
  gates.
- **Risk**: Cleanup can weaken production safety.
- **Recommended next step**: Keep; refactor only inside release/deploy lane.
- **Pre-refactor checks**: CI, deploy dry-run, release approval for execute.

### F-072-013: Local Recording Writer Is Safety-Critical

- **Classification**: `keep intentionally`
- **Paths**: `apps/macos/RecApp/Sources/Capture/LocalRecordingWriter.swift`
- **Evidence**: Owns local recording write/finalization behavior.
- **Risk**: Casual split can break recording package integrity.
- **Recommended next step**: Keep as-is until capture-specific refactor slice.
- **Pre-refactor checks**: Local package validation and capture tests.

### F-072-014: Spec And Product History Are Evidence

- **Classification**: `keep intentionally`
- **Paths**: `specs/`, `docs/prd-voice-layer-final.md`,
  `docs/current-product-status.md`
- **Evidence**: Product baseline and prior slices explain current contracts.
- **Risk**: Deleting stale-looking docs can remove rationale before
  reconciliation.
- **Recommended next step**: Reconcile in a docs/product-truth slice.
- **Pre-refactor checks**: Product owner review and link audit.

### F-072-015: Docker Runtime Services Are Core Contracts

- **Classification**: `keep intentionally`
- **Paths**: `infra/docker-compose.yml`, `infra/docker-compose.dev.yml`
- **Evidence**: API, worker, Temporal, Postgres, MinIO, migration, and init
  services map to runtime architecture.
- **Risk**: Removing a service changes product deployment.
- **Recommended next step**: Keep; alter only under deploy/runtime spec.
- **Pre-refactor checks**: Compose config, migration, smoke checks.

### F-072-016: Desktop WebView Route Policy Is A Trust Boundary

- **Classification**: `keep intentionally`
- **Paths**: `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetRoutePolicy.swift`
- **Evidence**: Controls what server cabinet routes can appear in native shell.
- **Risk**: Simplifying it can cross native/server trust boundaries.
- **Recommended next step**: Keep; change only with route policy tests.
- **Pre-refactor checks**: Route allow/block tests and cabinet shell smoke.

### F-072-017: Diagnostic Redaction Rules Are Not Cleanup

- **Classification**: `keep intentionally`
- **Paths**: `apps/macos/RecApp/Sources/Diagnostics/`
- **Evidence**: Diagnostics are support evidence but must remain metadata-only.
- **Risk**: Removing "extra" redaction logic can leak private data.
- **Recommended next step**: Keep until redaction-specific tests prove changes.
- **Pre-refactor checks**: Redaction tests and evidence scan.

## Risky / Needs Spec

### F-072-018: Auth, Session, And Device Boundary

- **Classification**: `risky / needs spec`
- **Paths**:
  - `apps/server/src/twobrain_rec_server/api/auth.py`
  - `apps/server/src/twobrain_rec_server/auth/`
- **Evidence**: Auth/session/device behavior gates access across cabinet,
  ingest, admin, and desktop.
- **Risk**: Refactor can change account/device authority.
- **Recommended next step**: Separate auth/session/device Spec Kit slice.
- **Pre-refactor checks**: Auth tests, session expiry tests, device trust tests.

### F-072-019: Deletion And Retention Boundary

- **Classification**: `risky / needs spec`
- **Paths**: `apps/server/src/twobrain_rec_server/deletion/`
- **Evidence**: Deletion and retention affect user trust and legal/product copy.
- **Risk**: Casual edits can overpromise deletion or leave data behind.
- **Recommended next step**: Separate deletion/retention slice.
- **Pre-refactor checks**: Deletion tests, retention tests, product copy review.

### F-072-020: MediaScribe Processing Boundary

- **Classification**: `risky / needs spec`
- **Paths**:
  - `apps/server/src/twobrain_rec_server/mediascribe/`
  - `apps/server/src/twobrain_rec_server/workflows/`
  - `apps/server/src/twobrain_rec_server/processing/`
- **Evidence**: Third-party processing must remain server-owned.
- **Risk**: Refactor can leak credentials or alter dual-track processing.
- **Recommended next step**: Separate processing/MediaScribe slice.
- **Pre-refactor checks**: Worker tests, mocked MediaScribe contract, trace
  metadata review.

### F-072-021: Database, RLS, And Migration Boundary

- **Classification**: `risky / needs spec`
- **Paths**:
  - `apps/server/src/twobrain_rec_server/db/`
  - `apps/server/alembic/`
  - `infra/scripts/verify-rec-migration.sh`
- **Evidence**: Persistence and migration behavior govern production data.
- **Risk**: Refactor can break migration, tenant/account isolation, or deploy.
- **Recommended next step**: Separate DB/runtime slice.
- **Pre-refactor checks**: Migration verification, RLS validation, server tests.

### F-072-022: Capture Engine Boundary

- **Classification**: `risky / needs spec`
- **Paths**: `apps/macos/RecApp/Sources/Capture/`
- **Evidence**: Capture is product-critical and platform-native by default.
- **Risk**: Refactor can break system-audio-first MVP acceptance or one-action
  stop.
- **Recommended next step**: Separate capture slice for behavioral changes.
- **Pre-refactor checks**: Swift capture tests and local runtime proof.

### F-072-023: Langfuse Metadata Boundary

- **Classification**: `risky / needs spec`
- **Paths**: `apps/server/src/twobrain_rec_server/`, docs mentioning Langfuse
- **Evidence**: Langfuse traces must remain metadata-only by default.
- **Risk**: Instrumentation changes can leak meeting content.
- **Recommended next step**: Separate observability/privacy slice.
- **Pre-refactor checks**: Trace payload review and no-content assertion tests.

### F-072-024: Production Deploy Behavior

- **Classification**: `risky / needs spec`
- **Paths**: `infra/scripts/cd-remote.sh`, `infra/docker-compose.yml`
- **Evidence**: Deploy executes remote changes, backup, restore, migration, and
  smoke.
- **Risk**: Script cleanup can alter production safety.
- **Recommended next step**: Separate release/deploy slice.
- **Pre-refactor checks**: CI, dry-run, execute only by explicit request.

### F-072-025: Product Status Reconciliation

- **Classification**: `risky / needs spec`
- **Paths**: `docs/prd-voice-layer-final.md`, `docs/current-product-status.md`,
  `specs/`
- **Evidence**: Baseline docs and merged slice status can diverge.
- **Risk**: Incidental wording changes can alter product truth.
- **Recommended next step**: Product-truth docs slice.
- **Pre-refactor checks**: Current status review and owner approval.

### F-072-026: Cabinet Route Policy And Native Shell Authority

- **Classification**: `risky / needs spec`
- **Paths**:
  - `apps/server/src/twobrain_rec_server/cabinet/`
  - `apps/macos/RecApp/Sources/Cabinet/`
- **Evidence**: Cabinet is server-owned post-meeting review; native shell owns
  active capture trust.
- **Risk**: Refactor can move authority across UI boundaries.
- **Recommended next step**: Separate cabinet/native-shell boundary slice if
  behavior changes.
- **Pre-refactor checks**: Cabinet route tests, route policy tests, UI smoke.

