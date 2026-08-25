# Infrastructure Checklist: MediaScribe v0.5.3 integration fidelity

**Purpose**: Validate MediaScribe, Postgres and Temporal safety before implementation closeout.
**Created**: 2026-08-25
**Feature**: [spec.md](../spec.md)

## Provider boundary

- [x] INF-001 The client uses only public `/v1` routes and the v0.5.3 OpenAPI result shape. Covered by the MediaScribe contract suite.
- [x] INF-002 `Retry-After`, provider `next_retry_at` and terminal error codes are mapped without fixed busy polling. Covered by recovery and Temporal focused suites.
- [x] INF-003 Provider blocks are persisted without local merge/split/resegmentation. Covered by import, cabinet and export suites.
- [x] INF-004 Source result hash changes when validated words or provider block data changes. Covered by result-import contract tests.

## Temporal and database

- [x] INF-005 Workflow replay and restart preserve deterministic commands and the same business attempt.
- [x] INF-006 Manual check and automatic timer race through one atomic schedule-generation fence.
- [x] INF-007 Nullable words storage migrates forward and old rows remain readable; deletion/result lineage remains workspace-scoped.
- [x] INF-008 Late result, deletion and stale-revision fences remain effective.

## Operations

- [x] INF-009 No credentials, signed URLs, raw audio, transcript or raw provider result enters ordinary logs, metrics, Search Attributes or committed evidence.
- [x] INF-010 Focused checks and `infra/scripts/ci-local.sh --fast` pass; production rollout is tracked as the separate release gate requested after this slice.
