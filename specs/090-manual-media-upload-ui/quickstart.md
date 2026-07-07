# Quickstart: Manual Media Upload UI

Use synthetic fixtures only. Do not use or commit real audio, private meeting
content, transcript text, signed URLs, object keys, credentials, private local
paths, or screenshots containing private account data.

## Prerequisites

- Active feature directory: `specs/090-manual-media-upload-ui/`
- `087-own-media-upload-processing` backend/API stack is present in this
  worktree.
- Local server test dependencies are installed.

## Focused Validation Scenarios

### 1. Browser Upload Success

Expected:

- `/meetings` renders an enabled `Загрузить медиа`/manual upload entry for a
  cookie-authenticated owner.
- The upload sheet accepts exactly one selected file.
- Duration is filled from media metadata when readable, or the UI requires a
  positive manual duration.
- Starting upload shows progress and returns an accepted meeting handoff.
- The meetings list or detail route shows manual upload provenance and
  processing state without claiming transcript readiness.

### 2. Embedded Desktop Session Path

Expected:

- `/desktop/meetings` renders the same upload sheet for a valid owner session.
- Desktop-safe copy avoids browser-only admin/share/export/delete report
  workflows in the sheet.
- Native capture and Stop remain outside WebView ownership.
- If no unsafe-action-capable session/CSRF token is available, the upload
  action shows a safe sign-in/unavailable state instead of attempting transfer.

### 3. CSRF And Auth Fail Closed

Expected:

- Cookie-authenticated upload without `X-CSRF-Token` or an accepted form token
  returns `403`.
- Stale CSRF returns `403`.
- Expired/invalid session returns the existing auth/session problem.
- Bearer/device public `/api/v1/media-uploads` behavior from `087` is not
  broken by the cabinet wrapper.

### 4. Safe Failure States

Expected:

- Missing file, missing duration, zero duration, empty file, oversized file,
  network failure, and server rejection all produce localized safe recovery
  states.
- UI and tests do not expose MediaScribe credentials, signed URLs, object keys,
  raw media, raw transcript text, private local paths, or dependency job ids.
- Aborted upload before acceptance does not claim a meeting exists.
- Accepted upload with later processing failure shows accepted media separately
  from transcript/notes readiness.

### 5. Existing Workflow Regression

Expected:

- Existing `087` manual API upload tests pass.
- Existing dual-track desktop processing tests pass.
- Existing cabinet deletion CSRF and meeting list/detail tests pass.
- Existing desktop route policy remains safe; Swift tests pass if touched.

## Focused Test Commands

Run focused tests during implementation as they are added:

```sh
cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q \
  tests/integration/test_cabinet_manual_upload.py \
  tests/integration/test_manual_media_upload.py \
  tests/integration/test_cabinet_csrf.py \
  tests/integration/test_cabinet_meeting_list.py \
  tests/unit/test_cabinet_web_shell.py \
  tests/contract/test_cabinet_static_assets_contract.py \
  tests/contract/test_ingest_openapi_contract.py
```

```sh
cd apps/server && PYTHONPATH=src uv run --extra dev ruff check .
```

Run if macOS cabinet route-policy or WebView behavior changes:

```sh
swift test --package-path apps/macos --disable-swift-testing --filter 'DesktopCabinet'
```

## Forbidden Content Scan

Run a metadata-safety scan before closeout:

```sh
rg -n -i \
  -e "authorization\\s*[:=]\\s*bearer\\s+[a-z0-9._~+/-]{10,}" \
  -e "x-amz-signature=[a-z0-9]" \
  -e "-----BEGIN [A-Z ]*PRIVATE KEY-----" \
  -e "(api[_-]?key|access_token|refresh_token|signed_url|object_key|bucket|private_path|raw_transcript|raw_audio|mediascribe_job)\\s*[:=]\\s*[^,[:space:]}]{4,}" \
  specs/090-manual-media-upload-ui \
  apps/server/src/twobrain_rec_server/api \
  apps/server/src/twobrain_rec_server/ingest \
  apps/server/src/twobrain_rec_server/cabinet \
  apps/server/tests
```

Expected outcome: no secret, signed-link, raw media/transcript, private path,
or dependency job evidence is committed. Detector source references are allowed
only when clearly part of the scan itself.

## Closeout Gate

Before implementation closeout or PR:

```sh
infra/scripts/ci-local.sh
```

Expected:

- `ci_local_result=pass`
- Focused tests above pass
- No production deploy was run
- `tasks.md` items are checked only after their validation evidence passes
