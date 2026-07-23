# Implementation Plan: Complete Recording Workflows

**Branch**: `121-recording-workflows` | **Date**: 2026-07-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/121-recording-workflows/spec.md`

## Summary

Complete the GRAF audio-meeting owner journey by composing existing native
capture, local custody/upload, processing, cabinet review, playback, outcomes,
access, export, and deletion foundations. The implementation adds only missing
capture-state presentation, versioned structured summary templates/candidates,
complete sharing/invitation/link policy, and server-rendered meeting-detail
interactions. It preserves native capture ownership, one server meeting model,
one Jinja/HTMX cabinet, feature-120 canonical exports, and existing deletion
authority. The UI deliberately exposes a much smaller route: Start, visible
capture, Stop, Итоги, and optional Share. Detailed lifecycle and policy state
appears only when it changes the user's next action.

## Technical Context

**Language/Version**: Swift 6 on macOS; Python 3.13 on server; HTML/CSS/JavaScript using the existing server-rendered cabinet

**Primary Dependencies**: ScreenCaptureKit and existing native capture services; SwiftUI/AppKit shell; FastAPI; SQLAlchemy 2 async; PostgreSQL; Jinja2; HTMX already vendored in the cabinet; existing Temporal cluster/worker with `temporalio[opentelemetry]==1.30.0`; `opentelemetry-sdk==1.44.0`; existing `httpx==0.28.1` for the owner-controlled LiteLLM Proxy contract; `langfuse==4.14.1` for versioned prompt/model request policy and full-content tracing; optional offline `gepa==0.1.4`; external LiteLLM stable capability baseline `1.93.0`; existing object storage and MediaScribe server boundary. Prompt optimization runs in a dedicated operations-only Temporal worker with the maintenance PostgreSQL role. No DSPy, LiteLLM, OpenAI client SDK, PayloadCodec, codec endpoint/service, key-management subsystem, or second content store is added to GRAF.

**Storage**: Existing v5 local recording package and persisted desktop upload queue; existing PostgreSQL meeting/outcome/access/deletion tables; additive summary-template, exact prompt/config snapshot, retained plaintext generation-call record, Temporal run-chain correlation, optimization-run provenance, and share/invitation tables; resumable GEPA artifacts remain in approved owner-controlled worker storage; no new service or independent content store

**Testing**: Swift package tests and contract validation; pytest unit/contract/integration/RLS tests; Jinja/HTML fixture tests; existing static accessibility/privacy checks; canonical `infra/scripts/ci-local.sh`; manual macOS/browser/embedded prototype and E2E matrix

**Risk / Validation Lane**: High-risk feature — touches recording UX, capture state, privacy, auth/access, external invitations, public links, AI-derived outcomes, Postgres/RLS, Temporal, export/egress, deletion, diagnostics, and cross-surface UX

**Release Gate**: No deploy during planning/prototype. Future implementation requires focused tests, full local CI, independent security/Ponytail review, dry-run deployment, explicit user approval, signed/notarized installed-app proof for macOS changes, and production evidence before any rollout claim.

**Target Platform**: macOS 14+ native app; responsive authenticated web cabinet and embedded WKWebView; self-hosted Linux server

**Project Type**: Native desktop app + server web/API + durable workers

**Performance Goals**:

- capture control/state response visible within 250 ms under normal local conditions;
- Stop stays local and does not wait for network/server response;
- meeting-detail action fragments p95 under 500 ms excluding asynchronous generation/delivery;
- template/grant list bounded to 100 visible records per request;
- idempotent generation/share commands return/reuse the same request within one normal API round trip;
- no playback/timeline regression from feature 118 and no capture real-time thread work added by this feature.

**Constraints**:

- no new capture engine, audio routing, virtual device, bot, video, screen capture, or direct desktop-to-MediaScribe path;
- capture-critical control remains native and one-action Stop remains local;
- browser/embedded review share server authorization truth;
- summary generation is asynchronous, revision-pinned, and never overwrites accepted output silently;
- content-bearing notes generation uses one operator-approved HTTPS LiteLLM
  base URL; each format's exact selected model route, initially
  `gpt-5.6-luna`, generation settings, and response schema come only from the
  pinned promoted Langfuse Prompt Config, while upstream routes/credentials
  never enter Langfuse or GRAF;
- model HTTP and LiteLLM route retries/fallbacks are disabled; Temporal owns
  retry with a 120-second HTTP timeout inside a 150-second activity timeout;
- public/external sharing is disabled until security/delivery/RLS/deletion gates pass;
- ordinary product logs, analytics, screenshots, audit, diagnostics, and
  committed evidence are metadata-only; Langfuse AI observations intentionally
  retain complete plaintext meeting/model content, and Temporal History retains
  the complete plaintext canonical transcript;
- one Langfuse generation observation per completed model call whose response
  reaches durable GRAF storage receives the exact
  compiled request, complete pinned transcript, raw response, and validated
  result; related AI observations may carry the same content. Raw audio and
  runtime credentials are not deliberately attached, while the transcript is
  never encrypted, redacted, masked, truncated, or deleted;
- each completed provider response is atomically stored in a retained plaintext
  generation-call row before acknowledgement; the sole publisher keeps Langfuse
  delivery pending until confirmation, reuses that row and observation identity,
  survives meeting deletion, and never repeats inference, while a pre-persist
  crash remains ambiguous;
- internal production uses a private project at `https://cloud.langfuse.com`
  with no public trace publishing; retention and role access are operator-managed.
  A tracing outage is fail-open for validated candidates,
  while prompt-control fallback remains limited to an integrity-checked export
  of the same promoted prompt/config version, never a code default;
- the first outcome activity resolves and pins prompt/config; model execution
  never re-resolves a mutable label;
- `Авто` is one direct conservative prompt, not a classifier; format prompts
  are self-contained and use no shared prompt dependency graph;
- Temporal 1.30.0's stable `TracingInterceptor` and Langfuse v4 share W3C
  TraceContext; propagated environment/user/session/tags plus nested workflow,
  activity, and generation observations expose full relevant content without
  duplicate generation/cost observations on replay or export retry;
- GEPA runs only as deployment-operator-triggered durable offline work on a
  dedicated concurrency-one task queue in an operations-only worker service, stores full
  optimization artifacts in owner-controlled storage, and cannot promote the
  project-global production label without held-out gates and deployment-operator approval;
- GEPA reflection and three metric-specific quality judges use independently
  pinned Langfuse prompt/configs; deterministic schema/privacy checks remain
  local, and a fenced application call ledger reuses durable successes and
  conservatively accounts ambiguous egress across GEPA resume;
- outcome-generation Temporal History contains the complete canonical
  transcript in deterministic plaintext chunks and may retain other workflow
  content when useful for execution/debugging;
  there is no PayloadCodec, application-layer encryption, redaction, masking,
  truncation, or GRAF-managed History deletion;
- each plaintext transcript chunk is at most 192 KiB before serialization and
  is reduced further to keep its canonical serialized payload at or below
  256 KiB; the complete canonical transcript/snapshot ceiling is 8 MiB, below
  Temporal's 2 MiB request, 4 MiB transaction, and 10 MiB history warning
  thresholds; oversized transcripts fail closed before generation;
- only restart-sensitive external work uses Temporal; authorization, reads,
  validation, and atomic accept/reject mutations remain direct transactions;
- deletion wins generation/share/invite/export races;
- this branch is synchronized with `origin/master` at `43f7b09e`; feature 106
  and merged feature 120 contracts were re-verified after sync. Their remaining
  installed/general-release evidence gates constrain release claims, not reuse
  of the merged code contracts.
- each normal state has at most one visually primary action;
- meeting detail has two content tabs only (`Итоги`, `Расшифровка`) and no permanent lifecycle stepper/right control rail;
- healthy source, pipeline, revision, and sharing-policy detail stays behind contextual disclosure;
- plain Escape dismisses transient UI and never stops recording.

**Scale/Scope**: One active local recording per device; existing self-hosted workspace scale and configured recording duration; reuse current list/pagination patterns only when real data requires them; no speculative template/grant dashboard, global task hub, or bulk cross-meeting sharing in this slice

**Dependency Reconciliation (2026-07-21)**:

- Feature 106 is implemented and locally validated, but installed-app hardware
  acceptance T063 remains open; feature 121 may reuse its code contract but
  cannot claim feature-106 installed/release acceptance.
- Feature 120 is implemented and merged into this baseline through PR #4084.
  Its capability endpoint, revision-pinned export endpoint, scope/format matrix,
  and TXT/MD/CSV/XLSX/versioned-JSON/SRT projections were re-verified here.
  Its controlled production preview is recorded in release
  `v2026.07.21.13`. Feature-120 T059 representative-reviewer evidence remains
  open before general release, so feature 121 may compose the contract but
  cannot inherit a general-release usability claim.
- Feature-120 embedded-download T060 is merged through PR #4217 and packaged in
  draft release `v2026.07.22.1`; this proves source/package readiness, not
  publication, production distribution, installed replacement, or the still-
  open representative-reviewer T059 gate.

## Constitution Check

*GATE: PASS before Phase 0 research.*

| Principle | Result | Evidence / Design Response |
|---|---|---|
| Capture-First MVP Integrity | PASS | Reuses the current Screen/System Audio + explicit microphone path and v5 package. No legacy routing, second writer, bot, video, or hidden AEC. Feature 106 acceptance remains a dependency. |
| Visible Consent And User Control | PASS | Manual Start remains; detect-and-ask has no countdown/autostart; active/paused capture keeps textual state and one-action Stop in main/titlebar/menu-bar surfaces; plain Escape cannot stop capture. |
| Plaintext Observability For Internal MVP | PASS | Constitution v4.0.0 makes Langfuse Prompt Config authoritative for request policy, LiteLLM the sole inference gateway, Langfuse plus Generation Call the complete plaintext call-debug record, and Temporal History the complete plaintext transcript record. No transcript codec, redaction, masking, truncation, or observability deletion subsystem is added. |
| Deletion Truth And Lifecycle Accounting | PASS | Deletion blocks GRAF access and wins races while explicitly disclosing that Langfuse observations and Temporal History remain under operator-managed retention. |
| Spec-Driven Delivery With Testable Gates | PASS | Fresh feature 121 completed full number preflight; specify/clarify/plan/checklist/tasks/analyze precede implementation. High-risk validation and release boundaries are explicit. |

Additional project gates pass: each story has test-first E2E evidence, and the
Krisp references remain clean-room category research rather than copied UI.

## Validation Plan

### Planning / Prototype Gate

- `specify self check`
- `.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks`
- requirements, UX, security/privacy, capture, and lifecycle checklist review
- the first three dense concepts are rejected; generate three revised clean-room expressions of the same calm IA grounded in user screenshots and the existing GRAF baseline
- user selects/refines one expression, then a connected 12-state prototype from `ux-ia.md` is completed before production UI implementation
- `$speckit-analyze` has zero CRITICAL findings before implementation

### Focused Implementation Gate

- macOS capture/state/accessibility suites under `apps/macos/Shared/Tests/`
- server template/outcome/share/invite/access/export/deletion unit and contract tests
- disposable PostgreSQL migration + RLS isolation/rollback tests
- Temporal generation/optimization/delivery idempotency, first-activity config
  resolution, deterministic plaintext transcript chunk assembly and size ceilings,
  replay, restart, cancellation, retained workflow History, and complete raw
  transcript-History tests
- LiteLLM allowlist, private-key file, Langfuse-selected route and upstream
  remap, zero-client-retry, timeout/error classification, strict-schema, and
  provenance tests
- Langfuse prompt/config allowlists, exact generation and workflow content,
  deterministic retry without model replay, verified promoted snapshot,
  Langfuse v4 propagated attributes, prompt linkage, selected/actual model plus
  exact-returned-or-unknown token/cost fields,
  fail-open delivery, retained traces, and trace-shape tests
- GEPA synthetic immutable splits, shared checkpoint/call-ledger resume,
  bounded absolute budget, hard/held-out evaluation, exact reflection/three-
  judge config pinning, exact candidate publication without manual labels, detailed trace,
  deployment-operator promotion, and separate rollback workflow tests
- browser and embedded cabinet HTML/HTMX/focus-state tests
- forbidden-content and secret/PII scan
- feature-120 export and feature-118 playback regressions

### Repository Gate

- `swift test --package-path apps/macos --disable-swift-testing`
- `swift run --package-path apps/macos ContractValidation`
- server test/lint/compile/Compose checks through `infra/scripts/ci-local.sh`
- `@ponytail-review` on the final implementation diff
- independent security review of link/invitation and RLS boundaries

### Release / Production Gate

- no release/deploy in this planning/prototype lane;
- future: `infra/scripts/cd-remote.sh --dry-run`, explicit approval, then execute;
- migration backup/restore/rollback rehearsal;
- signed/notarized old-to-new app update smoke with TCC retention if macOS binary changes;
- real installed-app capture → local custody → upload → processing → review → template → share/revoke → export → delete E2E using synthetic-safe evidence;
- public link/external invite remain runtime-disabled until abuse/delivery/legal gates are separately proven.

## Project Structure

### Documentation (this feature)

```text
specs/121-recording-workflows/
├── spec.md
├── plan.md
├── research.md
├── ux-ia.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── recording-workflow-contract.md
├── checklists/
│   ├── requirements.md
│   ├── ai-content-boundary.md
│   ├── capture-privacy.md
│   ├── infra.md
│   ├── sharing-security.md
│   └── ux.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/macos/
├── RecApp/App/TwoBrainRecApp.swift
├── RecApp/Sources/Capture/
│   ├── CaptureControlViewCore.swift
│   ├── CaptureSessionController.swift
│   ├── CaptureStatusItem.swift
│   └── DesktopPermissionOnboardingView.swift
├── RecApp/Sources/Cabinet/DesktopMeetingShellView.swift
└── Shared/Tests/
    ├── CaptureControlV5Tests.swift
    ├── CaptureIndicatorTests.swift
    ├── AppControlAccessibilityTests.swift
    └── DesktopUploadQueueV5Tests.swift

apps/server/src/twobrain_rec_server/
├── api/
│   ├── cabinet.py
│   └── schemas.py
├── cabinet/
│   ├── access.py
│   ├── queries.py
│   ├── rendering.py
│   ├── review_policy_rendering.py
│   ├── view_models.py
│   ├── web_routes/browser.py
│   ├── static/cabinet/cabinet.css
│   ├── static/cabinet/cabinet.js
│   └── templates/cabinet/
│       ├── pages/meeting_detail_content.html
│       └── fragments/
├── db/models/
│   ├── meeting.py
│   ├── meeting_access.py
│   └── outcomes.py
├── db/migrations/versions/0031_recording_workflow_templates_sharing.py
├── db/migrations/versions/0032_backfill_current_outcome_set.py
├── db/migrations/versions/0033_prompt_optimization_maintenance.py
├── outcomes/
│   ├── ai_service.py
│   ├── generator.py
│   ├── prompts.py
│   ├── prompt_optimization.py
│   └── templates.py
├── observability/
│   └── langfuse.py
├── workflows/
│   ├── invitation_delivery_workflow.py
│   ├── outcome_generation_workflow.py
│   ├── prompt_optimization_workflow.py
│   ├── prompt_rollback_workflow.py
│   ├── prompt_optimization_worker.py
│   ├── temporal_client.py
│   └── worker.py
├── cli/prompt_optimization.py
└── deletion/

apps/server/tests/
├── unit/
├── contract/
└── integration/
```

**Structure Decision**: Keep native capture changes inside current Swift files
and keep post-meeting functionality inside the existing server cabinet,
including pending invitation/link policy in the current access service;
template generation remains with the existing `outcomes/` package. The new
`ai_service.py` owns only Feature-121 durable candidate/generation-call
activities; the pre-existing `service.py` keeps synchronous non-AI outcome
projection and is not overloaded with provider orchestration. Add one
focused Langfuse adapter under
the existing observability boundary and one outcome workflow/activity under the
existing Temporal worker. Add a small optional offline GEPA adapter and a
second workflow definition in that same boundary; do not add another cluster,
worker service, DSPy stack, generic telemetry framework, or global FastAPI/SQL
instrumentation. Add no global navigation destination,
permanent meeting-detail control rail, frontend project, or dependency.

## Phase 0 Research

Completed in [research.md](./research.md):

- current repo flow and reusable authorities;
- official Krisp category behavior and contradictions;
- Apple ScreenCaptureKit permission/capture guidance;
- WAI modal/focus guidance;
- template/version decision;
- audience/content/capability sharing decision;
- public/external security boundary;
- export/deletion reuse and clean-room prototype direction.
- one-primary-action and progressive-disclosure guidance from Apple HIG, W3C,
  and GOV.UK Design System.
- official Langfuse Python v4 instrumentation, observation, prompt-management, and
  trace-quality guidance;
- versioned Langfuse Prompt Config authority for separate format prompts,
  selected model route, generation settings, and strict response schemas;
- existing Temporal processing/normalization workflow reuse, plaintext payload
  limits, retry classification, reconciliation, cancellation, and official
  OpenTelemetry context propagation boundaries;
- official GEPA reflective optimization, resumability, Pareto evaluation, and
  the distinction between GEPA prompt optimization and JEPA model training.

No `NEEDS CLARIFICATION` items remain for planning. User may still refine the
visual direction after seeing three options; that selection changes prototype
expression, not the core trust model.

## Phase 1 Design

- [data-model.md](./data-model.md) defines additive entities, fields,
  transitions, authorization matrix, and migration compatibility.
- [ux-ia.md](./ux-ia.md) defines the calm three-place IA, disclosure policy,
  complete scenario matrix, exact Russian state/action copy, and required
  12-state connected prototype.
- [contracts/recording-workflow-contract.md](./contracts/recording-workflow-contract.md)
  defines native projection, server commands, narrow share projections,
  HTML/HTMX interactions, accessibility, and safe problem details.
- [quickstart.md](./quickstart.md) defines independent E2E and failure/race
  evidence scenarios.

## Post-Design Constitution Check

*GATE: PASS against constitution v4.0.0.* The design adds no capture/audio path,
keeps manual/local control, makes Langfuse the versioned request authority and
complete call-debug record, routes inference only through owner-controlled
LiteLLM, retains complete plaintext meeting/model content in Langfuse and the
Generation Call ledger plus the complete plaintext transcript in Temporal
History, keeps optimization synthetic, and makes external sharing fail
closed until gated. No exception or complexity waiver is required.

## Complexity Tracking

No constitution violations require justification. Production adds the official
Langfuse SDK and pinned OpenTelemetry support to the existing Temporal/httpx
boundary. GEPA is optional offline-only. DSPy, LiteLLM SDK, OpenAI SDK, another
provider abstraction, content store, codec/key service, and orchestration
service are not added. The existing Temporal cluster is reused. GEPA uses a
dedicated operations-only worker service and optimization task queue with
concurrency one; it never shares the normal recording worker or its
credentials. A separate Temporal cluster is deferred until measured
isolation/capacity requires it. Existing
cabinet access, outcome generation, export, and deletion modules remain the
owning services.

Temporal 1.30.0's stable interceptor is selected for production even though its
new OpenTelemetry plugin is recommended for more accurate spans, because the
plugin API is still officially experimental. Workflow spans are explicitly
zero-duration correlation markers; activity/generation spans and durable
timestamps own latency. Recorded-history replay, trace shape, client-local W3C
TraceContext plus bounded Langfuse-attribute baggage propagation, full-content
trace inspection, and no-duplicate-cost tests are mandatory. The
plugin becomes the upgrade path after API stabilization and the same gates. A
shared prompt base, meeting classifier, separate optimization service, and
real-meeting optimization datasets are deliberately excluded.
