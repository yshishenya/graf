# Specification Analysis Report: Dual Audio Formats

**Date**: 2026-06-28

## Findings

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| A1 | Process | LOW | tasks.md, tracker-policy.md | GitHub issue sync is still a PR-closeout step if this slice is externally tracked. It is not a local artifact blocker. | Before PR closeout, run issue sync or record why no external tracker issue is needed for this remediation. |

## Coverage Summary

| Requirement Key | Has Task? | Task IDs | Notes |
|-----------------|-----------|----------|-------|
| FR-001..FR-004 | Yes | T007-T010 | Preserves WAV transcription source and meeting/media identity. |
| FR-005..FR-008 | Yes | T009-T014 | Creates and validates optional playback derivative. |
| FR-009..FR-011 | Yes | T015-T017 | Separates playback from download/export and hides format choice from users. |
| FR-012..FR-014 | Yes | T018-T024 | Covers lifecycle, fallback, retention/deletion, and validation evidence. |
| FR-015..FR-017 | Yes | T015-T024 | Preserves server-owned STT boundary, egress safety, and fail-closed access. |
| FR-018..FR-019 | Yes | T012, T020-T024 | Covers retry/no-duplicate behavior and release copy. |
| SC-001 | Yes | T009-T010, T023 | WAV pair remains transcription input. |
| SC-002..SC-004 | Yes | T009-T014, T023 | M4A generation and review validation are covered by quickstart. |
| SC-005 | Yes | T015-T017, T023 | Download/export policy and response metadata are covered. |
| SC-006..SC-008 | Yes | T012, T018-T024 | Lifecycle, metadata safety, and duplicate prevention are covered. |

## Constitution Alignment Issues

None blocking.

## Unmapped Tasks

None. T021-T024 are validation/closeout tasks required by the selected
high-risk lane.

## Metrics

- Total functional requirements: 19
- Total success criteria: 8
- Total tasks: 24
- Requirement coverage: 100%
- Ambiguity count: 0 blocking
- Duplication count: 0 blocking
- Critical issues count: 0

## Next Actions

- Decide whether to sync GitHub issues before PR closeout; avoid duplicate
  issues for already-remediated local review tasks.

## Validation Evidence

- `swift test --package-path apps/macos --filter SystemAudioRecordingPackageTests`: pass, 7 tests.
- `swift test --package-path apps/macos --filter DesktopUploadClientTests`: pass, 27 tests.
- `swift test --package-path apps/macos --filter DesktopUploadQueueTests`: pass, 52 tests.
- `cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/contract/test_cabinet_playback_contract.py`: pass, 5 tests.
- `cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/integration/test_cabinet_playback_route.py`: pass, 12 tests.
- `cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/integration/test_artifact_egress_policy.py`: pass, 9 tests.
- `cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/unit/test_minio_async_wrappers.py`: pass, 3 tests.
- `cd apps/server && uv run pytest tests/integration/test_persistent_ingest_storage.py::test_legacy_empty_expected_roles_rehydrate_to_required_upload_roles`: pass, 1 test.
- `.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks`: pass.
- `infra/scripts/ci-local.sh`: pass; server tests, lint, Python compile, RLS boundary check, production compose config, and deployment evidence scan completed. RLS production truth remains blocked by the expected local `postgres_test_database_required` boundary.
