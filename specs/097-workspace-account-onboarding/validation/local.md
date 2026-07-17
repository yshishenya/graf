# Local validation: Workspace Account Onboarding

## Validation lane

Feature 097 is a high-risk auth, privacy, PostgreSQL migration, RLS and
user-facing onboarding slice. The receipts below are metadata-only: no real
account, invitation, credential, recording or transcript data was used.

## Focused quickstart receipts

| Area | Command/result | Evidence |
| --- | --- | --- |
| Onboarding migration downgrade | `run_local_postgres_tests.sh --focused -q tests/integration/test_postgres_migrations.py -k workspace_onboarding_migration_downgrades_cleanly` | 1 passed, 9 deselected, 2 warnings, 1.50 s |
| Worker schema-head compatibility | `run_local_postgres_tests.sh --focused -q tests/unit/test_playback_normalization_worker.py -k schema_startup_gate_requires_exact_migration_head or worker_schema_head_is_derived_from_packaged_migrations` | 2 passed, 8 deselected, 2 warnings, 0.17 s |
| Feature 097 focused regression group | PostgreSQL runner with the onboarding, auth, tenant, RLS, migration, admin and OpenAPI selections | 139 passed; the RLS subset passed 22 tests; no failures |
| Email personal-space fallback | Focused browser login regression | 2 passed |
| macOS workspace selector | `swift test --filter DesktopCabinetWorkspaceTests` | 30 passed |
| macOS package gate | Existing closeout run on the same implementation branch | 572 Swift tests, build and `ContractValidation` passed |

The focused runs emitted only existing pytest plugin/import and Starlette
`httpx` deprecation warnings. They did not emit secrets or private content.

## Accelerated full PostgreSQL gate

The Feature 110 runner was used without the old serial path:

```sh
GRAF_TEST_WORKERS=4 bash apps/server/scripts/run_local_postgres_tests.sh --full -q
```

Result:

- collection: 1,866 node IDs;
- collection digest: `ba3803734dcdf3a2effa5feacb81b9f623c076f887c784d87bbc6d4784853735`;
- parallel phase: 1,830 passed, 1 skipped, 10 warnings in 245.94 s;
- strict RLS phase: 34 passed, 1 skipped, 2 warnings in 7.21 s;
- final runner result: `pass`;
- disposable PostgreSQL container: removed by the runner.

Eight workers were also exercised on this expanded 097 collection. That mode
completed 1,351 tests before the disposable PostgreSQL server stopped accepting
connections, producing 479 setup errors. This is a local resource-saturation
limit, not a product assertion failure. Four workers are the stable closeout
setting for this 1,866-node collection on the current 8 GB Docker allocation;
the runner still accepts an explicit bounded `GRAF_TEST_WORKERS` override.

The six-worker repetition was intentionally stopped after the user asked to
stop repeating full tests; it is not represented as a result.

## Canonical CI boundary

The Feature 110 branch has a recorded `infra/scripts/ci-local.sh` pass for its
1,827-node baseline. In this continuation, the expanded 097 server gate above
was run directly with the stable worker setting; the complete canonical
`ci-local.sh` command was not repeated after the user stopped additional full
test cycles. Therefore this file does not claim a new `ci_local_result=pass`
for the 1,866-node collection.

