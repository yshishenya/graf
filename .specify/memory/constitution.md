<!--
Sync Impact Report
Version change: template -> 1.0.0
Modified principles:
- Template principle 1 -> I. Driver-First Capture Integrity
- Template principle 2 -> II. Visible Consent And User Control
- Template principle 3 -> III. Data Boundary And Secret Discipline
- Template principle 4 -> IV. Deletion Truth And Lifecycle Accounting
- Template principle 5 -> V. Spec-Driven Delivery With Testable Gates
Added sections:
- Product And Platform Constraints
- Development Workflow And Quality Gates
Removed sections:
- Template placeholder sections
Templates requiring updates:
- ✅ .specify/templates/plan-template.md
- ✅ .specify/templates/spec-template.md
- ✅ .specify/templates/tasks-template.md
Follow-up items:
- None
-->
# 2brain Rec Constitution

## Core Principles

### I. Driver-First Capture Integrity

2brain Rec MUST deliver the MVP through a macOS virtual audio driver/layer. A
no-driver fallback product is not allowed for MVP. The virtual audio layer MUST
capture local microphone audio and remote speaker audio as separate tracks,
preserve live passthrough when upload, transcription, or server connectivity
fails, and prevent loopback from remote audio into `2brain Rec Microphone`.

Driver implementation, privilege model, installer, signing, notarization,
update, rollback, repair, uninstall, passthrough failure behavior, and QA matrix
MUST be approved before Phase 0 coding starts. Features that touch capture,
routing, recording integrity, buffering, or driver UX MUST define measurable
latency, dropout, routing, install, recovery, and degraded-state requirements.

Rationale: capture integrity is the product. If the audio layer is unreliable,
silent, looped, or opaque, downstream transcription and notes cannot be trusted.

### II. Visible Consent And User Control

Active capture MUST always have a persistent local visible indicator and a
one-action stop path. The product MUST NOT provide user or admin settings that
make active capture invisible. Manual start/stop MUST remain available whenever
workspace policy permits recording.

Assisted auto-start is allowed only as a policy-gated, user-acknowledged,
visible, auditable feature. It MUST be limited to approved routed meeting
targets and MUST NOT start from arbitrary system audio, media playback,
notifications, music, videos, or non-approved apps. Internal-team MVP may operate
without participant-facing notice, but external/customer workspaces MUST select
a notice/legal policy before recording, transcript-only capture, or assisted
auto-start can be enabled.

Rationale: botless capture is powerful and sensitive. Trust depends on visible
state, immediate control, clear policy, and no surprise recording.

### III. Data Boundary And Secret Discipline

2brain Rec-owned meeting data MUST remain in configured owner-controlled
infrastructure by default. MediaScribe and Langfuse are owner-controlled
dependencies for internal MVP only and MUST be represented as configurable,
explicitly allowlisted dependencies for future customer deployments.

Desktop clients MUST never send audio directly to MediaScribe and MUST never
store MediaScribe credentials. Secrets, API keys, passwords, device tokens,
upload tokens, signed URLs, and live credential paths MUST NOT be committed,
logged, exposed in diagnostics, embedded in images, or shipped to clients.
Langfuse traces MUST be metadata-only by default; content-bearing traces require
explicit admin enablement, short retention, RBAC, audit logging, and deletion
participation.

Rationale: the product promise is control. Hidden egress or sloppy secret
handling breaks both security and positioning.

### IV. Deletion Truth And Lifecycle Accounting

Deletion language MUST be truthful about what 2brain Rec controls. Product copy
MUST NOT promise universal erasure outside controlled storage. Preferred wording
is: "Delete this meeting everywhere 2brain Rec controls."

Every feature that creates, transforms, exports, observes, or caches meeting
content MUST register lifecycle artifacts for retention and deletion accounting.
Deletion reports MUST distinguish active server purge, local desktop purge,
backup expiry, Temporal/workflow payload limits, MediaScribe dependency state,
Langfuse trace/content state, diagnostics, external/post-egress limits, and
unreachable clients. If a dependency cannot confirm deletion, the UI and admin
report MUST say so.

Rationale: deletion is not a button; it is a cross-system lifecycle promise.
Precise status is safer than broad claims that the system cannot prove.

### V. Spec-Driven Delivery With Testable Gates

All significant work MUST follow Spec Kit: constitution, specify, clarify, plan,
checklist when risk warrants it, tasks, analyze, then implement. Specifications
MUST be user-value focused and testable. Plans MUST pass the constitution check
before Phase 0 research and again after Phase 1 design. Tasks MUST be grouped by
independently testable user stories and include exact file paths.

High-risk features MUST run `$speckit-clarify`, `$speckit-checklist`, and
`$speckit-analyze` before implementation. High-risk includes driver/audio,
recording start behavior, privacy, auth, secrets, MediaScribe, Langfuse, MinIO,
Postgres, Temporal, Docker, retention, deletion, diagnostics, tray/widget,
onboarding, admin, and brand-distance UX.

Rationale: this product has privacy, driver, and data-lifecycle risk. The work
must be decomposed into reviewable artifacts before code.

## Product And Platform Constraints

- MVP target platform is macOS with Apple Silicon required.
- Windows is a later platform after macOS launch and MUST NOT be represented as
  MVP-supported.
- MVP server target is `2brain.dev` with public URL `https://rec.2brain.dev`.
- `2brain_rec`-owned infrastructure MUST run in Docker containers for MVP.
- Dedicated Postgres and MinIO are required for `2brain_rec`.
- Temporal is the selected durable workflow engine for MVP workflows unless the
  constitution is amended.
- MediaScribe at `https://mediascribe.2brain.pro` is the MVP STT dependency.
- Langfuse at `https://langfuse.2brain.pro` is the MVP LLM observability
  dependency.
- Default storage mode retains audio plus transcript; transcript-only mode is
  required.
- User deletion deletes the whole meeting in MVP; partial artifact deletion is
  deferred unless explicitly specified.
- UI MUST use an original `2brain Rec` design system and pass brand-distance
  review before private alpha.

## Development Workflow And Quality Gates

Required sequence for product/code work:

1. `$speckit-constitution` when governance changes are needed.
2. `$speckit-specify` for each feature or architectural slice.
3. `$speckit-clarify` before planning unless the slice is trivial and low risk.
4. `$speckit-plan` to produce plan, research, data model, contracts, quickstart.
5. `$speckit-checklist` for requirement-quality gates on high-risk areas.
6. `$speckit-tasks` to produce dependency-ordered, story-scoped tasks.
7. `$speckit-analyze` to detect cross-artifact issues before implementation.
8. `$speckit-implement` only after blockers are resolved.

Required quality gates:

- No implementation starts with unresolved critical Spec Kit analyze findings.
- No implementation starts with unresolved constitution violations.
- Driver features require driver QA and installer/recovery gates.
- Data features require artifact lifecycle, retention, deletion, and audit gates.
- External dependency features require egress, secret, timeout, failure, and
  retention/deletion gates.
- UI features require visible-state, accessibility, localization, and
  brand-distance gates.
- Deployment features require Docker secrets, health checks, backups, restore,
  rollback, log redaction, and disk-full behavior.

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

**Version**: 1.0.0 | **Ratified**: 2026-05-27 | **Last Amended**: 2026-05-27
