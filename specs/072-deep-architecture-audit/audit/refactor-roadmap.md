# Refactor Roadmap

072 does not implement these batches. Each batch is a future small PR or
separate Spec Kit slice with its own evidence.

## Current Master Refresh

The 2026-07-03 refresh in
`specs/072-deep-architecture-audit/audit/current-master-priority-refresh.md`
records the current priority after the merged cabinet follow-up PRs. Do not
keep doing cabinet rendering micro-splits. The next high-value architecture
work is either:

1. `086-desktop-upload-custody-architecture` as a product-value-first,
   high-risk read-only slice before code; or
2. `086-cabinet-egress-boundary` as a smaller server-side split with strong
   egress/export/playback/admin tests.

`delete now` remains zero until a focused deletion proof pass produces caller,
runtime, entrypoint, validation, and rollback evidence.

## Batch Order

### RB-072-01: Cabinet Web Follow-Up Segmentation

- **Goal**: Reduce remaining cabinet auth/calendar route, view-model, rendering,
  and egress hotspots without changing behavior. Keep `cabinet/web.py` as the
  route-family aggregator unless a focused test proves the include boundary is
  wrong.
- **Findings**: F-072-001, F-072-002.
- **Included paths**:
  - `apps/server/src/twobrain_rec_server/cabinet/web_routes/auth.py`
  - `apps/server/src/twobrain_rec_server/cabinet/web_routes/calendar.py`
  - `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
  - `apps/server/src/twobrain_rec_server/cabinet/rendering.py`
  - `apps/server/src/twobrain_rec_server/cabinet/egress.py`
- **Excluded paths**: auth provider semantics, deletion service semantics,
  MediaScribe, deploy scripts, and `cabinet/web.py` aggregator behavior except
  route include wiring required by a split.
- **Expected diff shape**: Split-only plus focused tests if missing.
- **Validation**: Cabinet route tests, template rendering tests, CSRF/session
  checks, export/download checks, no-secret evidence scan, `infra/scripts/ci-local.sh`.
- **Release policy**: No deploy unless separately requested.
- **Rollback/stop condition**: Stop if route responses, CSRF/session behavior,
  export/download authorization, or template output changes beyond a documented
  split-only move; revert the split PR as one unit.

### RB-072-02: Readiness Matrix Split

- **Goal**: Separate readiness data definitions from rendering/reporting.
- **Findings**: F-072-003.
- **Included paths**: `apps/server/src/twobrain_rec_server/readiness/`
- **Excluded paths**: release script behavior and product acceptance claims.
- **Expected diff shape**: Split-only, behavior-preserving.
- **Validation**: Readiness snapshot/unit tests, docs status review,
  `infra/scripts/ci-local.sh`.
- **Release policy**: No deploy unless release readiness docs require it later.
- **Rollback/stop condition**: Stop if readiness labels, ordering, or acceptance
  claims change without an explicit product-status decision.

### RB-072-03: Desktop Upload Custody Split

- **Goal**: Make upload queue, server client, custody projection, and local
  purge acknowledgement easier to review.
- **Findings**: F-072-005.
- **Included paths**: `apps/macos/RecApp/Sources/Upload/`
- **Excluded paths**: server ingest schema changes, deletion behavior,
  MediaScribe processing.
- **Expected diff shape**: Split-only plus test fixture cleanup.
- **Validation**: `swift test --package-path apps/macos`, upload queue tests,
  local purge acknowledgement tests, server ingest contract checks if API calls
  move.
- **Release policy**: No deploy.
- **Rollback/stop condition**: Stop if retry, custody, ingest-session, or local
  purge acknowledgement behavior changes.

### RB-072-04: Desktop App Composition Split

- **Goal**: Extract app composition/lifecycle helpers from
  `TwoBrainRecApp.swift` without changing capture visibility or startup order.
- **Findings**: F-072-004.
- **Included paths**: `apps/macos/RecApp/App/`,
  `apps/macos/RecApp/Sources/`
- **Excluded paths**: capture algorithm changes, driver work, upload protocol.
- **Expected diff shape**: Move-only/split-only.
- **Validation**: Swift tests, app launch smoke, capture state review.
- **Release policy**: No deploy.
- **Rollback/stop condition**: Stop if launch ordering, capture visibility,
  manual stop, or window lifecycle behavior changes.

### RB-072-05: Diagnostic Evidence Split

- **Goal**: Split diagnostic bundle assembly by evidence family while
  preserving redaction.
- **Findings**: F-072-006, F-072-017.
- **Included paths**: `apps/macos/RecApp/Sources/Diagnostics/`
- **Excluded paths**: support token handling, raw audio/transcript evidence,
  server support integration behavior.
- **Expected diff shape**: Split-only with redaction tests.
- **Validation**: Diagnostic redaction tests, support payload tests,
  no-secret/evidence scan.
- **Release policy**: No deploy.
- **Rollback/stop condition**: Stop if redaction output, support evidence shape,
  or private-content exclusion changes.

### RB-072-06: Capture Script Helper Extraction

- **Goal**: Extract reusable shell helpers from the system-audio capture
  validation script without weakening proof.
- **Findings**: F-072-007.
- **Included paths**: `apps/macos/Scripts/`
- **Excluded paths**: capture implementation code and acceptance criteria.
- **Expected diff shape**: Helper extraction and shell tests/checks.
- **Validation**: `bash -n` on changed scripts, local capture validation dry-run
  or equivalent proof, script usage docs.
- **Release policy**: No deploy.
- **Rollback/stop condition**: Stop if CLI flags, exit codes, evidence files, or
  capture-proof semantics change.

### RB-072-07: Shared Swift Model Segmentation

- **Goal**: Split large shared model files by model family while preserving
  serialization and contract behavior.
- **Findings**: F-072-009.
- **Included paths**: `apps/macos/Shared/Sources/Models/`
- **Excluded paths**: API contract behavior unless separately specified.
- **Expected diff shape**: Move-only/split-only.
- **Validation**: `swift test --package-path apps/macos`, contract validation
  tool.
- **Release policy**: No deploy.
- **Rollback/stop condition**: Stop if serialization, fixture compatibility, or
  contract validation output changes.

### RB-072-08: Admin Surface Split

- **Goal**: Apply the proven cabinet split pattern to admin web/API surfaces.
- **Findings**: F-072-008.
- **Included paths**: `apps/server/src/twobrain_rec_server/admin/`,
  `apps/server/src/twobrain_rec_server/api/admin.py`
- **Excluded paths**: deploy scripts, auth semantics, production config.
- **Expected diff shape**: Split-only after cabinet pattern is proven.
- **Validation**: Admin route tests, auth checks, `infra/scripts/ci-local.sh`.
- **Release policy**: No deploy unless admin changes are bundled into a release.
- **Rollback/stop condition**: Stop if operator access, admin route behavior, or
  readiness state changes outside the split scope.

## Separate Spec Kit Slices Required

These areas should not be folded into routine split PRs:

- Auth/session/device changes.
- Deletion/retention behavior.
- MediaScribe/Temporal processing behavior.
- DB, RLS, migrations, and production data changes.
- Capture engine behavior.
- Langfuse/observability payload behavior.
- Production deploy behavior.
- Product status reconciliation that changes accepted product truth.
- Cabinet/native-shell authority changes.

## Batch Validation Matrix

| Batch | Minimal Checks Before PR Merge |
|-------|--------------------------------|
| RB-072-01 | Cabinet tests, CSRF/session checks, export/download checks, local CI |
| RB-072-02 | Readiness tests/snapshots, docs status review, local CI |
| RB-072-03 | Swift tests, upload queue tests, local purge checks |
| RB-072-04 | Swift tests, app launch smoke, capture state review |
| RB-072-05 | Redaction tests, support payload tests, evidence scan |
| RB-072-06 | `bash -n`, capture validation dry-run/proof |
| RB-072-07 | Swift tests, contract validation tool |
| RB-072-08 | Admin route tests, auth checks, local CI |

## Plain-Language Closeout For 072

1. Architecture is already reasonable where product trust boundaries are
   explicit: native capture, server-owned processing, server cabinet, scripted
   deploy gates, and documented ADRs.
2. The real pain is not a missing framework. It is reviewability: remaining
   cabinet route/view/render/egress, readiness, desktop upload, app lifecycle,
   diagnostics, model, and capture script files mix too many responsibilities.
3. Nothing is safe to delete in the first read-only stage. Several things that
   look removable are intentional runtime, test, future-routing, or deploy
   contracts.
4. The next safe move is small split PRs, one boundary at a time.
5. Each refactor batch needs focused tests for its boundary plus the relevant
   repository gate; deploy proof belongs only to release/deploy slices.
