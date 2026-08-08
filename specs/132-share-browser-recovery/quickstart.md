# Quickstart: browser invitation error responses

## Prerequisites

- Run from the repository root.
- Use the existing local PostgreSQL test runner; no new service or migration is
  required.

## Focused validation

```sh
GRAF_TEST_WORKERS=1 bash apps/server/scripts/run_local_postgres_tests.sh -q \
  tests/contract/test_browser_problem_responses.py \
  tests/contract/test_recording_share_invitation_contract.py \
  tests/contract/test_recording_share_ui_contract.py \
  tests/integration/test_recording_share_public_link.py
```

The runner changes into `apps/server`, so pytest paths above are relative to
that directory.

The focused matrix must prove:

1. valid first entry still returns the existing allowed result;
2. replayed, expired, revoked and recipient-mismatch browser paths return
   HTML without raw secret or meeting content;
3. explicit JSON callers retain Problem Details JSON;
4. missing or generic `Accept` on browser invitation paths does not produce a
   downloadable JSON response;
5. replay does not create a session, grant, membership or expanded access.

## Static checks

```sh
git diff --check
python3 -m compileall -q apps/server/src apps/server/tests
```

Run the repository gate before implementation closeout:

```sh
infra/scripts/ci-local.sh
```

Evidence must remain metadata-only. An approved production release uses the
release CD gate and records the exact deployed SHA plus sanitized health/log
results.

## Validation evidence

Evidence from 2026-07-26/27:

- Focused invitation matrix: `32 passed, 2 warnings` in 53.62 seconds;
  coverage includes first entry, replay, expiry/revoke, explicit JSON and
  browser response negotiation, plus the calendar-context regression.
- `git diff --check`, Python compile and targeted Ruff all passed.
- Full local CI on release SHA `8b0ba4df`: macOS build and `642` macOS tests
  passed; server phase reached `2456 passed, 1 skipped`; strict RLS reached
  `42 passed, 1 skipped`; lint, compile, compose and evidence scans passed.
- Ponytail review completed: the fix reuses the existing proof and access
  decision path, adds no dependency or abstraction, and keeps the regression
  setup minimal.
- Implementation PR `#4675` and release PR `#4676` were merged. Release
  `v2026.07.26.11` passed Developer ID signing, notarization, stapling,
  Gatekeeper, Sparkle continuity and public HTTPS asset/hash checks.
- Production deploy completed through the release CD gate at SHA
  `8b0ba4df`. Backup/restore rehearsal, migration, RLS, worker readiness,
  smoke, cleanup and automatic dispatch all passed. The post-deploy API
  health check passed; the last 15-minute aggregate contained zero
  tracebacks, 5xx responses, `meeting_not_found` responses or error lines.

All evidence is metadata-only. Do not include invitation tokens, email
addresses, meeting content, audio, transcripts or raw production responses.

## Closeout references

- Tasks: `T001–T010` complete; corresponding GitHub issues `#4659–#4668`
  reconciled with implementation and release evidence.
- Implementation: PR `#4675`, merge SHA `aabda3af`.
- Release/deploy: PR `#4676`, tag `v2026.07.26.11`, production SHA
  `8b0ba4df`.
