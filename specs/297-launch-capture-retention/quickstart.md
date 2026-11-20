# Quickstart: F297 validation

## 1. Capture continuity (Swift + hardware)

```sh
cd apps/macos
swift build
swift test --filter 'RecordingAudioTimeline|LocalRecordingWriterSystemAudio|SystemAudioCaptureService'
swift run ContractValidation
```

Expected:
- 5–20 ms and exactly 500 ms system-audio gaps bridge silence and continue.
- 500 ms–15 s gaps do not get masked; they produce a partial result or stop with preserved prefix.
- Route-change test rebases a new generation (including a different sample rate) and continues one recording.
- Gap above `maximumKnownGapSeconds` still fails closed.
- Partial continuity test uploads the prefix with `timelineMisaligned` and `partialContinuity=true`.
- Existing AEC3, pause/privacy, short-recording and queue tests stay green.

### Hardware QA matrix (metadata-only evidence)

| ID | Device / moment | Action | Expected |
|---|---|---|---|
| H1 | AirPods | Start recording, connect AirPods mid-call | One recording; both files grow; upload/transcript succeeds; non-blocking status |
| H2 | Wired headphones | Start recording, plug headphones mid-call | Same as H1 |
| H3 | Dock/display speakers | Start recording, switch default output to dock | Same as H1 |
| H4 | Any device before first system-audio packet | Start recording, change output immediately | No crash; one recording or clear partial; no silent full claim |
| H5 | Sleep/lid | Start recording, close lid, wake | Recording stops or continues honestly; prefix preserved; no false success |
| H6 | Real short call | 5–10 minute real call with one route change | One meeting; transcript covers recorded audio; partial status only if a gap > 500 ms occurred |

Do not commit raw audio, transcript text, private meeting titles or paths. Record only device class, timestamps, counts and result.

## 2. Retention scheduler (server)

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/unit/test_retention_reconciler.py \
  tests/unit/test_retention_scan.py \
  tests/integration/test_retention_deletion.py
```

Expected:
- One workspace run creates at most one deletion request per due meeting.
- Fresh/processing/deleting/policy-blocked meetings are skipped.
- A workspace failure does not stop the loop.
- `TWOBRAIN_RETENTION_SCHEDULER_ENABLED=false` stops the loop.
- Audit is metadata-only and idempotent.

## 3. Backup prune (host script)

```sh
TWOBRAIN_BACKUP_ROOT=/opt/projects/2brain-rec/backups \
  infra/scripts/prune-rec-backups.sh --dry-run --older-than-days 30
TWOBRAIN_BACKUP_ROOT=/opt/projects/2brain-rec/backups \
  infra/scripts/prune-rec-backups.sh --execute --older-than-days 30
```

Expected:
- Dry-run prints candidates and changes nothing; exit `0` even with no candidates.
- Execute removes only exact `YYYYMMDDTHHMMSSZ` directories older than 30 days directly under `TWOBRAIN_BACKUP_ROOT`.
- Symlinks, foreign directories, the newest directory and files outside the root are skipped.
- Invalid root/arguments exit `2`; partial deletion failure exits `3`.
- Disable by stopping `graf-rec-backup-prune.timer`; rollback restores from the newest verified backup.

## 4. Public copy and referral

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/contract/test_billing_clarity.py \
  tests/contract/test_billing_purchase_ui.py \
  tests/unit/test_referral_landing.py
```

Live checks:

```sh
curl -sS -o /dev/null -w '%{http_code}\n' https://rec.2brain.pro/r/unknown-token
curl -sS -o /dev/null -w '%{http_code}\n' https://rec.2brain.pro/referral/unknown-token
curl -sS https://rec.2brain.pro/offer | grep -i '4 час'
curl -sS https://rec.2brain.pro/ | grep -i '4 час'
```

Expected:
- Referral routes return 410 for unknown tokens, 503 for unavailable DB, never 500.
- Offer/landing show the 4-hour limit.
- Checkout renders one checked `recurring_consent` that can be unchecked; CSRF/auth/routes unchanged.
- Offer says auto-renewal is checked by default and can be removed before payment.

On the Dev stand, sign in as `local@graf.test` with the local code `000000` before opening `/billing/checkout`; an anonymous request redirects to `/login`. Check the DB-unavailable 503 only in a coordinated stand window.

## 5. Final gates

```sh
python3 scripts/validate-changelog-fragments.py
git diff --check
infra/scripts/ci-local.sh --fast
```

Then exact-SHA PR checks (`governance-fast`, `macos-pr`, `pr-metadata`) and one `release-full` on the frozen candidate before release. Production retention/prune enablement is a separate operator action.
