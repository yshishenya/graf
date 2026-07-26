<!--
Sync Impact Report
Version change: 4.1.0 -> 4.2.0
Modified principles:
- Data Boundary And Secret Discipline -> Plaintext Observability For Internal
  MVP: complete transcript and model content are intentionally retained in
  Langfuse and the Generation Call ledger, while Temporal History retains the
  complete transcript, all without application-layer encryption, redaction, or
  GRAF-managed observability deletion.
- Deletion Truth And Lifecycle Accounting: meeting deletion remains truthful
  and complete inside GRAF, while Langfuse observations and Temporal History
  are explicitly retained under operator-managed platform retention.
- Visible Consent And User Control: the approved target-scoped automatic
  recording flow, countdown, opt-in checkbox, and native-app allowlist are
  preserved product requirements and cannot be removed by a cleanup or UX
  simplification without an explicit superseding feature decision.
Added sections:
- Public macOS Distribution And Update Integrity: public app and package
  releases use only Developer ID, Apple notarization, stapling and Gatekeeper;
  local/self-signed paths are never public release or update paths.
Removed sections:
- None.
Templates requiring updates:
- ✅ reviewed .specify/templates; no structural change needed.
- ✅ updated AGENTS.md for the internal-MVP plaintext observability policy.
- ✅ updated docs/agent-guidance/product-gates.md.
- ✅ updated docs/prd-voice-layer-final.md AI boundary.
- ✅ this amendment is propagated to the active recording specification,
  current product status, and release changelog by Feature 124.
Follow-up items:
- Revisit encryption, redaction, and observability deletion only in a later
  stabilization feature when the operator chooses to add those controls.
- Do not remove automatic recording behavior without a new approved feature,
  migration/compatibility note, and explicit product-owner decision.
- First migration from a legacy local/self-signed app to Developer ID is a
  manual notarized-package bootstrap; the live Sparkle feed MUST NOT be
  replaced until the migration validator proves safe continuity.
-->
# 2brain Rec Constitution

## Core Principles

### I. Capture-First MVP Integrity

2brain Rec MUST deliver the MVP through the safest native macOS capture path
that can reliably produce separate local microphone and incoming/system-audio
tracks without overheating, hanging CoreAudio, hiding capture, or requiring
fragile meeting-app routing. The MVP capture path is system-audio-first:
Screen/System Audio capture for incoming audio plus explicit microphone capture
for the local speaker. The superseded separate routing implementation is
removed and
MUST NOT be packaged, started, repaired, or used as a fallback. Future advanced
routing requires a new approved architecture, safety case, packaging model,
rollback plan, and validation slice.

Capture implementation, permission model, installer/signing behavior, update,
rollback, repair, degraded-state behavior, and QA matrix MUST be approved
before Phase 0 coding starts. Features that touch capture, recording integrity,
buffering, permissions, screen/system audio, microphone capture, or future
advanced-routing UX MUST define measurable latency, dropout, track alignment,
authorization, recovery, and degraded-state requirements.

Rationale: capture integrity is the product. The prior separate-routing path
produced repeated CoreAudio hangs and CPU runaway during `019` validation. If
the audio layer is unreliable, silent, looped, overheated, or opaque,
downstream transcription and notes cannot be trusted.

### II. Visible Consent And User Control

Active capture MUST always have a persistent local visible indicator and a
one-action stop path. The product MUST NOT provide user or admin settings that
make active capture invisible. Manual start/stop MUST remain available whenever
workspace policy permits recording.

The approved target-scoped automatic-recording flow is a required product
capability, not removable legacy. Settings MUST expose the meeting-detection
control and a complete allowlist of verified native meeting applications. Each
application MUST have an explicit, reversible auto-record permission. A user
MUST be able to choose "always record this application" from the meeting
prompt, and that choice MUST persist in the target-scoped settings.

For a detected approved target without saved auto-record permission, the
product MUST show a visible prompt with the designed countdown timer and
automatic start at its expiry, while retaining an immediate manual start,
dismissal, and one-action Stop. Saved auto-record permission MAY start capture
without asking again, but the local visible indicator, one-action Stop, and all
capture prerequisites remain mandatory. Automatic recording MUST be limited to
approved meeting targets or explicit user-selected capture scopes and MUST NOT
start from arbitrary system audio, media playback, notifications, music,
videos, or non-approved apps.

Assisted auto-start is allowed only as a policy-gated, user-acknowledged,
visible, auditable feature. The countdown and automatic-start path MUST remain
gated by meeting confidence, target permission, microphone/system-audio
authorization, storage readiness, suppression state, and the current capture
policy. A cleanup, refactor, or UX simplification MUST NOT remove the timer,
auto-start, opt-in checkbox, or application allowlist. Removing or narrowing
this contract requires a new approved Spec Kit feature, compatibility and
migration notes, updated tests, and an explicit product-owner decision.
Internal-team MVP may operate without participant-facing notice, but
external/customer workspaces MUST select a notice/legal policy before
recording, transcript-only capture, or assisted auto-start can be enabled.

Rationale: botless capture is powerful and sensitive. Trust depends on visible
state, immediate control, clear policy, and no surprise recording.

### III. Plaintext Observability For Internal MVP

2brain Rec-owned meeting data MUST remain in configured owner-controlled
infrastructure by default. An external SaaS dependency MAY be used only after
an explicit approved feature or constitution decision defines its destination,
region, data classes, secret custody, timeout/failure behavior, retention,
deletion limits, and rollback. MediaScribe remains an owner-controlled internal
dependency. Langfuse Cloud EU is an approved external dependency for
internal-MVP AI observability and prompt control and MUST remain configurable
and explicitly allowlisted for every deployment.

AI notes that require transcript content MUST leave GRAF only through an
owner-controlled, explicitly allowlisted LiteLLM gateway. GRAF MUST NOT contain
direct provider-specific credentials or direct provider endpoints. Each
LiteLLM route that may receive meeting content MUST be explicitly approved by
the deployment operator with its destination, data class, retention/deletion
limits, and rollback recorded. Langfuse Prompt Config MUST be the single
editable authority for the prompt, selected LiteLLM model route, allowlisted
request-level generation settings, and structured-output schema. GRAF MUST
validate and atomically pin an exact promoted prompt/config version before
model execution. Changing the selected model route or generation settings MUST
be possible through a promoted Langfuse version without workflow-code changes.
LiteLLM remains authoritative only for mapping that selected route to an
approved upstream provider and for upstream secret custody. The application
MUST preserve both the selected route and the actual provider/model provenance
returned by the gateway when available.

Desktop clients MUST never send audio directly to MediaScribe and MUST never
store MediaScribe credentials. Secrets, API keys, passwords, device tokens,
upload tokens, signed-URL secrets, and live credential paths MUST NOT be
committed, logged, exposed in diagnostics, embedded in images, or shipped to
clients.

For every completed model call whose response reaches GRAF, exactly one
Langfuse `generation` observation MUST contain the exact compiled logical model
request, the complete pinned canonical transcript revision, the raw model
response, and the locally validated result. The surrounding AI workflow
observations MAY contain the same plaintext meeting/model content when it makes
the execution easier to debug. GRAF MUST NOT redact, mask, truncate, encrypt,
or delete this observability content. Once a completed response is durably
captured in the retained Generation Call ledger, one sole observability
publisher MUST keep its deterministic delivery pending and retry until Langfuse
confirms that observation; candidate readiness MUST NOT wait for confirmation,
and retry MUST NOT repeat inference. Meeting deletion MUST NOT cancel or suppress
delivery for a completed retained call. A call that may have left GRAF but
crashes before its response is durably captured MUST be reported as `ambiguous`;
GRAF MUST NOT fabricate missing content or claim exactly-once provider egress.
Langfuse MUST NOT become the source of truth for meeting, workflow, acceptance,
or deletion state.

Outcome-generation Temporal History MUST contain the complete pinned canonical
transcript in plaintext. The workflow MAY use deterministic plaintext chunks
to remain below Temporal request, transaction, and History limits, and those
chunks MUST reconstruct the complete transcript without omission. GRAF MUST NOT
install a transcript PayloadCodec, application-layer encryption, masking,
redaction, or workflow-history deletion for the internal MVP. Workflow inputs,
activity inputs/results, and failure details MAY contain full meeting/model
content when required for execution or debugging. Search Attributes and Memo
MUST stay bounded, low-cardinality operational fields because they are indexes,
not transcript storage. Observability retention is controlled by the operator's
Langfuse and Temporal configuration; GRAF MUST NOT shorten it or delete traces
or histories when a meeting is deleted.

Runtime credentials, API keys, authorization headers, cookies, passwords,
signed-URL secrets, and raw audio are not model inputs and MUST NOT be
deliberately attached as observability attributes. This rule does not authorize
content-changing transcript filters: the canonical transcript remains complete
and verbatim even when spoken text resembles a credential. The application MUST
select the relevant transcript/model fields explicitly, without a redaction or
masking pipeline. Recording and transcription MUST continue when Langfuse is
unavailable; trace export MAY retry with deterministic identity and MUST NOT
repeat a completed model call.

Prompt-control failure MAY use only an exact, integrity-checked last-known-good
export of a previously promoted Langfuse prompt/config version. If neither
Langfuse nor that verified snapshot is available, recording and transcription
MUST continue while AI generation waits in a truthful bounded dependency state;
GRAF MUST NOT invent or silently substitute model settings from code.

Prompt optimization MUST run outside the user request path as durable,
deployment-operator-controlled work. Workspace administrators MUST NOT control
project-global prompt labels. Optimizers MAY publish exact numeric candidate
prompt versions and evaluation evidence without a manually assigned deployment
label, but MUST NOT move production without explicit
operator approval, held-out validation, privacy review, serialized
expected-source verification, protected-label plus sole mutation credential
readiness, and a rollback target. Automated promotion MUST remain disabled when
that readiness is unavailable. Feature 121 prompt optimization remains
synthetic-only to keep the first version small. Synthetic optimization
observations and Temporal histories MAY contain complete plaintext inputs,
outputs, judge feedback, and optimizer state. Using real meetings for
optimization remains a separate product decision.

Rationale: during the internal MVP, complete debuggability is more valuable
than building a security subsystem before the product flow stabilizes. The
operator owns the Langfuse, LiteLLM, and Temporal environments and explicitly
accepts plaintext observability content there.

### IV. Deletion Truth And Lifecycle Accounting

Deletion language MUST be truthful about what 2brain Rec controls. Product copy
MUST NOT promise universal erasure outside controlled storage. Preferred wording
is: "Delete this meeting everywhere 2brain Rec controls."

Every feature that creates, transforms, exports, observes, or caches meeting
content MUST register lifecycle artifacts for truthful accounting. Deletion
reports MUST distinguish active GRAF server purge, local desktop purge, backup
expiry, MediaScribe dependency state, and unreachable clients. They MUST also
state that the GRAF Generation Call ledger, Langfuse observations, and Temporal
History are retained under the operator's observability policy and are not
deleted by meeting deletion. The product MUST NOT present these retained
observability copies as a failed GRAF purge.

Rationale: deletion is not a button; it is a cross-system lifecycle promise.
Precise status is safer than broad claims that the system cannot prove.

### V. Public macOS Distribution And Update Integrity

Every public macOS application and installer package MUST use an Apple-issued
Developer ID Application or Developer ID Installer identity as applicable,
hardened runtime, a secure timestamp, successful Apple notarization, a valid
staple, and Gatekeeper acceptance before publication. Public `/download`,
GitHub Release assets, versioned update archives, and the live Sparkle feed MUST
not contain an ad-hoc, local self-signed, or owner-only artifact.

The ordinary Sparkle update path MUST preserve the same bundle identifier,
Developer ID team, designated-requirement compatibility, public feed, and
Sparkle trust generation. A migration from a legacy local/self-signed client
to Developer ID MUST use a separately labelled, notarized `.pkg` bootstrap and
MUST keep the old appcast unchanged until an explicit migration validator has
proved the transition safe. The first Developer ID bootstrap MUST NOT be
represented as an ordinary in-app update.

Release scripts and documentation MUST fail closed when a local/self-signed
identity is selected for a public lane. Local or ad-hoc signing MAY remain only
in isolated development fixtures and historical metadata-only receipts, never
as an active release instruction or public fallback.

Rationale: macOS signing identity is part of application continuity and
permission retention. Publishing a local signature as if it were a public
update can strand installed clients, trigger unexpected permission prompts, or
weaken Gatekeeper trust.

### VI. Spec-Driven Delivery With Testable Gates

All work MUST start by selecting an explicit risk/validation lane. Significant
work MUST follow Spec Kit: constitution, specify, clarify, plan, checklist when
risk warrants it, tasks, analyze, then implement. Low-risk direct changes MAY
skip new Spec Kit artifacts only when they do not touch high-risk areas and the
scoped validation is recorded in the final response or pull request.
Specifications MUST be user-value focused and testable. Plans MUST pass the
constitution check before Phase 0 research and again after Phase 1 design. Tasks
MUST be grouped by independently testable user stories and include exact file
paths.

High-risk features MUST run `$speckit-clarify`, `$speckit-checklist`, and
`$speckit-analyze` before implementation. High-risk includes capture/audio,
recording start behavior, privacy, auth, secrets, MediaScribe, Langfuse, MinIO,
Postgres, Temporal, Docker, retention, deletion, diagnostics, tray/widget,
onboarding, admin, and brand-distance UX. If lane selection is unclear, choose
the stricter lane.

Rationale: this product has privacy, capture, and data-lifecycle risk. The work
must be decomposed into reviewable artifacts before code.

## Product And Platform Constraints

- MVP target platform is macOS with Apple Silicon required.
- Windows is a later platform after macOS launch and MUST NOT be represented as
  MVP-supported.
- Platform capture and routing must be implemented on native OS primitives first
  for each operating system slice; cross-platform abstractions may be used only
  where they do not own capture authorization, real-time audio capture, local
  recording truth, permission flows, or installer signing/notarization.
- For the MVP, this means Swift/Cocoa/ScreenCaptureKit/AVFoundation/Core Audio
  where appropriate for the macOS app. The removed routing implementation is
  not a dormant option. Any future advanced routing requires a new approved
  spec, implementation, safety gate, packaging model, and rollback plan.
- MVP server target is `2brain.dev` with public URL `https://rec.2brain.pro`.
- `2brain_rec`-owned infrastructure MUST run in Docker containers for MVP.
- Dedicated Postgres and MinIO are required for `2brain_rec`.
- Temporal is the selected durable workflow engine for MVP workflows unless the
  constitution is amended.
- MediaScribe at `https://mediascribe.2brain.pro` is the MVP STT dependency.
- An owner-controlled, explicitly allowlisted LiteLLM deployment is the MVP LLM
  gateway for content-bearing notes generation. Application workers MUST use
  its OpenAI-compatible contract and MUST NOT call upstream model providers
  directly.
- A private Langfuse Cloud EU project at `https://cloud.langfuse.com` is the
  approved internal-MVP LLM observability and prompt-control dependency; public
  trace publishing MUST remain disabled, and self-hosted/customer deployments
  MUST configure and allowlist their own approved destination.
- Langfuse observations retain the complete plaintext transcript, logical
  request, raw model response, and validated result for internal-MVP debugging.
- Temporal History retains the complete plaintext transcript and may naturally
  retain other workflow/model content; the exact full request/response/result is
  guaranteed in Langfuse and the Generation Call ledger rather than duplicated
  deliberately. Deterministic plaintext chunks keep payloads within Temporal
  limits. No transcript codec or application-layer encryption is used.
- GRAF does not redact, mask, truncate, or delete Langfuse or Temporal
  observability content. Their retention is operator-managed.
- Langfuse Prompt Config is the versioned authority for prompt text, selected
  LiteLLM model route, request-level generation settings, and structured-output
  schema. LiteLLM owns upstream routing and secrets, not product model policy.
- Durable model calls and offline prompt-optimization runs use Temporal.
  Protected production prompt labels require explicit deployment-operator promotion after
  evaluation; optimization never auto-promotes.
- Default storage mode retains audio plus transcript; transcript-only mode is
  required.
- User deletion deletes the whole meeting in MVP; partial artifact deletion is
  deferred unless explicitly specified.
- UI MUST use an original `2brain Rec` design system and pass brand-distance
  review before production rollout.

## Development Workflow And Quality Gates

Required sequence for significant product/code work:

1. `$speckit-constitution` when governance changes are needed.
2. `$speckit-specify` for each feature or architectural slice.
3. `$speckit-clarify` before planning unless the slice is trivial and low risk.
4. `$speckit-plan` to produce plan, research, data model, contracts, quickstart.
5. `$speckit-checklist` for requirement-quality gates on high-risk areas.
6. `$speckit-tasks` to produce dependency-ordered, story-scoped tasks.
7. `$speckit-analyze` to detect cross-artifact issues before implementation.
8. `$speckit-implement` only after blockers are resolved.

Low-risk direct lanes are allowed for read-only investigation, mechanical
documentation, and tiny code changes only when applicable product gates are
unchanged. They still require the smallest relevant validation, and they MUST
escalate to the full sequence if they touch a high-risk domain or shared
behavior. Process/governance surfaces such as `AGENTS.md`, constitution,
`docs/agent-guidance/`, Spec Kit templates, PR templates, release policy, and
bootstrap/extension tooling are not docs-only unless the edit is strictly
typo/link-only.

Required quality gates:

- Every implementation records the selected validation lane and why it is
  sufficient.
- No implementation starts with unresolved critical Spec Kit analyze findings.
- No implementation starts with unresolved constitution violations.
- Capture features require permission, system-audio, microphone, track
  alignment, no-overheat, and local recording truth gates.
- A new advanced-routing architecture, if proposed, requires its own QA matrix,
  installer/recovery gates where applicable, Core Audio safety/resource gates,
  and rollback evidence before it can affect product behavior.
- Data features require artifact lifecycle, retention, deletion, and audit gates.
- External dependency features require egress, secret, timeout, failure, and
  retention/deletion gates.
- UI features require visible-state, accessibility, localization, and
  brand-distance gates.
- Deployment features require Docker secrets, health checks, backups, restore,
  rollback, log redaction, and disk-full behavior.
- Production deployment runs only when a release/deploy gate is explicitly met.

## Governance

This constitution supersedes conflicting guidance in specs, plans, tasks,
implementation notes, and ad hoc instructions. If a lower-level artifact
conflicts with this constitution, the artifact MUST be corrected or the
constitution MUST be explicitly amended first.

Amendment procedure:

- Amendments MUST update this file and include a Sync Impact Report.
- Amendments MUST update dependent templates when they change required gates or
  artifact structure.
- Versioning follows semantic versioning:
  - MAJOR for removing or redefining core principles.
  - MINOR for adding principles, sections, or material governance requirements.
  - PATCH for clarifications that do not change obligations.
- Every feature plan MUST perform a constitution check before Phase 0 research
  and after Phase 1 design.
- Every implementation review MUST verify that tasks and code preserve the
  applicable constitution gates.

**Version**: 4.2.0 | **Ratified**: 2026-05-27 | **Last Amended**: 2026-07-26
