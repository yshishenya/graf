# Quickstart: Recording Date And Smart Title

This quickstart defines the smallest focused validation set that proves feature
`059` before release/deploy evidence.

## Preconditions

- Work from `specs/059-recording-date-title/`.
- Implementation branch `codex/059-recording-date-title` must include merged
  057/058 work before code changes start.
- Use only synthetic app/date and generic title fixtures.
- Do not call real calendar APIs, window-title APIs, or live foreground app polling in 059 validation.
- Do not commit raw audio, transcript text, emails, raw URLs, tokens, signed URLs, private local paths, or live meeting names.

## Coordination Evidence - 2026-06-27

- Merge basis: `codex/059-recording-date-title` was fast-forwarded to
  `origin/master` at `586691f`.
- 057 basis: `057-local-upload-custody` and review fixes are included through
  PR #2052 and PR #2097.
- 058 basis: `058-web-cabinet-htmx-shell` and review fixes are included through
  PR #2096 and PR #2234.
- Final implementation branch policy: continue directly on
  `codex/059-recording-date-title`; do not stack on the old 057/058 worktrees.

Post-merge touchpoint check:

| Path | Status | 059 note |
|------|--------|----------|
| `apps/macos/Shared/Sources/Models/AudioModels.swift` | exists | Add only recording title/date metadata fields needed by queue/upload. |
| `apps/macos/RecApp/Sources/Capture/LocalRecordingManifestService.swift` | exists | Preserve manifest `startedAt`/`stoppedAt`; do not replace with upload/finalize time. |
| `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift` | exists | 057 custody code is present; persist 059 metadata without changing custody identity. |
| `apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift` | exists | Create-meeting request sends persisted `title`, `started_at`, and `ended_at` from queue metadata. |
| `apps/macos/RecApp/Sources/Upload/RecordingMetadataResolver.swift` | added in 059 | Minimal app/date/generic resolver for deterministic title and safe basename metadata. |
| `apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleService.swift` | exists | Emit title provenance evidence as metadata-only summary without raw title or basename. |
| `apps/macos/Shared/Sources/Diagnostics/DiagnosticRedactor.swift` | exists | Keep title provenance evidence metadata-only. |
| `apps/macos/Shared/Tests/RecordingMetadataResolverTests.swift` | added in 059 | Resolver tests cover source order, suppression, safe basename, and 500 ms synthetic budget. |
| `apps/server/src/twobrain_rec_server/api/problems.py` | exists | Return metadata-only request validation problem responses without raw unsafe input. |
| `apps/server/src/twobrain_rec_server/main.py` | exists | Register the metadata-only request validation handler. |
| `apps/server/src/twobrain_rec_server/ingest/meetings.py` | exists | Server accepts/persists safe `title`, `started_at`, `ended_at` and rejects unsafe title-like input. |
| `apps/server/src/twobrain_rec_server/cabinet/queries.py` | exists | API already recognizes `started_desc`/`started_asc`; keep sort based on `Meeting.started_at`. |
| `apps/server/src/twobrain_rec_server/cabinet/view_models.py` | exists | 058 view-model split is present; add date/title fallback here. |
| `apps/server/src/twobrain_rec_server/cabinet/rendering.py` | exists | 058 rendering split is present; keep row/detail rendering in rendering helpers. |
| `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_list_content.html` | exists | 058 Jinja sort control is present; expose recording-date sort there. |
| `apps/server/tests/integration/test_cabinet_meeting_list.py` | exists | Extend current list/search/sort shell coverage for recording-date sort. |
| `apps/server/tests/unit/test_cabinet_view_models.py` | exists | Extend current display helper coverage for date/title fallback. |

## Scenario 1 - Recording Date Survives Delayed Upload

1. Create or fixture a local recording manifest with:
   - `startedAt = 2026-06-26T11:30:00Z`
   - `stoppedAt = 2026-06-26T12:05:12Z`
   - upload/create time at least 24 hours later.
2. Enqueue/upload through the desktop path.
3. Verify server meeting `started_at` and `ended_at` match the manifest.
4. Verify cabinet list/detail show the recording date, not upload date.
5. Repeat with a display-timezone change fixture and verify the canonical stored start instant is unchanged.
6. Seed at least two meetings with different `started_at` values and verify started-date sort uses the recording start instant.

Expected result: pass.

## Scenario 2 - Title Source Matrix

Run synthetic title candidates:

| Case | Already-available app context | External context outside 059 | Expected title source |
|------|-------------------------------|------------------------------|-----------------------|
| App context known | `Chrome` | none | `app_context` |
| Native app context known | `Zoom` | none | `app_context` |
| Unknown context | none | none | `generic` |
| Window title would exist elsewhere | `Chrome` | not provided to resolver | `app_context`; window title ignored |
| Calendar data would exist elsewhere | `Chrome` | not provided to resolver | `app_context`; calendar ignored |

Expected result: each case records selected source, confidence, and safe title in local manifest/upload metadata. Synthetic resolver checks complete within the 500 ms budget and do not require server-side provenance.

## Scenario 3 - Safe Basename

1. Generate safe basenames for titles with spaces, Cyrillic, slashes, URLs, emails, long text, and duplicates.
2. Verify every basename includes recording date/time and stable suffix.
3. Verify every basename excludes reserved filesystem characters, raw URLs, emails, credentials, and control characters.
4. Verify `manifest.json`, `mic.wav`, `incoming.wav`, local recording id, media revision id, and object keys remain unchanged.

Expected result: pass.

## Scenario 4 - Retry Idempotency

1. Resolve title/date and persist them locally before first create-meeting call.
2. Simulate a network failure after meeting creation but before upload completion.
3. Retry upload from the same queue item.
4. Verify the retry sends the same title/date metadata and does not conflict with the existing meeting.

Expected result: pass.

## Scenario 5 - Legacy Fallback

1. Seed a legacy meeting without `title` and `started_at`.
2. Open list and detail.
3. Verify the UI remains readable, shows truthful fallback title/date, and does not mutate legacy data silently.

Expected result: pass.

## Scenario 6 - Title Identity Compatibility

1. Generate a meeting title and safe basename from persisted metadata.
2. If an explicit title update path exists, apply a synthetic user-confirmed title; otherwise run the contract/model compatibility test for a future user-confirmed title.
3. Verify local recording id, media revision id, upload idempotency key, playback identity, transcript identity, outcome identity, object keys, and deletion accounting remain unchanged.

Expected result: pass.

## Focused Checks

Focused implementation checks:

```sh
swift test --package-path apps/macos --filter LocalRecordingManifestTests
swift test --package-path apps/macos --filter RecordingMetadataResolverTests
swift test --package-path apps/macos --filter DesktopUploadQueueTests
swift test --package-path apps/macos --filter DesktopUploadClientTests
swift test --package-path apps/macos --filter DiagnosticRedactionTests
cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q \
  tests/contract/test_cabinet_no_secret_content_egress.py \
  tests/integration/test_ingest_happy_path.py \
  tests/integration/test_cabinet_meeting_list.py \
  tests/unit/test_cabinet_view_models.py
```

## Implementation Evidence - 2026-06-27

Risk/validation lane: `high-risk-feature`.

Implementation branch `codex/059-recording-date-title` is based on
`origin/master` at `586691f`, including the merged 057 custody work and 058
cabinet shell work. Feature 059 stays intentionally narrow:

- no calendar lookup, matching, connector, or calendar-derived title;
- no window/browser title collection;
- no new app/window observer or permission prompt;
- no rename UI/API, download/export implementation, or storage-object rename.

Focused Swift validation:

| Command | Result |
|---------|--------|
| `swift test --package-path apps/macos --filter LocalRecordingManifestTests` | `22 tests, 0 failures` |
| `swift test --package-path apps/macos --filter RecordingMetadataResolverTests` | `6 tests, 0 failures` |
| `swift test --package-path apps/macos --filter DesktopUploadQueueTests` | `43 tests, 0 failures` |
| `swift test --package-path apps/macos --filter DesktopUploadClientTests` | `13 tests, 0 failures` |
| `swift test --package-path apps/macos --filter DiagnosticRedactionTests` | `20 tests, 0 failures` |

Focused server validation:

| Command | Result |
|---------|--------|
| `PYTHONPATH=src uv run --extra dev pytest -q tests/integration/test_ingest_happy_path.py tests/integration/test_cabinet_meeting_list.py tests/unit/test_cabinet_view_models.py tests/contract/test_cabinet_no_secret_content_egress.py::test_create_meeting_rejects_unsafe_title_without_echoing_raw_input tests/integration/test_degraded_ingest.py::test_finalize_without_required_tracks_returns_truthful_failure tests/unit/test_api_boundary_validation.py::test_rejects_oversized_and_control_character_meeting_fields` | `25 passed, 1 warning` |
| `PYTHONPATH=src uv run --extra dev ruff check src/twobrain_rec_server/cabinet/view_models.py src/twobrain_rec_server/cabinet/queries.py src/twobrain_rec_server/ingest/meetings.py tests/integration/test_ingest_happy_path.py tests/integration/test_cabinet_meeting_list.py tests/unit/test_cabinet_view_models.py tests/contract/test_cabinet_no_secret_content_egress.py` | `All checks passed!` |

Full local CI:

| Command | Result |
|---------|--------|
| `swift test --package-path apps/macos` | `653 tests, 0 failures` |
| `infra/scripts/ci-local.sh` | `ci_local_result=pass`; server tests `712 passed, 4 skipped, 103 warnings`; server lint `All checks passed!`; deployment evidence scan `pass files=7` |

Local CI also reported `rls_validation_result=blocked` because the production
RLS truth probe was not attempted from the local `postgres_test` boundary
(`reason=postgres_test_database_required`). This does not block the local CI
pass, but it must not be represented as production RLS enforcement evidence.

## Post-Merge Review Fix Evidence - 2026-06-27

Risk/validation lane: active Spec Kit slice post-merge hotfix. Full local
validation is required because the fix touches macOS metadata, server ingest,
database schema, cabinet rendering, and the public OpenAPI contract.

Post-merge findings closed:

- Unsafe legacy fallback titles no longer display raw `local_recording_id` when
  that fallback looks like an email, URL, token, or other unsafe title.
- Cabinet `title_asc` sorting now follows the visible title after safe fallback
  logic instead of the raw stored title.
- Recording date labels use the display timezone offset captured by the macOS
  app at recording start, while preserving UTC instants for storage.
- Exact idempotent retries for already-persisted legacy unsafe titles return the
  existing meeting instead of failing a duplicate upload retry.
- Swift metadata plumbing was simplified to the minimal values still needed for
  059, and diagnostics no longer expose `stableSuffix`.
- OpenAPI contract snapshot was updated for
  `recording_display_timezone_offset_minutes`.

Focused post-merge validation:

| Command | Result |
|---------|--------|
| `cd apps/server && uv run pytest tests/unit/test_cabinet_view_models.py tests/integration/test_cabinet_meeting_list.py tests/integration/test_ingest_happy_path.py tests/contract/test_cabinet_no_secret_content_egress.py tests/unit/test_api_boundary_validation.py -q` | `38 passed, 1 warning` |
| `swift test --package-path apps/macos --filter 'RecordingMetadataResolverTests|DesktopUploadClientTests|DesktopUploadQueueTests|DiagnosticRedactionTests'` | `82 tests, 0 failures` |
| `swift test --package-path apps/macos` | `653 tests, 0 failures` |
| `cd apps/server && uv run pytest tests/contract/test_openapi_contract_drift.py -q` | `5 passed, 1 warning` |
| `cd apps/server && uv run ruff check .` | `All checks passed!` |

Full post-merge local CI:

| Command | Result |
|---------|--------|
| `infra/scripts/ci-local.sh` | `ci_local_result=pass`; server tests `715 passed, 4 skipped, 103 warnings`; server lint `All checks passed!`; deployment evidence scan `pass files=7` |

Review follow-up validation:

| Command | Result |
|---------|--------|
| `cd apps/server && uv run pytest tests/integration/test_cabinet_meeting_list.py tests/unit/test_cabinet_view_models.py -q` | `22 passed, 1 warning` |
| `cd apps/server && uv run pytest tests/integration/test_ingest_happy_path.py::test_create_meeting_duplicate_rejects_mutated_recording_metadata tests/integration/test_ingest_happy_path.py::test_create_meeting_unsafe_legacy_title_retry_returns_existing_meeting -q` | `2 passed, 1 warning` |
| `cd apps/server && uv run ruff check tests/integration/test_cabinet_meeting_list.py src/twobrain_rec_server/cabinet/view_models.py` | `All checks passed!` |
| `cd apps/server && uv run ruff check src/twobrain_rec_server/ingest/meetings.py tests/integration/test_ingest_happy_path.py` | `All checks passed!` |
| `infra/scripts/ci-local.sh` | `ci_local_result=pass`; server tests `716 passed, 4 skipped, 103 warnings`; server lint `All checks passed!`; deployment evidence scan `pass files=7` |

The full CI run still reports `rls_validation_result=blocked` for the local
`postgres_test` boundary. This is unchanged from the earlier 059 validation and
must not be used as production RLS evidence.

Behavior confirmed:

- Queue metadata is resolved from manifest `startedAt`/`stoppedAt` and the
  already-approved app/platform display name when available.
- `LocalRecordingManifestService.swift` needed no runtime change because it
  already preserves canonical manifest start/stop instants; focused manifest
  and queue tests cover the 059 contract.
- Upload retries reuse the persisted recording title/date metadata instead of
  recalculating identity-changing values.
- Create-meeting payloads send persisted `title`, `started_at`, and `ended_at`.
- Server ingest rejects unsafe title-like values such as raw URLs, emails,
  tokens, and password-like strings without echoing rejected input.
- Request validation errors return metadata-only problem responses and do not
  echo raw rejected input such as control-character titles.
- Cabinet list/detail/search/sort use recording start date when present and
  truthful legacy fallbacks when it is missing.
- Recording-date sorting explicitly keeps legacy/no-date rows after dated rows
  for both newest and oldest recording-date sort orders.
- `cabinet/rendering.py` needed no runtime change because the 058 rendering
  helper already passes the view-model sort state through to the Jinja template;
  the 059 change is in query/view-model/template behavior.
- Safe filename basename is stored as metadata only and does not rename
  `manifest.json`, `mic.wav`, `incoming.wav`, local recording id, media
  revision id, upload idempotency key, or object keys.
- Diagnostics include provenance/status/length metadata and exclude raw title
  text, safe basename text, raw URLs, emails, tokens, transcript text, and
  audio content.

Before closeout/PR for implementation:

```sh
infra/scripts/ci-local.sh
```

Latest result: `ci_local_result=pass` on 2026-06-27.
