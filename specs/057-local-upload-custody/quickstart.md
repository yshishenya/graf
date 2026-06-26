# Quickstart: Local Upload Custody

Date: 2026-06-26

## Purpose

Validate that local recordings are treated as product custody, not as a user
managed upload queue:

1. valid local recordings are preserved;
2. upload retries automatically when possible;
3. normal users see only real actions;
4. server-known meetings stay in the server-owned list;
5. server-unknown recordings stay native aggregate custody only;
6. purge/deletion truth is not overclaimed;
7. feature `057` does not touch server cabinet presentation owned by `058`.

## Prerequisites

- macOS development environment with Swift toolchain.
- Server Python environment through `uv`.
- Docker available for full local CI.
- Synthetic recordings only for automated tests and committed evidence.
- No real credentials, raw audio, transcript text, private paths, signed URLs,
  or private meeting content in evidence.
- 057 validation evidence lives under
  `specs/057-local-upload-custody/validation/` and must be metadata-only.

## Focused Desktop Validation

After implementation tasks add/update the required tests, run:

```sh
swift test --package-path apps/macos --disable-swift-testing \
  --filter 'DesktopUploadQueue|DesktopUploadClient|DesktopLocalPurge|CaptureControl|DesktopCabinet'
```

Expected:

- queue v2 preserves local identity, server ids, accepted ranges, retry records,
  and retention decisions;
- malformed queue state becomes metadata-safe blocked custody truth;
- local custody ledger, quarantine copy, manifest, and audio artifacts are
  written with complete file protection and user-only permissions;
- automatic retry states have no normal-user Retry or Stop retry controls;
- auth/workspace/permission states expose only meaningful user actions;
- local purge acknowledgement happens only after verified local deletion,
  tombstone, or cryptographic unrecoverability;
- right/control surface exposes compact aggregate custody, not a second meeting
  list.

## Focused Server Contract Validation

After implementation tasks add/update the required tests, run:

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/contract/test_desktop_status_contract.py \
  tests/contract/test_ingest_openapi_contract.py \
  tests/integration/test_ingest_failure_truth.py \
  tests/integration/test_local_purge_coordination.py \
  tests/unit/test_ingest_state_machine.py
```

Expected:

- `404 recording_not_found` remains server-unknown local custody, not terminal
  loss;
- sync-state and problem responses expose stable custody owner/action/retry-class
  fields or the agreed nested equivalent;
- server list/detail API read models expose explicit structured custody fields
  for 058 and do not use `status_label`, `status_reason`, or `primary_action` as
  the 057/058 machine contract;
- problem responses use stable `Problem.code` classes;
- legacy action names such as `manual_review`, `stop_upload`, `retry_later`,
  `retry_future`, and `open_desktop_queue` do not reach the 057/058 contract;
- local purge ack rejects or reports unverifiable completion safely;
- no server cabinet presentation file is required to pass these tests.

## 057/058 Boundary Guard

Before closing implementation, verify no 057 task modified server cabinet
presentation files:

```sh
git diff --name-only | rg '^apps/server/src/twobrain_rec_server/cabinet/(web\\.py|templates/|static/|.*\\.css$)'
```

Expected:

- no output for 057-owned work, unless the user explicitly created a separate
  server-web slice.

## Manual Scenario 1: Offline Recording Is Preserved

1. Disable network.
2. Record and stop a short synthetic meeting.
3. Quit and relaunch the desktop app.
4. Open the meeting workspace and right/control surface.

Expected:

- local custody says the recording is saved on this Mac;
- no Retry task is shown;
- no fake row is injected into the server WebView list;
- sending resumes automatically after network recovery.

## Manual Scenario 2: Auth Expiry Needs Sign-In Only

1. Create or keep a local custody item.
2. Expire or remove desktop auth.
3. Open the app.
4. Sign in through the WebView.

Expected:

- local custody remains preserved;
- primary action is sign-in, not Retry;
- after sign-in, upload resumes without pressing a manual retry button.

## Manual Scenario 3: Server Unknown Reconciles Safely

1. Use a local item whose sync-state returns `404 recording_not_found`.
2. Keep the app open until registration is allowed.

Expected:

- the item remains server-unknown local custody before registration;
- no server review route is opened;
- when registration succeeds, the server read model owns the meeting identity;
- native UI does not duplicate the server row.

## Manual Scenario 4: Partial Upload Survives Restart

1. Start upload with a large synthetic recording.
2. Interrupt network after at least one accepted range.
3. Quit and relaunch the app.
4. Restore network.

Expected:

- accepted server ranges are reused;
- upload does not start a duplicate meeting/session/job;
- progress remains aggregate native custody until server review is available;
- WebView route is not force-refreshed while the user is reviewing another
  route.

## Manual Scenario 4b: Server Truth Survives Response Loss

1. Use synthetic fixtures to simulate successful server registration followed by
   lost desktop persistence of the response.
2. Repeat for upload-session creation and finalize-response loss.
3. Relaunch the desktop app and run custody processing.

Expected:

- server meeting id, upload session id, accepted ranges, and finalize truth are
  reconciled before new upload or terminal decisions;
- no duplicate meeting, upload session, or processing job is created;
- the native surface remains aggregate custody and does not fabricate review
  availability.

## Manual Scenario 4c: Malformed Local Ledger Is Not Loss

1. Replace the synthetic upload queue JSON with invalid JSON.
2. Relaunch the app and run custody processing.

Expected:

- the malformed document is copied to protected local quarantine;
- the active ledger is recreated with metadata-only blocked custody truth;
- no existing recording artifact is deleted;
- UI/log/evidence do not expose private local paths.

## Manual Scenario 5: Purge Truth

1. Create a server local-purge task for a synthetic local recording.
2. Run desktop custody processing.
3. Test success and failure cases.

Expected:

- success ack happens only after verified local deletion, tombstone, or
  cryptographic unrecoverability;
- failure/unverified cases report safe failure;
- no raw proof payload or private local path is sent.

## Forbidden Content Scan

Run before closeout:

```sh
rg -n --hidden --glob '!*.wav' --glob '!*.m4a' --glob '!*.mp3' \
  'Bearer |BEGIN (RSA |OPENSSH |EC |DSA )?PRIVATE KEY|signed_url|X-Amz-|/Users/|/private/|transcript text|raw audio' \
  specs/057-local-upload-custody/validation specs/057-local-upload-custody
```

Expected:

- no committed raw audio, transcript text, credentials, tokens, cookies, signed
  URLs, private local paths, or private meeting content;
- matches in requirement text are reviewed as policy wording, not evidence
  leakage.

## Full Local Gate

Run after focused validation passes:

```sh
infra/scripts/ci-local.sh
```

Expected:

- macOS tests pass;
- server tests and lint pass;
- compose/config checks pass;
- no forbidden content appears in committed docs/evidence.
