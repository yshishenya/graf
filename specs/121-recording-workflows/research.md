# Research: Complete Recording Workflows

**Date**: 2026-07-21
**Mode**: Read-only clean-room product, repository, and internet research

## Research Boundary

Krisp is used only to identify category expectations and failure modes. GRAF
does not copy Krisp copy, branding, assets, colors, icons, layout, proprietary
behavior, binaries, or model behavior. The two user-provided screenshots prove
only a summary-template selector and a sharing dialog state. Official help
pages were used for broader behavior; contradictory vendor claims are not
treated as GRAF requirements.

## Selected Visual Direction And Prototype

**Selected by the user**: visual direction 1, the calm single-column meeting
workspace with compact navigation, exactly two content tabs, contextual format
selection, Share/More actions, and a persistent player.

**Reference**:
`/Users/yshishenya/.codex/generated_images/019f8549-3049-7bd2-959d-fcbfb15ae912/exec-148db47b-9d0d-4ef4-b849-b3166dcfd49d.png`

**Interactive artifact**: `specs/121-recording-workflows/prototype/`

**Local preview**: `http://127.0.0.1:4173/`

The prototype keeps the selected visual direction as the default ready-summary
state and connects the 12 required lifecycle/exception states through real
controls. A prototype-only scenario switcher is available from the profile or
version label and is excluded from the production IA. Visual and interaction
evidence is recorded in `specs/121-recording-workflows/prototype/design-qa.md`.

## Decision 1: Converge Existing GRAF Capabilities

**Decision**: Implement one coherent workflow by extending existing native
capture state, local custody/upload, server review, access, outcomes, export,
and deletion paths. Do not create another recorder, upload pipeline, SPA,
playback stack, or access layer.

**Rationale**:

- Native start, pause/resume, stop, permission recovery, local package writing,
  upload retry, processing, playback, speaker review, outcomes, internal-user
  grants, downloads, and deletion already exist.
- The actual product gaps are disabled or read-only meeting-detail actions,
  summary templates/revisions, recipient selection, broader sharing policy, and
  complete state/interaction coverage.
- A second path would create conflicting meeting identity, lifecycle, tenant,
  and deletion truth.

**Alternatives considered**:

- New end-to-end recording subsystem: rejected because it duplicates accepted
  capture and backend foundations and violates the removed-legacy boundary.
- Frontend SPA: rejected because the current cabinet intentionally uses one
  server-owned Jinja/HTMX shell shared by browser and embedded desktop.

## Decision 2: Keep Capture Native, Visible, And Deliberate

**Decision**: Reuse the existing macOS capture controller, status item, HUD,
permission onboarding, v5 writer, and upload queue. Add no silent auto-start,
second mute control, bot, video, or screen capture. Meeting detection remains
detect-and-ask.

**Rationale**:

- Apple ScreenCaptureKit requires explicit user permission and provides the
  native system-audio/microphone stream boundaries used by GRAF. Apple's sample
  also demonstrates separate stream outputs and permission/restart behavior:
  https://developer.apple.com/documentation/screencapturekit/capturing-screen-content-in-macos
- Krisp exposes duration, active state, and pause/resume in an in-call widget;
  this confirms the category expectation for persistent controls without
  authorizing its visual expression:
  https://help.krisp.ai/hc/en-us/articles/15521278939548-Using-Krisp-Widget-on-AI-Meeting-Assistant
- The GRAF constitution requires persistent local capture indication and a
  one-action stop path.

**Alternatives considered**:

- Policy-gated auto-record in this slice: rejected because it requires a
  separate notice/legal and target-scope approval.
- App-level microphone mute: rejected because product Pause already provides
  the honest privacy action for both owned sources.
- Seamless device hot-switch guarantee: rejected until capture evidence proves
  it; this feature shows degraded/recovery truth instead.

## Decision 3: Use One Explicit Recording Lifecycle

**Decision**: Project existing subsystem states into one user lifecycle:
`blocked/ready → starting → active ↔ paused → stopping/finalizing → saved_local
→ queued/uploading/retrying → processing → partial/ready/failed → deleting/deleted`.
Artifact readiness remains independent inside that lifecycle.

**Rationale**:

- Capture state, upload state, transcript state, playback state, summary state,
  and deletion state have different authorities and must not be collapsed into
  a generic `ready` or `failed` label.
- Krisp help describes recording, post-meeting processing, retry/error, and
  storage-limit behavior, but does not document crash recovery. GRAF therefore
  keeps its stronger local-custody guarantee instead of mirroring cloud-first
  assumptions:
  https://help.krisp.ai/hc/en-us/articles/12216182124956-FAQ-about-Krisp-Recording-feature

**Alternatives considered**:

- One progress percentage: rejected because most stages are not measurable as
  one monotonic percentage.
- Manual repair buttons for every state: rejected because automatic durable
  recovery should remain automatic until a safe user action is actually needed.

## Decision 4: Structured Templates, Revisioned Outcomes

**Decision**: Templates are versioned, bounded definitions of supported outcome
sections, output language, and detail level. GRAF seeds original built-ins and
supports personal copies. Regeneration creates a candidate outcome revision;
the last accepted revision stays current until explicit replacement.

**Rationale**:

- Krisp supports built-in/custom templates, a default, per-meeting override,
  and regeneration. Its documented regeneration replaces previous notes and
  can remove manual edits, which GRAF treats as a failure mode to avoid:
  https://help.krisp.ai/hc/en-us/articles/26708055686044-Meeting-Notes-Templates
- GRAF already stores outcome sets, items, generation attempts, source result,
  hashes, generator version, and lifecycle state. Extending this model is
  smaller and safer than introducing a second notes store.
- Structured sections keep prompt injection, arbitrary markup, and provider
  coupling outside the first version.

**Alternatives considered**:

- Free-form system prompts: rejected for v1 because they expand security,
  quality, and support scope without being required by the reference.
- Mutating one summary row: rejected because it destroys provenance and creates
  races with sharing/export.
- Global task hub: deferred; action items inside a meeting are sufficient for
  this workflow.

## Decision 5: Sharing Has Three Independent Axes

**Decision**: Model `audience × content scope × role` explicitly. Default to
invite-only + summary-only + view. Copy link preserves current access. Broader
workspace/team/link access requires explicit confirmation. Public and external
delivery are implemented only after their security gates pass.

**Rationale**:

- Krisp documents audience modes, summary-only versus everything, and view/edit
  collaboration. These are separate choices, not one overloaded visibility
  field:
  https://help.krisp.ai/hc/en-us/articles/10386573495196-Sharing-your-meetings-with-Krisp
- The user screenshot shows owner, recipients, current general access, and Copy
  link in one context. The useful pattern is visible scope before copying; the
  exact layout and wording are not copied.
- Current GRAF grants are authenticated, workspace-bound, recipient-specific
  token grants. They can be extended for role/content without weakening the
  existing authorization path.
- A generic public link needs a separate hashed token lifecycle, expiry,
  rotation, rate limits, narrow projection, audit, deletion behavior, and
  abuse controls. An external email invite needs a pending-invite identity and
  delivery lifecycle; neither can be faked by storing raw email in the current
  user-grant row.

**Alternatives considered**:

- Copy link implicitly changes visibility to public: rejected as a privacy bug.
- Anonymous users receiving the internal meeting-review response: rejected as
  an authorization and data-minimization failure.
- Raw email as the long-lived grantee identity: rejected; use normalized,
  privacy-bounded pending invitations and resolve to internal user identity.

## Decision 6: Reuse Export And Deletion Sources Of Truth

**Decision**: The meeting workspace links to the accepted canonical export
contract from feature 120 and existing server-mediated download/deletion
services. Feature 121 owns orchestration and UI completeness, not duplicate
formatters or deletion workers.

**Rationale**:

- Feature 120 is merged into this synchronized baseline and defines provider-
  neutral TXT, MD, CSV, XLSX, versioned JSON, and SRT projections with revision/
  egress truth. Its controlled production preview is recorded in release
  `v2026.07.21.13`; its implementation contract is reusable, while open T059
  still blocks a general-release usability claim.
- Embedded-download T060 is merged through PR #4217 and packaged in draft
  release `v2026.07.22.1`; feature 121 reuses that updated source contract
  without inferring publication, production distribution, installed-app
  replacement, or closure of T059.
- Existing whole-meeting deletion already blocks access and accounts for local,
  server, backup, dependency, workflow, and post-egress limits.
- Deletion must win races once requested; exported/downloaded copies outside
  GRAF control cannot be recalled.

**Alternatives considered**:

- Direct browser construction of files: rejected because it bypasses policy,
  audit, revision pinning, and deletion races.
- Promising universal erasure: rejected by the constitution.

## Decision 7: Accessibility Is Part Of Safety

**Decision**: Modal/popup behavior, keyboard focus, screen-reader state, narrow
layouts, reduced motion, increased contrast, and Russian labels are acceptance
requirements, not polish.

**Rationale**:

- WAI-ARIA's modal dialog pattern requires focus to enter the dialog, remain
  contained with Tab/Shift+Tab, close via Escape when appropriate, and return
  to a logical point after close:
  https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/
- Recording Stop, sharing scope, regeneration replacement, and deletion are
  safety-sensitive actions. Pointer-only or color-only behavior is not adequate.

**Alternatives considered**:

- Accessibility after visual implementation: rejected because modal structure
  and focus ownership affect the interface contract and tests.

## Decision 8: Hide System Complexity Behind One Human State

**Decision**: Use the three-place IA and progressive-disclosure contract in
[ux-ia.md](./ux-ia.md). The normal route has one primary action per state; the
meeting page has two content tabs only; templates, Share, export, deletion, and
provenance open as focused contextual flows.

**Rationale**:

- Review of all three initial concepts found the same failure: each displayed
  navigation, transcript, outcomes, pipeline state, templates, and access at
  once. The control-center direction was the most severe example.
- The existing meeting-detail right rail already exposes too many independent
  concepts. Feature 121 should remove or relocate that density instead of
  adding more panels.
- Apple recommends passive contextual feedback for normal status and alerts
  only for important actionable interruption; W3C recommends clear hierarchy,
  concise content, and predictable modal behavior; GOV.UK Details formalizes
  optional information revealed only when needed.
- The user's job is linear even when the implementation is not: record, know
  the recording is safe, stop, review, optionally share.

**Alternatives considered**:

- Permanent lifecycle stepper: rejected because it makes internal pipeline
  stages look like tasks the user must manage.
- Permanent right inspector: rejected because it competes with meeting content.
- Role/capability matrix in Share: rejected because this slice is view-only and
  the safe default already resolves most decisions.
- Separate novice/expert modes: rejected; remembered defaults, menu bar control,
  shortcuts, and settings cover repeat/power use without two products.

## Decision 9: Durable Outcome Generation Reuses Temporal

**Decision**: Add one `OutcomeGenerationWorkflow` to the existing Temporal
cluster and processing worker. The API first commits a queued candidate and
generation attempt, then dispatches a deterministic
`outcome-generation/<candidate_id>` workflow. A reconciler picks up committed
rows that were not dispatched. Start with the existing processing task queue;
split a worker or queue only after measured capacity, rollout, or credential
isolation requires it.

Workflow input contains compact pinned request identity only. A metadata
activity pins the canonical transcript hash and chunk count; chunk activities
return the complete canonical transcript as deterministic uncompressed UTF-8
chunks no larger than 192 KiB before serialization and 256 KiB after canonical
serialization. The model activity reloads the authorized transcript, assembles
and validates it against that plaintext History snapshot, compiles the prompt,
calls the allowlisted LiteLLM
gateway, validates the response, and atomically stores the candidate plus a
retained plaintext Generation Call row. Exactly one Langfuse generation records
the call's complete request/transcript/raw response/validated result. The sole
publication activity keeps Langfuse export durably pending until confirmation;
candidate readiness remains fail-open and retry never repeats the model call.
Accept/reject remains a direct atomic database transaction.

**Rationale**:

- Temporal is already installed and operates MediaScribe processing and
  playback normalization; another cluster or orchestration framework is not
  needed.
- External AI calls are long-running and retryable and must survive worker/API
  restarts without duplicate candidates or automatic replacement.
- Temporal activity retries are at-least-once, so the provider call and store
  path need the candidate ID as the idempotency key.
- Plaintext History gives the operator immediate end-to-end debugging without a
  codec, key lifecycle, decode endpoint, or deletion subsystem during the MVP.
- Normal authorization, reads, validation, and accepted-pointer changes are
  shorter and safer as direct application/database operations.

**Retry and deletion policy**:

- Retry timeout, connection, rate-limit, and transient `5xx` failures with
  bounded exponential backoff.
- Treat auth/configuration, invalid input, stale source/template, policy,
  deletion, and structured-output failures as non-retryable.
- Check deletion before external egress and again before persistence; request
  workflow cancellation on deletion, while the database tombstone remains the
  authority.
- Do not copy the current long polling loop into the outcome workflow; the
  selected LiteLLM contract is one bounded synchronous request per activity.

**Alternatives considered**:

- New Temporal cluster or immediate `rec-outcomes-worker`: rejected until a
  concrete isolation or capacity requirement exists.
- Sending every API/DB action through Temporal: rejected because it adds
  latency, event history, and operational coupling without durability value.
- Encrypted PayloadCodec and private Codec endpoint: rejected for the internal
  MVP because they add key rotation, decode, replay, and operational failure
  modes while the operator explicitly prioritizes complete observability.
- External transcript offload: rejected because the user requires Temporal
  History itself to contain the full transcript. Deterministic plaintext chunks
  reuse the existing cluster and worker while respecting hard payload limits.

## Decision 10: Langfuse Owns Prompt And Model Request Policy

**Decision**: Use a separate versioned Langfuse chat prompt for each built-in
outcome format and one bounded `custom` prompt for all personal structured
templates. The prompt's versioned `config` is the single editable source for
the selected LiteLLM model route and the exact v1 profile fields only: literal
contract version, `model`, `temperature`, `max_completion_tokens`, and—for
outcome/judge prompts—the strict `response_format`. The initial selected route
is `gpt-5.6-luna`.

Prompt names use `graf/meeting-outcome/<built-in-key>` and
`graf/meeting-outcome/custom`. GRAF stores only the bounded mapping from a
template key to one allowlisted prompt name. It does not create a Cloud prompt
per user. Personal template name, sections, language, and detail are validated
structured variables, never system-prompt text.

`graf/meeting-outcome/auto` is a self-contained conservative general-summary
prompt. It does not add a meeting classifier or a second model call. Each
format prompt is self-contained rather than referencing a shared base: with the
small bounded built-in set, atomic versioning and rollback are worth more than
a prompt dependency graph.

The first activity in `OutcomeGenerationWorkflow` resolves the explicit
`production` label, validates prompt type, variables, config keys, types,
provider capability, safety/budget ceilings, and schema compatibility, then
atomically persists the exact uncompiled prompt/config snapshot,
schema/adapter versions, canonical hash, and source. Later activities use that snapshot and
never re-resolve a label. `latest` is never used in production.

An integrity-checked last-known-good export of the same previously promoted
Langfuse version may cover an outage. It is an immutable cache artifact with a
recorded source version/hash, not a second editable prompt. If neither Langfuse
nor a verified snapshot exists, only AI generation enters
`blocked_dependency`; recording, upload, and transcription continue.

Langfuse is not a secret store. LiteLLM URL/key, Langfuse keys, upstream
provider secrets/routes, network headers, retry policy, and security ceilings
remain file-backed deployment/application policy. Arbitrary config keys,
destinations, tools, or headers are rejected rather than passed through.

**Rationale**:

- Langfuse Python v4 is OpenTelemetry-based, asynchronous, and catches SDK
  export failures rather than breaking application work:
  https://langfuse.com/docs/observability/sdk/overview
- Prompt Config is versioned atomically with prompt text and officially supports
  model parameters and strict structured-output schemas:
  https://langfuse.com/docs/prompt-management/features/config
- Langfuse v4 recommends meaningful observation input/output, stable action
  names, prompt linkage, propagated environment/user/session/tags, and
  model/token/cost fields. GRAF sends exact LiteLLM/provider usage/cost when
  returned, otherwise lets Langfuse calculate cost from its configured model
  catalog or records `unknown`; it never fabricates accounting:
  https://langfuse.com/docs/observability/best-practices
- Production prompt lookup should use an intentionally promoted production
  version:
  https://langfuse.com/docs/prompt-management/get-started
- The SDK cache defaults to 60 seconds, serves stale values during background
  refresh, and supports a cold-start fallback:
  https://langfuse.com/docs/prompt-management/features/caching
- Deterministic trace IDs can be derived from an external stable seed:
  https://langfuse.com/docs/observability/features/trace-ids-and-distributed-tracing
- Feature 121 intentionally keeps complete plaintext meeting/model content in
  AI workflow observations and does not install masking or redaction. Ordinary
  product logs, screenshots, audit, diagnostics, and committed evidence remain
  separate metadata-only surfaces.

**Credential boundary**:

- Local keys live only in ignored `infra/secrets/` files with owner-only
  permissions.
- Production keys come from operator secret files/store and are mounted only
  into the outcome-capable worker, never macOS or browser code.
- The key supplied in chat is usable for the requested setup/smoke but must be
  rotated afterward because conversation disclosure prevents treating it as a
  long-lived production secret.

**Alternatives considered**:

- Global FastAPI/HTTP/SQL tracing: rejected as noisy and higher-risk for route,
  query, and identity leakage.
- A single prompt plus code-owned format recipes: rejected because formats have
  different user goals, evaluators, and optimization lifecycles, and model
  request policy belongs in Langfuse.
- Editable local fallback: rejected because it creates a conflicting model and
  prompt authority. Only an exact verified export of a promoted version is
  allowed.

## Decision 11: LiteLLM Executes; Temporal And Langfuse Share Trace Context

**Decision**: GRAF calls one owner-controlled, operator-allowlisted LiteLLM
Proxy over its OpenAI-compatible `/v1/chat/completions` contract. The exact
model route comes from the pinned Langfuse config; LiteLLM owns only mapping
that route to an approved provider, gateway policy, and upstream secrets. The
base URL and virtual key are file-backed deployment inputs supplied before
live smoke.

Selected-model changes occur by promoting a Langfuse prompt/config version;
upstream-provider changes may occur behind the same LiteLLM route. Neither
requires a GRAF provider factory. GRAF records the selected route plus actual
provider/model/request provenance returned by the gateway when available and
locally validates the exact pinned strict schema.

GRAF uses the already-installed, current stable `httpx==0.28.1` rather than
adding either the LiteLLM Python SDK or OpenAI SDK. As of 2026-07-21 the current
stable gateway package is `litellm==1.93.0` (`1.94.0rc2` is prerelease), the
current Temporal SDK is `temporalio==1.30.0`, and the current Langfuse SDK is
`langfuse==4.14.1`. The app lock is refreshed to those stable versions during
implementation; the external gateway must report compatible capability before
rollout.

The HTTP client performs zero retries and uses a bounded application-owned
timeout inside the Temporal activity timeout. The LiteLLM route must also
disable its own retries/fallbacks so one durable retry authority exists.
Timeout, connection, `408`, `429`, and `5xx` failures are retryable; `400`,
`401`, `403`, `404`, `422`, budget/policy, missing-alias, and schema failures
are terminal until configuration or input changes.

**Rationale**:

- LiteLLM Proxy supports OpenAI-format calls, virtual keys, semantic model
  aliases, provider routing, and structured JSON-schema output:
  https://docs.litellm.ai/
  https://docs.litellm.ai/docs/completion/json_mode
- Reusing `httpx` is the smallest dependency surface and makes retry ownership
  explicit.
- Langfuse decouples selected model/request policy from code; LiteLLM decouples
  that selected route from the upstream provider.
- Temporal Python's official OpenTelemetry interceptor propagates W3C context
  through workflow and activity boundaries:
  https://github.com/temporalio/sdk-python#opentelemetry-tracing

**Alternatives considered**:

- LiteLLM Python SDK inside GRAF: rejected because routing already belongs to
  the deployed Proxy and the extra dependency/retry layer adds no capability.
- OpenAI SDK pointed at the Proxy: rejected because the required endpoint and
  strict response are small, existing `httpx` already covers them, and local
  Pydantic validation remains mandatory.
- One GRAF adapter/factory per provider: rejected because it duplicates LiteLLM
  and makes every provider change a code rollout.

Use `temporalio[opentelemetry]==1.30.0` with the stable
`TracingInterceptor`, registered once on the Temporal client and inherited by
the worker. A minimal subclass uses a client-local composite W3C TraceContext
and Baggage propagator. Baggage is restricted to the approved Langfuse
environment/user/session/fixed-trace-name/tags correlation fields, while the transcript and
model content remain in their explicit Temporal payload and Langfuse
observation fields. The global propagator is unchanged. Because the serialized
headers are immutable workflow input and extraction is deterministic, replay
does not create a new side effect or model call. Langfuse `4.14.1` uses the same
OpenTelemetry provider and exports the explicit outcome/optimization workflow
tree. It does not turn on unrelated global HTTP, SQL, FastAPI, or object-store
auto-instrumentation.

The deterministic root trace ID is derived from
`outcome-generation/<candidate_id>`. The execution activity persists a retained
plaintext Generation Call row; the publication activity owns the Langfuse
generation and uses the original call timestamps:

```text
generate-meeting-outcome
└── run-outcome-workflow
    ├── resolve-prompt-config
    ├── snapshot-transcript-metadata
    ├── snapshot-transcript-chunk[*]   # complete plaintext History
    ├── execute-generation-attempt
        ├── load-context
        ├── call-outcome-model          # provider egress; no generation owner
        ├── validate-outcome
        └── persist-candidate
    └── publish-observability           # sole generation owner; retry only
```

Every real activity retry records `activity.info().attempt`, and every completed
provider call whose response reaches durable GRAF storage creates one distinct
generation. Workflow replay, duplicate
dispatch, and idempotent short-circuit do not create a generation or cost.
The model call and candidate are not repeated when export fails. An application
delivery ledger retries the same deterministic trace and observation identity
until the Langfuse observation is confirmed; errors remain durably pending and
candidate readiness does not wait for tracing. Meeting deletion cannot cancel
this delivery after a completed call is retained. A genuine provider retry gets
a new deterministic observation ID from
provider attempt/call sequence, while an ambiguous crash has metadata only.
AI workflow observations may expose the full request, transcript, raw response,
validated result, and failure context. Raw audio and runtime credentials are not
deliberately added as observation attributes; no content-changing mask is used.

Temporal snapshot activities return deterministic plaintext chunks no larger
than 192 KiB before serialization and reduce them further whenever canonical
JSON would exceed 256 KiB. A shared assembler validates identity, count, order,
duplicates, contiguous indices, UTF-8, and final SHA-256 before model execution.
One workflow accepts at most 8 MiB of canonical transcript/snapshot, below
Temporal's 2 MiB payload, 4 MiB transaction, and 10 MiB practical History
target. No PayloadCodec, Failure
Converter, application encryption, key ring, or Codec endpoint is added.
Search Attributes and Memo remain bounded operational indexes.

The newer `OpenTelemetryPlugin` is recommended by Temporal for accurate workflow
durations but remains explicitly experimental in SDK 1.30.0. GRAF deliberately
chooses the stable interceptor now: workflow spans are zero-duration correlation
markers and durable workflow/activity/DB timestamps own end-to-end latency.
Revisit after the plugin API is stable and passes recorded-history replay,
TraceContext propagation, full-content inspection, and trace-shape tests.

Temporal 1.30.0 comparison and interceptor source:
https://github.com/temporalio/sdk-python/blob/1.30.0/temporalio/contrib/opentelemetry/README.md
https://github.com/temporalio/sdk-python/blob/1.30.0/temporalio/contrib/opentelemetry/_interceptor.py

## Decision 12: GEPA Improves Prompts Offline; JEPA Is Not Added

**Decision**: Add only `gepa==0.1.4` in an optional evaluation dependency
group. Do not add DSPy, GEPA full extras, or another production inference
stack. A thin GEPA adapter invokes the same pinned prompt compilation,
zero-client-retry LiteLLM call, structured validation, and bounded evaluators
used by production.

Use four additional self-contained Langfuse control prompts:
`graf/prompt-optimization/reflection` for GEPA's native textual proposal, plus
independently calibrated faithfulness, action-item, and completeness judges
under `graf/evaluation/meeting-outcome-*`. Their model routes, generation
parameters, and judge schemas live in Prompt Config and exact versions/hashes
are pinned to the run. Separate judges keep rubrics and calibration histories
auditable; hard schema/privacy checks remain deterministic code.

`PromptOptimizationWorkflow` is deployment-operator-triggered, global to the
Langfuse project, unavailable to workspace/cabinet admins, and never runs in a
user request. It pins source/reflection/three-judge versions, immutable
synthetic train/development/held-out manifests, metric/evaluator versions,
absolute deadline/budget, and rollback target. A concurrency-one heartbeat
activity snapshots GEPA state to shared owner-controlled storage. Worker-local
`run_dir` is insufficient because a retry may execute elsewhere. Checkpoints
are immutable server-generated objects under a fixed prefix; checksum/schema/
optimizer version is verified before restore and the DB pointer advances only
after a complete upload.

GEPA 0.1.4 checkpoints at iteration boundaries and performs seed validation
before restoring an existing run. An application-owned metadata call ledger is
therefore mandatory for task/reflection/judge budget reservation and reuse of
durable successes. Each reservation has a lease and activity fence; a retry
atomically fences the old worker, expired work becomes ambiguous, and the old
worker cannot commit. Ambiguous crash outcomes consume budget and follow a
bounded operator policy. Callbacks receive raw content and swallow their own
failures, so GRAF wraps them as non-throwing/sanitizing aggregate emitters that
never own cancellation, budget, checkpointing, or telemetry content.

GEPA optimizes against hard schema/privacy constraints plus a small quality
set: unsupported-claim/faithfulness, action-item coverage/precision, and
format-specific completeness. Latency and token cost are ceilings/objectives,
not substitutes for quality. LLM judges must be calibrated against human labels
before they can gate release.

Control-prompt promotion is separate from outcome-prompt optimization.
Reflection versions must preserve the exact GEPA 0.1.4 `<curr_param>` and
`<side_info>` placeholders plus one triple-backtick proposal fence and pass
native-parser/preservation/anti-copy/cost smokes. Each judge version must pass
its own frozen human-labelled synthetic calibration, invalid-output report,
agreement threshold, and deployment-operator approval; labels never enter the
judge task itself.

Held-out evaluation is isolated until finalist selection. Only a passing
finalist creates an exact numeric prompt version with no manually assigned
candidate/staging/production label; Langfuse-managed `latest` is ignored. The
candidate is re-read and its canonical config SHA-256 must equal the source.
Promotion serializes per prompt, rechecks expected `production`, moves the
label, clears cache and post-verifies; this detects conflicts but is not native
CAS. Protected label plus a sole deployment-service mutation credential is a
rollout gate; otherwise automated promotion stays disabled. Rollback is a
separate linked durable workflow. Feature 121 uses synthetic owner-controlled
datasets only; meeting-derived optimization is a later product decision.
Langfuse observations and Temporal History may retain complete plaintext
synthetic inputs, outputs, reflection, judge feedback, and optimizer state for
the full run. Owner-controlled checkpoints remain the resume authority. An
operator purge removes only GRAF-owned run rows/call-ledger rows/checkpoints;
Langfuse traces and Temporal History remain retained observability copies.

GEPA is the Genetic-Pareto reflective optimizer described by its official
project and paper:
https://gepa-ai.github.io/gepa/guides/
https://arxiv.org/abs/2507.19457

The resume/callback/budget behavior above is pinned to GEPA 0.1.4 source:
https://github.com/gepa-ai/gepa/blob/v0.1.4/src/gepa/core/engine.py
https://github.com/gepa-ai/gepa/blob/v0.1.4/src/gepa/core/callbacks.py
https://github.com/gepa-ai/gepa/blob/v0.1.4/src/gepa/utils/stop_condition.py

JEPA means Joint-Embedding Predictive Architecture and targets representation
learning/model training, not prompt optimization. It is therefore outside this
feature rather than being represented as an interchangeable optimizer:
https://ai.meta.com/blog/yann-lecun-ai-model-i-jepa/

**Alternatives considered**:

- Optimizing inline with summary generation: rejected because it adds latency,
  nondeterminism, cost, and unreviewed behavior to a user action.
- Auto-promoting the best aggregate score: rejected because optimizer/judge
  regressions and overfitting require held-out and human gates.
- Using real meeting-derived datasets in Feature 121: rejected to keep the first
  optimizer synthetic and bounded; this does not limit full-content tracing of
  the synthetic optimization workflow.
- JEPA prompt optimization: rejected because no such applicable prompt
  optimizer was identified; adopting model training needs a separate slice.

## Clean-Room Interface Findings

### User screenshots

- The template selector uses progressive disclosure: quick choices, library,
  and New template.
- The share dialog keeps recipient entry, owner/current grants, access scope,
  and Copy link visible together.
- The visible focus ring is a useful state cue, but the screenshot alone does
  not prove focus trap, Escape, tab order, or accessible names.
- Vendor-specific scope labels, emoji, purple selection treatment, spacing,
  and exact composition must not be copied.

### Existing GRAF baseline

- Reuse dark surfaces, typography, spacing, button sizing, tabs, status chips,
  focus treatment, and native-over-embedded capture ownership from feature 030.
- Keep the meeting detail focused on playback/transcript/outcomes; templates
  and Share are contextual actions, not new top-level destinations.
- Keep lifecycle rows inside the meeting list/workspace; do not create a second
  queue product.

## Vendor Contradictions And Rejected Assumptions

- Krisp official pages disagree on minimum meeting duration and recording
  storage limits. GRAF uses its own tested limits and does not copy those values.
- Krisp's general local-processing marketing does not apply uniformly to its
  recording/AI modes. GRAF must always state local storage, upload, and external
  processing separately.
- Krisp does not document durable crash recovery for local material. GRAF keeps
  local custody and idempotent recovery as first-class requirements.
- Switching capture modes in the middle of a meeting may discard prior content
  in Krisp's bot flow. GRAF explicitly forbids destructive mode switching.

## Repository Evidence Map

- Native orchestration: `apps/macos/RecApp/App/TwoBrainRecApp.swift`
- Capture state: `apps/macos/RecApp/Sources/Capture/CaptureSessionController.swift`
- Capture UI/status: `apps/macos/RecApp/Sources/Capture/CaptureControlViewCore.swift`, `CaptureStatusItem.swift`, and `apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift`
- V5 writer/artifacts: `apps/macos/RecApp/Sources/Capture/V5LocalRecordingWriter.swift`
- Upload recovery: `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`
- Cabinet projection: `apps/server/src/twobrain_rec_server/cabinet/queries.py`, `view_models.py`, `rendering.py`
- Access/sharing: `apps/server/src/twobrain_rec_server/cabinet/access.py`, `api/cabinet.py`, `db/models/meeting_access.py`
- Outcomes: `apps/server/src/twobrain_rec_server/db/models/outcomes.py`, `outcomes/`
- Durable orchestration: `apps/server/src/twobrain_rec_server/workflows/temporal_client.py`, `processing_workflow.py`, and `worker.py`
- Langfuse configuration baseline: `apps/server/src/twobrain_rec_server/config.py`, `infra/docker-compose.yml`, and `infra/env/rec.production.env.example`
- Deletion: `apps/server/src/twobrain_rec_server/deletion/`
- Visual baseline: `specs/030-mvp-experience-design-system/`
- Playback timeline: `specs/118-interactive-playback-timeline/`
- Canonical export dependency: merged `specs/120-transcript-export/`, re-verified by T002
