# Feature 090: current-diff metadata closeout 2026-07-20

This receipt is metadata-only. It contains no content-bearing media or
transcript/summary data, cookies, credentials, object keys, private paths, or
private media digests.

## Candidate and runtime boundary

- Current `origin/master`: `bde00e0fa7e2d7c5cb298bb3e95a0cd4be630885`.
- Runtime code release: `v2026.07.20.6` at
  `bcfba51a212bf723ed9fa86f96bbe3dcd49282fb`.
- The delta from the runtime SHA to current master is documentation-only:
  `docs/current-product-status.md`, the 090 task list, and two existing
  metadata receipts. No runtime or test source changed after the release.

## Fresh current-diff checks

- Focused disposable PostgreSQL command:
  `GRAF_TEST_WORKERS=4 bash apps/server/scripts/run_local_postgres_tests.sh
  tests/integration/test_production_smoke_boundary.py
  tests/contract/test_product_analytics_provider_smoke_output.py
  tests/unit/test_redaction.py -q` -> `26 passed, 2 warnings`.
- Deployment-evidence scan over the four 090 validation receipts:
  `deployment_evidence_scan=pass files=4`.
- Forbidden-evidence scan over the same receipts:
  `forbidden_content_scan=pass files=4`.
- `git diff --check` -> pass.

## Production residue boundary

The exact runtime release receipt records production smoke and cleanup as
`cleanup_result=pass`, `residue_records=[]`, and three synthetic objects
removed without publishing object keys. Health and readiness were green. This
is infrastructure and GRAF-controlled cleanup evidence; it does not claim the
external `test-rec` transcript/speaker/summary user path.

## Remaining boundary

The external `test-rec` user-path receipt and Chrome/embedded browser runtime
proof remain separate open gates. The deferred Codex Security scan 097 was not
run by explicit user instruction and is not represented as a pass here.
