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
```

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

Run the repository gate before closeout:

```sh
infra/scripts/ci-local.sh
```

Evidence must remain metadata-only. Production execution, if approved later,
uses the release CD gate and records the exact deployed SHA plus sanitized
health/log results.

## Validation evidence

Evidence from 2026-07-26:

- Focused invitation matrix: `32 passed` (contract and external invitation
  integration tests, including first entry, replay, expiry/revoke coverage and
  explicit JSON/browser response negotiation).
- Isolated existing performance check:
  `test_sc017_one_hundred_warmed_atomic_consumptions_are_within_50ms_p95` —
  `1 passed`.
- Full local CI: macOS build, 640 macOS tests and `ContractValidation` passed;
  the server parallel phase reached `2446 passed, 1 skipped` and one unrelated
  timing-sensitive SC-017 p95 assertion failed at `52.18 ms` under the full
  suite. The same test passed in isolation; no invitation test failed.
- Ruff, Python compile, production compose config and deployment-evidence scan
  passed. Standalone RLS verification reported `blocked` because it was run
  without the disposable PostgreSQL test database; the full PostgreSQL runner
  completed its RLS collection boundary before the unrelated parallel-phase
  failure.

All evidence is metadata-only. Do not include invitation tokens, email
addresses, meeting content, audio, transcripts or raw production responses.
