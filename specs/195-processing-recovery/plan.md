# Implementation Plan: Восстановление обработки и ранняя расшифровка встречи

**Branch**: `195-processing-recovery` | **Date**: 2026-08-23 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/195-processing-recovery/spec.md`

## Summary

Перевести серверный lifecycle MediaScribe на v1 и разделить его на безопасные
бизнес-попытки, provider jobs и импортированные GRAF-артефакты. Пользовательский
текст становится доступен только после подтверждённой диаризации; summary,
playback и export больше не блокируют transcript. Временный сбой становится
восстанавливаемым состоянием с durable next-attempt time, countdown и ручным
«Проверить обработку». Temporal оркестрирует bounded stages и durable timers,
а PostgreSQL остаётся источником пользовательской processing truth.

## Technical Context

**Language/Version**: Python 3.11+; existing vanilla JavaScript/Jinja2 cabinet surface

**Primary Dependencies**: Existing FastAPI/Pydantic, SQLAlchemy/PostgreSQL,
MinIO, `httpx`, `temporalio` Python SDK, Jinja2/HTMX cabinet; MediaScribe API v1
as a server-side dependency

**Storage**: Existing PostgreSQL processing/MediaScribe/job/result tables and
owner-controlled MinIO artifacts; Temporal persistence for workflow history and
durable timers

**Testing**: Existing focused pytest/unit/integration suites, MediaScribe contract
fixtures, Temporal `WorkflowEnvironment`/time-skipping/replay tests, cabinet
browser/embedded visual and accessibility checks, and the repository CI gate

**Risk / Validation Lane**: `high-risk-feature` — MediaScribe, Temporal, Postgres,
deletion, retry/egress semantics and degraded-state UX can cause data loss,
duplicate provider jobs, false deletion claims or user-visible trust failures.
Clarify, high-risk checklists, full artifact analysis and repository validation
are required before implementation.

**Release Gate**: `no deploy` for this planning slice. Any later implementation
release requires the normal CI/release gate and a separate deployment approval;
no MediaScribe production migration or Temporal rollout is authorized here.

**Target Platform**: GRAF server/worker on the existing Docker deployment,
browser cabinet and embedded desktop meeting review; MediaScribe v1 server boundary

**Project Type**: Multi-tenant web service with durable backend worker and
desktop-embedded review surface

**Performance Goals**: Preserve the provider's runtime retry hints and active-job
limits; avoid busy polling; expose a first usable result as soon as transcript
and diarization are imported; keep status projection fast enough for ordinary
detail/list requests and do not generate one server request per countdown tick.
Acceptance targets are defined in `spec.md` and bounded by runtime capabilities.

**Constraints**: Server-only MediaScribe credentials; no direct client egress;
same idempotency key and equivalent body for unknown upload outcomes; new key
only for an explicit new business attempt after terminal confirmation; GRAF owns
user-facing status/deletion truth; no raw transcript/audio/provider payloads in
ordinary logs or analytics; no provider webhooks are assumed.

**Scale/Scope**: Existing multi-tenant processing path and browser/embedded
meeting detail/list surfaces. Use provider capability limits and existing quota
admission. Evaluate Temporal task-queue fairness for workspace-level backlog
without introducing one task queue per tenant by default.

## Constitution Check

*GATE: Passed before Phase 0 research; re-check after Phase 1 design.*

- **Capture-first integrity**: Pass. Capture, recording controls and canonical
  audio preparation are reused and not changed by this slice.
- **Visible consent and control**: Pass. No recording start/stop or automatic
  recording contract is changed.
- **Plaintext observability and secret discipline**: Pass with existing policy.
  MediaScribe credentials remain server-side. Ordinary logs, analytics and
  committed evidence are metadata-only; the existing explicitly approved
  Temporal/Langfuse internal-MVP retention policy is not broadened by this plan.
- **External dependency boundary**: Pass. MediaScribe v1 remains an
  owner-controlled server dependency with explicit timeout, retry, egress and
  deletion behavior.
- **Deletion truth**: Pass. Provider cancellation/deletion is represented as
  pending until confirmed; GRAF does not promise erasure outside its control and
  retained Temporal/Langfuse observability remains disclosed.
- **Tenant isolation/RLS**: Pass as a gate. Any new or altered processing fields
  must remain workspace-scoped and covered by existing authorization/RLS tests.
- **High-risk UX and accessibility**: Pass as a requirement. Countdown, manual
  retry, partial artifact states and localized copy require keyboard, screen
  reader, reduced-motion and forced-colors validation.
- **Ponytail**: Reuse existing processing/job/result tables, status projection,
  audit event and cabinet components. Do not add a separate retry service,
  provider console, webhook layer or event store unless a concrete gap is proven.

Post-design re-check: passed. The design keeps the current server boundary and
storage model, adds only the durable fields/contracts needed to preserve v1
signals, and leaves deployment, provider-summary activation and task generation
for a later approval step.

## Validation Plan

The implementation phase must first run the scenarios in `quickstart.md` and the
high-risk checklists. Focused validation must cover:

1. MediaScribe v1 contract fixtures for single/dual upload, capabilities,
   status/queue states, headers, Problem Details, result/summary, downloads and
   synchronous/asynchronous deletion.
2. Retry classification and idempotency tests for transport retry, unknown POST
   outcome, provider `Retry-After`, manual/automatic race, terminal failure and
   refresh/restart recovery.
3. Result-import and projection tests proving that transcript is hidden until
   diarization is ready and is not blocked by summary state.
4. Temporal workflow tests with mocked activities, durable timer time-skipping,
   manual Update/Signal behavior as selected by the contract, cancellation,
   restart/replay and workflow-version compatibility.
5. Browser and embedded desktop checks for countdown copy, button focus/disabled
   state, live-region behavior, refresh/background-tab time calculation and
   artifact-level status parity.
6. Metadata-only analytics/support checks and no-secret/no-content scans.
7. `git diff --check`, focused test suites and `infra/scripts/ci-local.sh` before
   implementation closeout. No `cd-remote.sh --execute` belongs to this slice;
   a later release must run the deployment dry-run separately.

## Project Structure

### Documentation (this feature)

```text
specs/195-processing-recovery/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── mediascribe-v1-client.md
│   ├── processing-status-ui.md
│   └── temporal-processing.md
├── checklists/
│   ├── requirements.md
│   ├── infra.md
│   ├── security.md
│   └── ux.md
└── tasks.md             # intentionally deferred; not created in this slice
```

### Source Code (repository root)

```text
apps/server/src/twobrain_rec_server/
├── mediascribe/                 # v1 transport, schemas, error/header mapping
├── processing/                  # lifecycle, submit/reconcile, import, status
├── workflows/                   # deterministic orchestration and worker entry
├── db/models/processing.py      # existing durable processing entities
├── db/migrations/               # additive lifecycle/result changes if needed
├── api/schemas.py               # server processing status contract
└── cabinet/
    ├── view_models.py           # artifact/recovery projection and copy keys
    ├── templates/cabinet/       # list/detail degraded states
    └── static/cabinet/          # countdown/manual action/accessibility behavior

apps/server/tests/
├── unit/                        # classifiers, projections, state transitions
├── integration/                 # Postgres/MediaScribe/restart/idempotency
└── fakes/                       # provider fixtures and deterministic responses

specs/195-processing-recovery/
├── contracts/                   # v1, UI status and Temporal contracts
└── quickstart.md                # runnable implementation validation scenarios
```

**Structure Decision**: Keep the existing server-owned MediaScribe and cabinet
boundaries. Reuse the current processing tables and content-safe projection;
split the large provider activity into stage-oriented activities and expose one
additive user-facing status contract. No new frontend framework, provider SDK,
queue service or separate retry database is justified.

## Complexity Tracking

No constitution violations. Intentional simplifications: no webhooks, no
provider-facing UI, no new retry service, no per-countdown HTTP polling and no
new task queue per tenant in the first implementation slice.
