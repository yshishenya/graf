# Implementation Plan: Support Incident Reporting

**Branch**: `codex/061-support-incident-reporting` | **Date**: 2026-06-26 | **Spec**: [spec.md](/Users/yshishenya/.codex/worktrees/503d/crisp/specs/061-support-incident-reporting/spec.md)

**Input**: Feature specification from `/Users/yshishenya/.codex/worktrees/503d/crisp/specs/061-support-incident-reporting/spec.md`

**Note**: This plan is produced by `$speckit-plan` for the high-risk privacy,
diagnostics, backend, and native UX feature slice.

## Summary

Add a native `Отправить отчет` support action for local upload custody blockers
and make the server the only component that can create or update the required
private GitHub issue. The desktop app sends a metadata-only support incident
report to `POST /api/v1/desktop/support-incidents`; the backend validates and
redacts the allowlisted payload again, persists an aggregate incident, dedupes
by safe root-cause key, rate-limits repeated submissions, confirms the target
repo is the private `yshishenya/crisp` repo, and creates or updates a canonical
GitHub issue. The desktop shows `CUST-{github_issue_number}` only after that
issue exists; offline, backend, GitHub, or configuration failures show the copy
fallback. This slice stays outside `cabinet/web.py` and does not change the
server-owned WebView meeting list.

## Technical Context

**Language/Version**: Python >=3.13 for `apps/server`; Swift 6 / macOS 14+
SwiftPM package for `apps/macos`

**Primary Dependencies**: FastAPI, Pydantic v2, SQLAlchemy asyncio, Alembic,
httpx, structlog; SwiftUI/AppKit/Foundation/CryptoKit; GitHub REST API for
server-side issue creation/update

**Storage**: Postgres via SQLAlchemy/Alembic for persisted support incidents,
dedupe keys, issue linkage, durable rate-limit buckets, and bounded safe
identity lists; existing local desktop upload ledger/queue for report action
state and restart persistence

**Testing**: `pytest` / `pytest-asyncio` for server unit, contract, and
integration coverage; `swift test --package-path apps/macos` for native custody
projection/action state coverage; `infra/scripts/ci-local.sh` as the repository
gate before implementation closeout

**Risk / Validation Lane**: `high-risk-feature` because the slice touches
privacy diagnostics, backend API/storage, external GitHub integration, support
workflow, native user-visible degraded states, redaction, and rate limiting

**Release Gate**: No deployment in this planning slice. Implementation must
complete focused server/macOS tests and `infra/scripts/ci-local.sh`; production
deploy or smoke is a separate explicit release gate.

**Target Platform**: Docker-hosted FastAPI backend for 2brain Rec plus native
macOS app custody UI

**Project Type**: Backend API/service + persistent model/migration + native
desktop UX/action state

**Performance Goals**: User send action reaches success or fallback in under
5 seconds for offline/backend/GitHub unavailable cases; server-side GitHub
requests use bounded timeouts within that user-visible window; duplicate groups
update one incident without unbounded issue creation; GitHub issue body
generation is deterministic for safe diffing and dedupe

**Constraints**: No audio, transcript text, raw local paths, credentials,
tokens, signed URLs, private meeting content, human names, email addresses,
account labels, or unsafe human-identifying values in payloads, storage, logs,
tests, screenshots, issue bodies, comments, support exports, or evidence.
Desktop never talks to GitHub directly. Success requires a private GitHub issue
in `yshishenya/crisp`. Missing labels, public repo, wrong repo, GitHub outage,
or unsafe payload means fallback copy from the user's perspective. The server
must not trust desktop redaction and must not mutate `cabinet/web.py` or the
server-owned WebView meeting list.

**Scale/Scope**: Custody/support incidents for local upload blockers introduced
by feature 057. Aggregate incidents keep `affected_count` and at most 5 safe
affected identities in generated issue content while storing only redacted
metadata. Labels are bounded and pre-managed; no dynamic problem-code labels.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Rationale |
|------|--------|-----------|
| Capture-first MVP integrity | PASS | This feature reports custody blockers and does not alter capture, drivers, routing, or recording fidelity. |
| Visible consent and user control | PASS | The feature adds support action state to an already visible native custody surface and does not hide active capture or remove one-action control. |
| Data boundary and secret discipline | PASS | Desktop sends metadata-only reports to 2brain Rec backend; backend creates private GitHub issues server-side only after redaction and repo privacy checks. No secrets or content are allowed in diagnostics. |
| Deletion truth and lifecycle accounting | PASS | Copy and issue content must not promise recording recovery or universal erasure; report fields include retention/local media/server-copy truth when safe. |
| Spec-driven delivery with testable gates | PASS | This is a high-risk feature and has completed specify + clarify before this plan. Checklist, tasks, analyze, task-to-issues, and implement remain required before code changes. |
| UX, accessibility, localization, brand distance | PASS | Required copy is Russian, human-readable, avoids internal enum codes as the primary explanation, and includes accessible names plus keyboard/focus reachability for native report controls. |
| Deployment validation discipline | PASS | No deploy is performed in planning. Implementation requires focused tests plus local CI before PR/closeout. |

**Post-design re-check**: PASS on 2026-06-26. Phase 0/1 artifacts preserve the
same boundaries: metadata-only reports, server-side redaction, private
server-side GitHub issue creation, no direct desktop tracker access, no WebView
meeting-list change, and focused high-risk validation before implementation.

## Validation Plan

Focused implementation validation will cover:

- Server redaction/allowlist tests for forbidden content, deterministic JSON,
  required safe fields, and `redaction_state=metadata_only`.
- Server contract tests for `POST /api/v1/desktop/support-incidents`, success
  response, failure `Problem` responses, idempotency, and copy fallback signals.
- Server integration tests with a fake GitHub client for created, updated,
  durable rate-limit bucket, missing-label, wrong/public-repo, and
  GitHub-unavailable cases.
- Backend migration/model tests that prove support incidents persist with
  workspace/device/user scope, dedupe key, affected count, bounded safe identity
  list, and GitHub issue linkage.
- macOS focused tests for report construction, action availability, success
  state persistence, failure fallback, copy fallback, aggregate count, and
  user-facing Russian copy.
- macOS accessibility checks for report action accessible names,
  keyboard/focus reachability, and non-overlapping status text in the native
  custody surface.
- A regression assertion that the server-owned WebView meeting list remains out
  of scope and does not gain native local-record rows from this feature.

Required closeout commands for implementation:

```sh
cd /Users/yshishenya/.codex/worktrees/503d/crisp
uv --directory apps/server run pytest \
  tests/unit/test_support_incident_redaction.py \
  tests/contract/test_support_incident_contract.py \
  tests/integration/test_support_incidents.py
swift test --package-path apps/macos
infra/scripts/ci-local.sh
```

Deployment is not part of this plan phase. If the implementation is later
released, follow `docs/agent-guidance/release-and-validation.md` for dry-run,
execute, smoke, changelog, and release evidence.

## Project Structure

### Documentation (this feature)

```text
specs/061-support-incident-reporting/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── support-incident-contract.md
├── checklists/
│   ├── requirements.md
│   └── support-incident.md
└── tasks.md             # Produced later by $speckit-tasks
```

### Source Code (repository root)

```text
apps/server/src/twobrain_rec_server/
├── api/
│   ├── support_incidents.py
│   └── schemas.py
├── support/
│   ├── incidents.py
│   ├── github_issues.py
│   └── redaction.py
├── db/
│   ├── models/
│   │   ├── support.py
│   │   └── __init__.py
│   └── migrations/versions/0010_support_incidents.py
├── config.py
└── main.py

apps/server/tests/
├── unit/test_support_incident_redaction.py
├── contract/test_support_incident_contract.py
└── integration/test_support_incidents.py

apps/macos/RecApp/Sources/
├── Capture/CaptureControlView.swift
├── Cabinet/DesktopMeetingShellView.swift
└── Upload/
    ├── DesktopUploadClient.swift
    └── DesktopUploadCustodyProjection.swift

apps/macos/Shared/Tests/
├── CaptureControlTests.swift
└── DesktopUploadCustodyProjectionTests.swift
```

**Structure Decision**: Implement the backend as a separate support incident API
and service module under `twobrain_rec_server`, then register the router in
`main.py`. Keep web cabinet rendering in `apps/server/src/twobrain_rec_server/cabinet/`
unchanged. Extend the existing native upload custody projection and capture
control surface instead of creating a new WebView or queue UI.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
