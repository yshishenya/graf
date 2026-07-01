# Cleanup Safety Checklist: Code Optimization

**Purpose**: Prevent unsafe deletion and split-only cleanup
**Created**: 2026-07-01
**Feature**: [spec.md](../spec.md)

## Candidate Evidence

- [x] Cleanup requires caller/import/runtime evidence
- [x] Cleanup requires risk-surface classification
- [x] Incomplete evidence means keep or defer
- [x] Tests must not be weakened

## Product Gates

- [x] Capture gates preserved
- [x] Auth/session/device gates preserved
- [x] Privacy and deletion/retention gates preserved
- [x] MediaScribe, Langfuse, MinIO, Postgres, Temporal gates preserved
- [x] Desktop WebView/cabinet gates preserved
- [x] Deploy path preserved; no production deploy

## Ponytail Gates

- [x] No new dependencies for cleanup
- [x] No split-only PRs
- [x] First implementation batch must have runtime LOC delta <= 0
- [x] PR must report docs/spec LOC separately from runtime LOC
