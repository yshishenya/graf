# Architecture Audit Quality Checklist: Deep Architecture Audit

**Purpose**: Validate that the 072 audit requirements and planning artifacts are
complete, testable, and safe before any implementation/refactor work.

**Created**: 2026-06-30

**Feature**: [spec.md](../spec.md)

## Scope And Lane

- [x] CHK-001 Risk lane is explicitly significant architecture / high-risk read-only audit.
- [x] CHK-002 Requirements forbid product/runtime code changes in stage one.
- [x] CHK-003 Requirements forbid code deletion in stage one.
- [x] CHK-004 Requirements forbid production deploy in 072.
- [x] CHK-005 072 is separated from 071 release/refactor scope.
- [x] CHK-006 Ponytail is framed as solution-shape guidance, not a lower validation lane.

## Evidence Completeness

- [x] CHK-007 Server architecture is in audit scope.
- [x] CHK-008 macOS architecture is in audit scope.
- [x] CHK-009 Infra, scripts, Docker, and production runtime dependencies are in audit scope.
- [x] CHK-010 Specs and product docs are in audit scope.
- [x] CHK-011 Python dependency/import graph evidence is required.
- [x] CHK-012 Swift package/target graph evidence is required.
- [x] CHK-013 Shell/infra entrypoint graph evidence is required.
- [x] CHK-014 Docker/runtime dependency graph evidence is required.

## Runtime Flows

- [x] CHK-015 Capture to local package flow is required.
- [x] CHK-016 Local package to upload/ingest flow is required.
- [x] CHK-017 Ingest to processing and MediaScribe flow is required.
- [x] CHK-018 Cabinet/review and desktop WebView flow is required.
- [x] CHK-019 Deletion/export/local purge flow is required.
- [x] CHK-020 Support/diagnostics flow is required.
- [x] CHK-021 Release/deploy flow is required but deploy execution is excluded.

## Boundary Coverage

- [x] CHK-022 Capture boundary is explicitly checked.
- [x] CHK-023 Auth/session/device boundary is explicitly checked.
- [x] CHK-024 Privacy and metadata-only evidence boundary is explicitly checked.
- [x] CHK-025 Deletion/retention boundary is explicitly checked.
- [x] CHK-026 MediaScribe boundary is explicitly checked.
- [x] CHK-027 Langfuse metadata boundary is explicitly checked.
- [x] CHK-028 MinIO/Postgres/Temporal boundary is explicitly checked.
- [x] CHK-029 Desktop WebView/cabinet boundary is explicitly checked.

## Finding And Roadmap Quality

- [x] CHK-030 Findings require one of `delete now`, `split soon`, `keep intentionally`, or `risky / needs spec`.
- [x] CHK-031 `delete now` requires caller/runtime/focused-validation evidence.
- [x] CHK-032 `split soon` requires a small PR boundary and validation plan.
- [x] CHK-033 `keep intentionally` requires contract evidence.
- [x] CHK-034 `risky / needs spec` requires a separate boundary/spec rationale.
- [x] CHK-035 Roadmap batches include excluded scope and pre-refactor checks.
- [x] CHK-036 Final output must answer the five plain-language audit questions.

## Safety And Hygiene

- [x] CHK-037 Evidence rules forbid secrets, raw audio, transcript text, signed URLs, and private meeting content.
- [x] CHK-038 Validation plan avoids production deploy.
- [x] CHK-039 Future refactor batches preserve focused tests and repository gates.
- [x] CHK-040 Stage-one artifacts are all under `specs/072-deep-architecture-audit/` except the managed `AGENTS.md` plan pointer.
