# Quickstart: F296

**Feature**: `296-server-cache-proof`

## Prerequisites

- macOS 14+, Swift 6.0.3.
- Python 3.13 with `apps/server/.venv` and dev extras.
- `git switch 296-server-cache-proof`.
- A synthetic queue fixture or a copy of a real `upload-queue.json`; never run destructive scenarios against the only production copy.
- Server contract deployed locally or in a staging environment for the live dry-run scenario.

## Build and focused tests

```sh
swift build --package-path apps/macos
swift test --package-path apps/macos --filter LocalCacheEligibility
swift test --package-path apps/macos --filter LocalCacheEvictionDryRun
swift test --package-path apps/macos --filter LocalCacheCleanup
swift test --package-path apps/macos --filter LocalCacheEvictionScheduler
swift test --package-path apps/macos --filter DesktopUploadClient
swift run --package-path apps/macos ContractValidation
```

Server:

```sh
cd apps/server
PYTHONPATH=src .venv/bin/python -m pytest -q \
  tests/contract/test_recording_sync_contract.py \
  tests/contract/test_desktop_status_contract.py \
  tests/contract/test_recording_sync_no_secret_egress.py \
  tests/contract/test_desktop_playback_proof_contract.py \
  tests/contract/test_desktop_retention_projection_contract.py \
  tests/contract/test_desktop_storage_status_contract.py \
  tests/integration/test_desktop_sync_custody_fields.py
```

## Scenario 1 — pre-contract payload keeps everything

1. Use a sync-state fixture without `playback`, `archive_audio`, `finalized_at`, or `retention`.
2. Run the dry run on a fixture with 35 uploaded, 37 terminal_deleted, 2 blocked, 10 deletion operations.
3. Expected: `eligible=0`; every uploaded item is `keep` with the applicable fail-closed reason; zero bytes deleted; queue and recordings tree unchanged.

## Scenario 2 — full proof authorizes only the correct revision

1. Seed a ready canonical playback artifact, `archive_audio=true`, a finalized session, safe retention, owner access, no conflict/deletion.
2. Run the dry run. Expected: the item is `potentially_eligible`; `playback.media_revision_id` equals `localMediaRevisionId`.
3. Change the playback revision to an older pinned revision and rerun. Expected: `revision_mismatch`, `keep`.

## Scenario 3 — object verification fails closed

1. Remove the canonical object; rerun. Expected: `playback_not_verified` / `canonical_artifact_missing`, `keep`.
2. Replace it with different-length bytes; rerun. Expected: `keep`.
3. Make the storage stat raise/timeout or the bounded read fail; rerun. Expected: `keep`.

## Scenario 4 — archive/retention/deletion gates

1. Finalize with `archive_audio=false`; expected `archive_audio_false`, `keep`.
2. Set retention `unsafe`/expired/too close; expected `keep`.
3. Open a deletion operation or pending local purge; expected `keep`.
4. Switch account/workspace mid-run; expected the run aborts and writes no partial eligibility.

## Scenario 5 — manual cleanup preserves playback

1. Use a fully proven item with `meeting-transcription.wav`, `meeting-review.m4a`, and `manifest.json`.
2. Confirm cleanup.
3. Expected: only the WAV is gone; review and manifest remain; local playback works; queue row and `finalizedAt` unchanged; receipt written.
4. Repeat cleanup. Expected: no-op, no duplicate receipt.
5. Simulate a crash after unlink but before the completed receipt; rerun. Expected: pending intent becomes `completed`/`noop`, no second deletion and no duplicate receipt.

## Scenario 6 — automatic eviction and kill switch

1. Set the cache above warning with several proven items; run the scheduler.
2. Expected: oldest WAVs evicted until under warning; review/manifest remain; receipts written.
3. Disable the kill switch; add new eligible items; run again. Expected: zero files deleted.
4. Inject a missing/stale proof, archive false, deletion open, account mismatch; expected: zero files deleted for those items.

## Scenario 7 — no-mutation proof

Before/after the dry run, compare:

- `upload-queue.json` SHA256, size, mtime;
- recursive recordings tree: relative path, size, SHA256, mtime;
- absence of quarantine directories;
- queue schema version unchanged;
- upload states, retry deadlines, `serverTruth`, `finalizedAt` unchanged.

Only the report file under `<queue dir>/LocalCacheEviction/` may appear or change.

## Release gate

```sh
python3 scripts/validate-changelog-fragments.py
infra/scripts/ci-local.sh --fast   # diagnostic only
```

Then the required GitHub checks on the exact PR SHA, one `release-full`, Developer ID/notarization/staple/Gatekeeper/Sparkle/live appcast, `cd-remote.sh --dry-run`, production deploy, health/runtime SHA, and `validation.md` evidence.

## Rollback

- Phase A/B: disable the cleanup action and auto-eviction kill switch; existing files stay.
- Phase C: turn the kill switch off and redeploy; evicted WAVs are not restored, but the server copy and local review audio remain.
- Never roll back by deleting receipts or queue rows.
