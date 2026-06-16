# Implementation Plan: MVP Loop Readiness

**Branch**: `034-mvp-loop-readiness` | **Date**: 2026-06-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/034-mvp-loop-readiness/spec.md`

## Summary

Create a metadata-only MVP loop readiness pass that proves, or explicitly blocks,
the owner value loop across accepted recording, upload, processing, review,
desktop embedding, access/egress, retention/deletion, production deployment,
and clean-room reference alignment. The implementation approach is an evidence
harness plus documentation/status updates: collect current facts from existing
feature evidence, runtime checks, desktop/web screenshots, production health,
and repository state; classify each loop stage; scan evidence for forbidden
content; and write an independently reviewable readiness report plus launch gap
register.

This slice may include bounded hardening only when needed to make the readiness
claim truthful, such as missing report fields, missing evidence labels, stale
status documentation, or unsafe wording. It does not add unrelated product
capabilities.

## Technical Context

**Language/Version**: Python 3.13 for server/evidence utilities; Swift 6
toolchain for macOS validation; shell for deployment/readiness scripts.

**Primary Dependencies**: FastAPI/TestClient and pytest for server validation;
Swift Package Manager tests for macOS validation; local Chrome/Playwright-style
capture where available; existing `infra/scripts/*` deployment helpers.

**Storage**: Repository evidence files under `docs/evidence/034-mvp-loop-readiness/`;
existing Postgres/MinIO/Temporal production storage is read or smoke-tested only
through established deployment scripts. No new product database tables are
required for 034.

**Testing**: `apps/server` pytest focused readiness tests, existing cabinet and
deletion tests as regressions, Swift package tests for desktop cabinet/capture
boundaries, forbidden-content scans, production health/smoke checks, and
metadata-safe screenshot review.

**Target Platform**: macOS MVP desktop app, browser/web cabinet, and current
`2brain.dev` Rec deployment.

**Project Type**: Hybrid desktop app + server-rendered web cabinet + evidence
automation.

**Performance Goals**: Readiness evidence generation completes in under 2
minutes locally when using existing artifacts and under 10 minutes when
including fresh desktop/browser screenshot captures; it must not require
private meeting playback or destructive production mutation.

**Constraints**:

- Evidence must stay metadata-only and safe to commit.
- `infra_smoke_ready` is not user rollout readiness.
- Desktop active capture authority remains native/local.
- Web/embedded surfaces own post-meeting review and governance.
- Krisp reference use is limited to clean-room IA/category learning.
- Current live private meetings must not be committed as screenshot or text
  evidence.

**Scale/Scope**: One MVP owner workspace and one current production deployment;
all accepted MVP loop stages from 007/008/010/012/013/014/015/016/017/018/020/
021/025/031/032/033 must be classified, even when the classification is blocked
or synthetic-only.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| Capture-First MVP Integrity | PASS | 034 does not change capture code. It verifies that native capture controls, visible state, and one-action stop remain outside embedded web content. |
| Visible Consent And User Control | PASS | Readiness must not accept any state where active capture is hidden or Stop is unavailable. |
| Data Boundary And Secret Discipline | PASS | Evidence is metadata-only; no raw audio, transcript text, credentials, signed URLs, private account data, or live local paths may be committed. |
| Deletion Truth And Lifecycle Accounting | PASS | Deletion/retention claims are explicitly included and must not overpromise universal erasure. |
| Spec-Driven Delivery With Testable Gates | PASS | Full Spec Kit flow is used: specify, clarify, plan, checklist, tasks, analyze, issue sync, implement, validate. |
| Product And Platform Constraints | PASS | macOS remains the MVP platform; no virtual-driver requirement is reintroduced. |
| UI Brand-Distance | PASS | Plan includes a clean-room reference comparison and forbidden Krisp-copy checks. |

No constitution violations are introduced.

## Project Structure

### Documentation (this feature)

```text
specs/034-mvp-loop-readiness/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── mvp-loop-readiness-contract.md
│   ├── readiness-evidence-schema.md
│   └── reference-comparison-contract.md
├── checklists/
│   ├── requirements.md
│   ├── ux.md
│   ├── security.md
│   ├── infra.md
│   └── launch-readiness.md
└── tasks.md

docs/evidence/034-mvp-loop-readiness/
├── README.md
├── readiness-report.json
├── readiness-report.md
├── launch-gap-register.md
└── screenshots/
```

### Source Code (repository root)

```text
apps/server/src/twobrain_rec_server/
├── cabinet/
├── deletion/
└── readiness/
    ├── __init__.py
    ├── evidence.py
    ├── matrix.py
    └── report.py

apps/server/scripts/
└── generate_mvp_loop_readiness.py

apps/server/tests/
├── contract/
│   └── test_mvp_loop_readiness_contract.py
├── integration/
│   └── test_mvp_loop_readiness_report.py
└── unit/
    └── test_mvp_loop_readiness_matrix.py

apps/macos/Shared/Tests/
├── DesktopCabinetWorkspaceTests.swift
├── DesktopCabinetRoutePolicyTests.swift
├── DesktopCabinetUploadLinkTests.swift
└── DesktopLocalPurgeTests.swift

docs/
├── current-product-status.md
└── evidence/034-mvp-loop-readiness/

infra/scripts/
├── ci-local.sh
├── cd-remote.sh
└── run-production-smoke.sh
```

**Structure Decision**: Keep 034's durable implementation in a small server-side
`readiness` package because it can validate evidence contracts without touching
production data. Use existing macOS tests and production scripts for runtime
proof instead of creating a new desktop subsystem.

## Phase 0: Research

Research resolves how to classify readiness truth, what evidence is strong
enough for launch claims, how to treat screenshots/reference comparisons, and
how to avoid private-content leakage. Output: [research.md](./research.md).

## Phase 1: Design And Contracts

- [data-model.md](./data-model.md) defines loop stages, evidence records,
  launch gaps, reference comparisons, and bounded readiness claims.
- [contracts/mvp-loop-readiness-contract.md](./contracts/mvp-loop-readiness-contract.md)
  defines the report sections and acceptance summary.
- [contracts/readiness-evidence-schema.md](./contracts/readiness-evidence-schema.md)
  defines the JSON evidence schema used by tests and docs.
- [contracts/reference-comparison-contract.md](./contracts/reference-comparison-contract.md)
  defines allowed/forbidden reference comparison content.
- [quickstart.md](./quickstart.md) defines local, desktop, web, production,
  screenshot, and forbidden-content validation scenarios.

## Post-Design Constitution Check

| Principle | Status | Evidence |
|-----------|--------|----------|
| Capture-First MVP Integrity | PASS | Contracts require native capture authority checks and do not alter capture runtime. |
| Visible Consent And User Control | PASS | Readiness cannot pass if visible active capture/Stop truth is absent from desktop evidence. |
| Data Boundary And Secret Discipline | PASS | Evidence schema has explicit forbidden-content categories and scan gates. |
| Deletion Truth And Lifecycle Accounting | PASS | Report contract includes deletion/retention/local purge/backup/dependency/post-egress states. |
| Spec-Driven Delivery With Testable Gates | PASS | Quickstart and tasks will provide independent validation by story. |
| UI Brand-Distance | PASS | Reference contract separates allowed IA lessons from forbidden Krisp copy/visuals/assets. |

No complexity waivers are required.

## Complexity Tracking

No constitution violations or extra architectural complexity are introduced.
