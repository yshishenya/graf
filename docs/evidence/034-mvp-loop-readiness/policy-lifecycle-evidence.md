# Policy And Lifecycle Evidence

Feature: `034-mvp-loop-readiness`

Status: `metadata_safe_fixture_evidence`

## Safe Evidence

- Command: `uv run --extra dev pytest -q tests/contract/test_access_sharing_downloads_contract.py tests/contract/test_retention_deletion_contract.py tests/unit/test_deletion_report_view_models.py tests/integration/test_local_purge_coordination.py`
- Scope: verifies login-required sharing, bounded download/export actions, deletion report partitioning, dependency truth, post-egress limits, backup expiry, and metadata-only desktop local purge acknowledgements.
- Boundary: fixture data only; no destructive production deletion or private artifact purge is performed.

## Truth Boundaries

- Deletion copy is bounded to artifacts 2brain Rec controls.
- MediaScribe, Langfuse, workflow/temp payloads, diagnostics, backups, local buffers, and post-egress copies are represented separately.
- Desktop local purge acknowledgements accept metadata-only states and reject private local path payloads.

## Forbidden Content Boundary

This note contains no raw audio, transcript from private meetings, private email, signed URL, token, local user path, or private Krisp screenshot.
