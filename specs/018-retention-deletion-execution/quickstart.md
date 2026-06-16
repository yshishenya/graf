# Quickstart: Retention And Deletion Execution

Feature: `018-retention-deletion-execution`
Date: 2026-06-16

This guide defines validation scenarios for the implementation phase. Commands
may be refined in `tasks.md` once exact test files are created.

## Prerequisites

- Current branch: `018-retention-deletion-execution`.
- Feature 017 cabinet access/share/download/export routes available.
- Local development dependencies installed for `apps/server`.
- Synthetic meeting fixtures only; do not use private meeting content in
  tracked screenshots, reports, logs, or evidence.

## 1. Contract And No-Secret Validation

Run focused contract tests:

```sh
uv run --extra dev pytest -q \
  apps/server/tests/contract/test_retention_deletion_contract.py \
  apps/server/tests/contract/test_deletion_no_secret_leakage.py
```

Expected outcome:

- deletion request/report/lifecycle schemas cover all required states;
- retention run and local purge endpoints validate request/response shapes;
- no schema exposes storage keys, signed URLs, credentials, bearer tokens,
  provider payloads, local paths, or private meeting content;
- deleting/deleted responses are bounded for unauthorized users.

## 2. Manual Deletion Workflow Validation

Run integration and unit tests:

```sh
uv run --extra dev pytest -q \
  apps/server/tests/integration/test_meeting_deletion_workflow.py \
  apps/server/tests/integration/test_deletion_lifecycle_blocks_access.py \
  apps/server/tests/unit/test_deletion_report_view_models.py \
  apps/server/tests/unit/test_deletion_audit_metadata.py
```

Expected outcome:

- owner/admin can request whole-meeting deletion with bounded confirmation;
- request and lifecycle audit are persisted before destructive actions;
- normal list/detail/share/download/export routes block original content once
  deletion starts;
- report shows controlled purge, backup expiry, dependency truth, local purge,
  and post-egress limits;
- audit write failure fails closed before destructive action.

## 3. Retention Job Validation

Run retention tests:

```sh
uv run --extra dev pytest -q \
  apps/server/tests/integration/test_retention_policy_execution.py \
  apps/server/tests/unit/test_retention_policy_snapshot.py
```

Expected outcome:

- eligible meetings create deletion requests using the same workflow model as
  manual deletion;
- not-yet-eligible, processing, already deleting, already deleted, blocked, and
  unsafe-policy meetings are skipped or blocked with safe reasons;
- policy snapshots are persisted and immutable;
- missing/unsafe policy fails closed.

## 4. Local Desktop Purge Validation

Run local purge tests:

```sh
uv run --extra dev pytest -q \
  apps/server/tests/integration/test_local_purge_coordination.py
```

If Swift client files change, also run the focused macOS test target selected in
`tasks.md`.

Expected outcome:

- purge tasks are created for relevant registered devices;
- devices see only tasks scoped to their workspace/device id;
- acknowledgement updates the report without private proof payloads;
- pending, unreachable, failed, and local-expiry-relied-upon states remain
  truthful and separate from server purge completion.

## 5. Dependency And Backup Truth Validation

Run dependency-state tests:

```sh
uv run --extra dev pytest -q \
  apps/server/tests/unit/test_dependency_deletion_states.py
```

Expected outcome:

- MediaScribe unknown/unsupported states do not become full purge claims;
- Langfuse metadata-only state is distinguished from future content-bearing
  trace deletion;
- backup pending expiry and expiry complete states are visible separately;
- downloads/exports/post-egress copies are reported as outside later 2brain Rec
  revocation.

## 6. Web UI Validation

Run web-state tests:

```sh
uv run --extra dev pytest -q \
  apps/server/tests/unit/test_cabinet_web_shell.py
```

Expected outcome:

- deletion confirmation uses bounded 2brain Rec copy;
- deleting/deleted meeting destinations show a report, not original content;
- report rows fit desktop and embedded/compact cabinet layouts;
- retryable and terminal failures are visually distinct;
- UI remains clean-room relative to Krisp references and uses 2brain Rec
  product language.

## 7. Browser Screenshot Evidence

After implementation, start the local server using the existing project run
path documented for server validation, then capture sanitized screenshots for:

- ready meeting with delete confirmation;
- deleting report with server purge in progress;
- report with backup expiry pending;
- report with local purge pending/unreachable;
- complete report with post-egress limits;
- compact embedded desktop route for the report.

Expected outcome:

- screenshots use synthetic data;
- no real emails, private transcripts, tokens, object keys, signed URLs,
  provider payloads, local paths, or dependency identifiers appear;
- interface follows the existing 2brain Rec cabinet style and does not copy
  Krisp assets, proprietary copy, or private screenshots.

## 8. Full Local Gate

Before closing implementation:

```sh
./infra/scripts/ci-local.sh
```

Expected outcome:

- lint passes;
- server tests pass;
- macOS focused tests pass if desktop files changed;
- production compose/config checks pass;
- evidence scan passes;
- no unrelated Spec Kit/local generated noise is included in the feature diff.
