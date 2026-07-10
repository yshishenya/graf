# Implementation Plan: Manual Media Upload UI

**Branch**: `codex/090-manual-media-upload-ui` | **Date**: 2026-07-07 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/090-manual-media-upload-ui/spec.md`

## Summary

Add the user-facing manual media upload surface for browser and embedded
desktop cabinet users on top of `087` one-file upload processing. Keep upload
inside the meetings workspace as a compact server-owned sheet, use the existing
Jinja/HTMX/static JS/CSS cabinet foundation, add a CSRF-protected cabinet upload
wrapper that reuses the `087` backend helper, and refresh the meeting
list/detail handoff after server acceptance. Do not add native macOS upload
business logic, a new frontend build pipeline, a separate upload dashboard, a
new DB schema, or a production deploy.

## Technical Context

**Language/Version**: Python 3.13 FastAPI server, Jinja2 templates, static
cabinet CSS and vanilla JavaScript, HTMX 2.0.10 already vendored, Swift 6/macOS
route-policy tests where desktop shell invariants are touched.

**Primary Dependencies**: Existing FastAPI, `python-multipart`, Pydantic,
SQLAlchemy asyncio, MinIO storage wrapper, cabinet templates/assets, pytest,
ruff, Swift XCTest. No new runtime or frontend build dependency.

**Storage**: Existing `087` Postgres/MinIO upload, media revision, upload
session, processing workflow, MediaScribe job, transcript, outcome, lifecycle,
and deletion accounting. This slice expects no new migration beyond the `087`
stacked backend migration.

**Testing**: Focused server unit/contract/integration tests for cabinet upload
rendering, CSRF/auth, upload success/failure, OpenAPI drift, and cabinet list
handoff; focused macOS tests only if route policy or WebView invariants change;
quickstart scenarios; final `infra/scripts/ci-local.sh`.

**Risk / Validation Lane**: High-risk feature. It touches user-visible upload
UX, storage custody entry, cookie/session unsafe actions, CSRF, desktop WebView
boundaries, accessibility/localization, and processing handoff.

**Release Gate**: No deploy. This is implementation readiness only; production
deploy requires a separate release/deploy lane and explicit approval.

**Target Platform**: Linux containerized server/browser cabinet plus macOS
desktop embedded WebView. Native macOS capture and desktop local uploader remain
regression boundaries, not implementation surfaces.

**Project Type**: Server-owned web/API service with embedded desktop cabinet
surface inside a native macOS app.

**Performance Goals**: A small local validation media file shows client-side
upload progress and reaches accepted meeting state in under two minutes.
Progress UI remains responsive during transfer. Meeting list refresh or detail
handoff appears within one existing poll/refresh after acceptance.

**Constraints**: No direct object-storage URLs or credentials in clients. No
MediaScribe egress from browser/desktop. No raw audio/transcript/private paths
in logs, errors, tests, screenshots, or evidence. No full video review promise.
No separate upload dashboard. No frontend framework/build pipeline. Embedded
web UI must not own native Record/Stop, active recording truth, local queue
truth, permissions, or diagnostics.

**Scale/Scope**: One media file per upload draft. No bulk import, resumable
browser upload, background upload after navigation, direct MinIO upload,
transcoding, or native desktop picker bridge.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Before Phase 0**: PASS with high-risk gates.

- Capture-first MVP integrity: PASS. No native capture, audio routing,
  permission, Record, Stop, or local package uploader behavior changes are
  planned.
- Visible consent and user control: PASS. Manual upload is explicit user action
  and does not add recording or assisted auto-start behavior.
- Data boundary and secret discipline: PASS with required tasks. Upload remains
  server-mediated; browser and desktop never receive MediaScribe credentials,
  signed dependency URLs, object keys, raw media, raw transcript text, or
  private local paths.
- Deletion truth and lifecycle accounting: PASS through `087` reuse. After
  acceptance, cancellation routes to existing meeting detail/deletion truth
  rather than overpromising universal erasure.
- Spec-driven delivery: PASS. Full Spec Kit sequence is required:
  specify, clarify, plan, checklist, tasks, analyze, issue sync, implement.
- UI and brand-distance: PASS with required tasks. The design reuses the
  original GRAF cabinet system and avoids copying competitor UI or adding a new
  visual language.
- Ponytail form: PASS. Reuse existing ingest, processing, cabinet shell,
  templates, assets, and tests; add only the wrapper/helper and UI behavior
  needed for this slice.

**After Phase 1 design**: PASS. Research, data model, and contracts keep the
change inside the existing cabinet and `087` upload boundaries. No constitution
violation or unresolved technical clarification remains.

## Validation Plan

- Run focused server tests for manual cabinet upload rendering, CSRF/auth
  rejection, successful cookie-session upload, safe failure states, meeting list
  handoff, and existing `087` upload behavior.
- Run OpenAPI contract drift tests if the new cabinet upload route is included
  in generated API schema.
- Run cabinet static/foundation tests to ensure no frontend toolchain, CDN,
  external font, or UI framework is introduced.
- Run focused macOS `DesktopCabinet` tests if route policy or WebView request
  behavior changes; otherwise record that no Swift source changed.
- Run quickstart scenarios from [quickstart.md](./quickstart.md).
- Run `infra/scripts/ci-local.sh` before closeout because the slice changes
  high-risk shared web/API behavior and user-facing UX.
- Do not run production CD dry-run/execute in this slice.

## Project Structure

### Documentation (this feature)

```text
specs/090-manual-media-upload-ui/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── manual-upload-ui-contract.md
├── checklists/
│   ├── requirements.md
│   ├── security.md
│   └── ux.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/src/twobrain_rec_server/api/
├── cabinet.py
├── ingest.py
└── schemas.py

apps/server/src/twobrain_rec_server/ingest/
└── manual_media_upload.py

apps/server/src/twobrain_rec_server/cabinet/
├── rendering.py
├── rendering_shared.py
├── templates.py
├── static/cabinet/cabinet.css
├── static/cabinet/cabinet.js
└── templates/cabinet/
    ├── pages/meeting_list_content.html
    └── fragments/manual_upload.html

apps/server/tests/
├── contract/
│   ├── test_cabinet_static_assets_contract.py
│   └── test_ingest_openapi_contract.py
├── integration/
│   ├── test_cabinet_manual_upload.py
│   ├── test_cabinet_csrf.py
│   └── test_manual_media_upload.py
└── unit/
    └── test_cabinet_web_shell.py

apps/macos/RecApp/Sources/Cabinet/
apps/macos/Shared/Tests/
CHANGELOG.md
AGENTS.md
```

**Structure Decision**: Keep server-owned upload UI inside the existing cabinet
modules. Extract only the reusable backend upload helper needed to let the
public `087` endpoint and the new CSRF-protected cabinet route share custody
logic. Use existing template/static asset patterns rather than a new frontend
package. macOS source changes are avoided unless route-policy tests prove they
are needed.

## Complexity Tracking

No constitution violations.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
