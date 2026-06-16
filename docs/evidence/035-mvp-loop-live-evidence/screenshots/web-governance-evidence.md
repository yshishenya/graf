# Web Governance Evidence

Feature: `035-mvp-loop-live-evidence`

## Scope

This note covers owner governance states for access, share, export, deletion,
and local purge truth without performing destructive or private production
actions.

## Production Boundary

- Production route family: `https://rec.2brain.pro/meetings`
- Live owner governance proof: blocked by missing auth context in this pass.
- No production share, export, delete, retry, or local purge acknowledgement was
  performed.
- No private screenshot, account identifier, token, signed URL, or raw meeting
  data is committed.

## Fixture-Backed Coverage

Governance behavior is covered by existing local tests:

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/contract/test_access_sharing_downloads_contract.py \
  tests/contract/test_retention_deletion_contract.py \
  tests/integration/test_meeting_share_links.py \
  tests/integration/test_meeting_deletion_workflow.py \
  tests/integration/test_local_purge_coordination.py
```

The fixture-backed surface covers:

- Owner/team/shared access states.
- Share panel state and share grant boundaries.
- Artifact download/export availability and denial states.
- Deletion request lifecycle and bounded deletion report truth.
- Local purge tasks and acknowledgement boundary.

## Readiness Classification

- Local governance model: `ready` with fixture-backed tests.
- Live production governance proof: `blocked`.
- Destructive production operations: intentionally not performed in this
  validation-only slice.
