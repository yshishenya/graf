# Evidence: 018 Retention And Deletion Execution

Date: 2026-06-16

Feature: `018-retention-deletion-execution`

This evidence index is intentionally metadata-only. Do not add real meeting
audio, transcript text, summary text, object storage keys, signed URLs,
provider payloads, dependency job identifiers, local filesystem paths, bearer
tokens, credentials, or private desktop proof payloads.

## Scope

- Whole-meeting deletion request lifecycle.
- Immediate access blocking for deleting/deleted meetings.
- Metadata-only deletion verification reports.
- Retention policy snapshot and scan behavior.
- Device-scoped local desktop purge tasks and acknowledgements.
- Backup expiry, dependency, diagnostics, workflow/temp, and post-egress copy
  truth.
- Lifecycle activity and safe retry guidance.

## Validation Log

### Quickstart Focused Gates

Contract and no-secret validation:

```sh
cd apps/server
uv run --extra dev pytest -q \
  tests/contract/test_retention_deletion_contract.py \
  tests/contract/test_deletion_no_secret_leakage.py
```

Result: `8 passed`.

Manual deletion workflow validation:

```sh
cd apps/server
uv run --extra dev pytest -q \
  tests/integration/test_meeting_deletion_workflow.py \
  tests/integration/test_deletion_lifecycle_blocks_access.py \
  tests/unit/test_deletion_report_view_models.py \
  tests/unit/test_deletion_audit_metadata.py
```

Result: `13 passed`.

Retention job validation:

```sh
cd apps/server
uv run --extra dev pytest -q \
  tests/integration/test_retention_policy_execution.py \
  tests/unit/test_retention_policy_snapshot.py
```

Result: `4 passed`.

Local purge, dependency, and web-shell validation:

```sh
cd apps/server
uv run --extra dev pytest -q \
  tests/integration/test_local_purge_coordination.py \
  tests/unit/test_dependency_deletion_states.py \
  tests/unit/test_cabinet_web_shell.py
```

Result: `7 passed`.

### Focused US1-US5 Regression

Command:

```sh
cd apps/server
uv run --extra dev pytest -q \
  tests/contract/test_deletion_no_secret_leakage.py \
  tests/contract/test_retention_deletion_contract.py \
  tests/integration/test_retention_deletion_migrations.py \
  tests/integration/test_meeting_deletion_workflow.py \
  tests/integration/test_deletion_lifecycle_blocks_access.py \
  tests/integration/test_retention_policy_execution.py \
  tests/integration/test_local_purge_coordination.py \
  tests/unit/test_deletion_audit_metadata.py \
  tests/unit/test_deletion_report_view_models.py \
  tests/unit/test_dependency_deletion_states.py \
  tests/unit/test_retention_policy_snapshot.py \
  tests/unit/test_cabinet_web_shell.py \
  tests/contract/test_rls_table_inventory_contract.py \
  tests/integration/test_postgres_migrations.py
```

Result: `43 passed`.

### macOS Local Purge Client

Command:

```sh
swift test --package-path apps/macos --filter DesktopLocalPurgeTests
```

Result: `3 tests, 0 failures`.

### Browser Screenshot Validation

Synthetic HTML was generated with `render_deletion_report_page()` and contains
only synthetic labels, lifecycle states, and safe reason codes.

Artifacts:

- `docs/evidence/018-retention-deletion-execution/screenshots/deletion-report-synthetic.html`
- `docs/evidence/018-retention-deletion-execution/screenshots/deletion-report-embedded-synthetic.html`
- `docs/evidence/018-retention-deletion-execution/screenshots/deletion-report-desktop.png`
- `docs/evidence/018-retention-deletion-execution/screenshots/deletion-report-embedded-compact.png`

Result: Playwright with local Chrome captured desktop and compact embedded
deletion report screenshots. PNG sizes were `142707` and `115843` bytes. DOM
sanity confirmed all required report sections, `bodyOverflow=0`, no offscreen
elements, visible report content, `2brain Rec` product copy, and no `Krisp`
brand text in the rendered page.

### Full Local Gate

Command:

```sh
./infra/scripts/ci-local.sh
```

Result: `ci_local_result=pass`.

Notes:

- Server tests: `411 passed, 4 skipped`.
- Server lint: `All checks passed!`.
- Python compile: passed.
- RLS hardening validation boundary: blocked without a Postgres test URL as
  expected, with `ready_for_production_truth=false`.
- Production compose config: rendered successfully with secret placeholders and
  secret-file references.
- Deployment evidence scan: `deployment_evidence_scan=pass`.

### Evidence Review

Command:

```sh
rg -n -i "(/Users/|bearer|secret|password|token|signed_url|presigned|object_key|storage_object_key|transcript text|raw audio|provider payload|credential|api[_-]?key|mediascribe_job|external_job_id)" docs/evidence/018-retention-deletion-execution specs/018-retention-deletion-execution/tasks.md
```

Result: No evidence artifact contained actual local paths, credentials, signed
URLs, object keys, provider payloads, raw audio, transcript text, or dependency
job identifiers. Matches were limited to this README's policy/disclaimer text,
task descriptions, and no-secret test names.
