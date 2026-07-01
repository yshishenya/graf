# Feature Specification: Deep Architecture Audit

**Feature Branch**: `codex/072-deep-architecture-audit`

**Created**: 2026-06-30

**Status**: Draft

**Input**: User description: "072 - Deep Architecture Audit under Spec Kit SDD for Crisp / 2brain Rec. First stage must not change code or delete files. Build an evidence map of architecture, dependencies, and runtime flow, then produce a safe small-PR refactor roadmap."

## Clarifications

### Session 2026-06-30

- Lane: significant architecture / high-risk read-only audit. The first stage may create Spec Kit and audit documentation only; product/runtime code, dependency declarations, migrations, generated release files, and production state must not be changed.
- Scope: audit the whole product surface, including server, macOS app and capture layer, infra, scripts, specs, docs, dependency declarations, Docker/runtime dependencies, release/deploy path, and cross-boundary runtime flows.
- Safety rule: no file or dependency may be classified as removable without caller evidence, runtime/entrypoint evidence, owner/control-boundary review, and a focused validation requirement. Actual deletion belongs to later approved refactor PRs.
- Ponytail rule: prefer the smallest evidence-backed roadmap, reuse existing helpers and checks, avoid new tooling unless the existing stack cannot produce the required graph, and never lower privacy, capture, deletion, auth, or deploy validation gates.
- Release rule: 072 does not deploy to production and must not be mixed with the 071 release/refactor work.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Map The Real Architecture Before Refactoring (Priority: P1)

A maintainer can review one evidence-backed architecture map that explains the current product shape across capture, desktop, server, processing, storage, review, deletion, support, and deploy surfaces before any refactor starts.

**Why this priority**: The product now spans high-risk capture, auth, storage, AI, deletion, and deployment boundaries. Refactoring without a trusted map risks breaking implicit contracts.

**Independent Test**: Review the architecture audit artifacts and confirm they cite inspected files, entrypoints, dependencies, and runtime-flow evidence for every audited product area.

**Acceptance Scenarios**:

1. **Given** the repository has server, macOS, infra, scripts, specs, docs, and dependency surfaces, **When** the audit map is produced, **Then** each surface has inspected-source evidence, responsibility boundaries, known entrypoints, and confidence/limits.
2. **Given** a runtime flow crosses desktop, server, storage, workers, or web review, **When** the audit describes it, **Then** the flow names the owning boundary, exchanged artifact or state, privacy/deletion implications, and validation evidence needed before refactor.
3. **Given** an architecture area already has acceptable boundaries, **When** the audit reports it, **Then** the report explicitly says what is healthy and why it should not be churned.

---

### User Story 2 - Classify Architecture Risks Without Editing Code (Priority: P1)

A maintainer can see which architecture issues are real, which only look suspicious, and which require a separate Spec Kit slice before any code is changed.

**Why this priority**: Large files, old specs, future driver code, shell scripts, framework hooks, and runtime-only dependencies can all look disposable. The first stage must separate proof from guesswork.

**Independent Test**: Review the risk register and confirm every finding is classified as `delete now`, `split soon`, `keep intentionally`, or `risky / needs spec` with evidence and validation requirements.

**Acceptance Scenarios**:

1. **Given** a file, dependency, module, or script appears unused, **When** the audit classifies it, **Then** the classification includes caller search, entrypoint/runtime role, dependency role, and validation needed before deletion.
2. **Given** a module mixes responsibilities, **When** the audit classifies it, **Then** the report distinguishes safe presentation splits from cross-boundary refactors that need their own slice.
3. **Given** a suspicious artifact supports capture, privacy, deletion, auth, MediaScribe, Langfuse, MinIO, Postgres, Temporal, WebView/cabinet, or deploy, **When** the audit classifies it, **Then** the default decision is `keep intentionally` or `risky / needs spec` unless strong contrary evidence exists.

---

### User Story 3 - Produce A Small-PR Refactor Roadmap (Priority: P1)

A maintainer can choose the next safe refactor batch from a roadmap that orders small PRs by risk, validation gates, and expected value.

**Why this priority**: The user asked for a deep audit, not a broad rewrite. The useful output is a sequenced roadmap where each PR can be reviewed, validated, and stopped independently.

**Independent Test**: Review the roadmap and confirm each proposed PR has a bounded scope, excluded surfaces, expected risk, required checks, rollback/stop condition, and traceability back to audit findings.

**Acceptance Scenarios**:

1. **Given** the audit identifies a safe deletion, **When** the roadmap proposes it, **Then** the proposal names the exact files or dependency records, required focused validation, and no-go conditions.
2. **Given** the audit identifies a large-file or boundary split, **When** the roadmap proposes it, **Then** the proposal keeps one responsibility boundary per PR and avoids combining presentation, data, auth, lifecycle, and deploy changes.
3. **Given** the audit identifies risky architecture work, **When** the roadmap reports it, **Then** the item is deferred to a separate Spec Kit slice rather than hidden inside cleanup.

---

### User Story 4 - Preserve Product Trust Boundaries During Audit (Priority: P1)

An owner can trust that the audit does not leak private data, mutate production, weaken product gates, or overstate deletion/capture guarantees.

**Why this priority**: The audit touches the most sensitive areas of 2brain Rec, including meeting content lifecycle, MediaScribe, Langfuse, storage, auth/session/device, desktop WebView, and production deploy scripts.

**Independent Test**: Review the audit evidence and quickstart to confirm all evidence is metadata-only, production deploy is excluded, and boundary-specific gates remain visible.

**Acceptance Scenarios**:

1. **Given** the audit inspects meeting, transcript, audio, diagnostic, or evidence paths, **When** artifacts are recorded, **Then** committed evidence contains no raw audio, transcript text, credentials, tokens, signed URLs, private local paths, or private meeting content.
2. **Given** a proposed refactor touches auth/session/device, privacy, deletion/retention, MediaScribe, Langfuse, MinIO/Postgres/Temporal, capture, or WebView/cabinet boundaries, **When** it enters the roadmap, **Then** it includes the boundary-specific checks required before implementation.
3. **Given** production deploy scripts are inspected, **When** 072 completes, **Then** no deploy or production smoke has been executed unless a later explicit user request authorizes it.

### Edge Cases

- A file has no direct imports but is loaded by a package manifest, shell script, Docker entrypoint, migration side effect, template include, static asset reference, test harness, or macOS resource bundle.
- A dependency appears unused in source search but is required by CLI execution, runtime image startup, database driver loading, ASGI behavior, test plugins, or generated constraints.
- A large server or desktop file is a real split candidate but mixes high-risk policy with low-risk presentation code.
- Old specs and docs appear stale but still encode accepted product constraints or evidence history.
- Future virtual driver code is not MVP-critical but may still be needed for installed-app cleanup, compatibility, or future advanced-routing rollback evidence.
- A runtime flow cannot be fully proven statically and needs dynamic validation before a refactor PR.
- The active checkout contains unrelated work, stale feature state, or a branch from another slice; 072 must stay anchored to a clean worktree from fresh `origin/master`.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The feature MUST record the selected lane as significant architecture / high-risk read-only audit and MUST prohibit product/runtime code changes, dependency removals, file deletions, and production deploy during the first stage.
- **FR-002**: The feature MUST use `specs/072-deep-architecture-audit/` as the active Spec Kit slice and MUST NOT mix 072 artifacts with 071 release or refactor artifacts.
- **FR-003**: The audit MUST inspect server, macOS, infra, scripts, specs, docs, dependency declarations, release/deploy path, production Docker/runtime dependency surfaces, and current product baseline documents.
- **FR-004**: The audit MUST build an import/dependency graph for Python server code, Swift package targets, shell/infra entrypoints, and production Docker/runtime dependencies.
- **FR-005**: The audit MUST describe the runtime flows for capture to local package, upload/ingest, processing, cabinet/review, deletion, export, support, and deploy.
- **FR-006**: The audit MUST identify architecture risks including mixed responsibilities, oversized files, weak boundaries, duplicate logic, implicit contracts, dead abstractions, stale dependencies, and stale documentation or spec conflicts.
- **FR-007**: Every finding MUST be classified as `delete now`, `split soon`, `keep intentionally`, or `risky / needs spec`.
- **FR-008**: Every `delete now` finding MUST include caller/runtime evidence and focused validation required before a later deletion PR.
- **FR-009**: Every `split soon` finding MUST name the current responsibility mix, the proposed smaller boundary, and at least one safe PR boundary.
- **FR-010**: Every `keep intentionally` finding MUST explain the contract, runtime role, evidence role, or product gate that makes the item intentional.
- **FR-011**: Every `risky / needs spec` finding MUST name the boundary risk and the separate Spec Kit slice or clarification required before implementation.
- **FR-012**: The audit MUST separately assess capture, auth/session/device, privacy, deletion/retention, MediaScribe, Langfuse, MinIO/Postgres/Temporal, desktop WebView/cabinet, and release/deploy boundaries.
- **FR-013**: The audit MUST include a small-PR refactor roadmap where each batch has scope, excluded surfaces, expected benefit, risk level, validation gates, and stop/rollback conditions.
- **FR-014**: The audit MUST identify where the architecture is already acceptable and should be preserved to avoid churn.
- **FR-015**: The audit MUST keep evidence metadata-only and MUST NOT commit raw audio, transcript text, credentials, tokens, signed URLs, private local paths, or private meeting content.
- **FR-016**: The audit MUST apply Ponytail criteria by reusing existing repo tools and checks first, avoiding new dependencies unless existing tools cannot produce the required evidence, and preferring minimal refactor batches over broad rewrites.
- **FR-017**: The audit MUST produce `spec.md`, `plan.md`, `research.md`, `data-model.md` where useful, `contracts/`, `quickstart.md`, `tasks.md`, audit docs, and a refactor roadmap before implementation is considered.
- **FR-018**: The final audit output MUST answer in plain language where the architecture is healthy, where it hurts, what can be safely removed, what needs separate PRs, and which checks are needed before each refactor batch.

### Key Entities

- **Architecture Surface**: A product area such as server, macOS capture, desktop shell, infra, scripts, specs, docs, dependencies, or release/deploy path with responsibilities and entrypoints.
- **Dependency Graph**: A recorded relationship map covering imports, package targets, shell entrypoints, Docker/runtime components, and cross-surface calls.
- **Runtime Flow**: A user or system journey crossing surfaces, artifacts, state transitions, trust boundaries, and validation points.
- **Architecture Finding**: A documented risk or healthy boundary with location, evidence, classification, severity, owner surface, and validation requirement.
- **Refactor Batch**: A later small PR proposal with one bounded change goal, excluded areas, validation commands, and stop/rollback condition.
- **Boundary Gate**: A product safety check for capture, auth/session/device, privacy, deletion/retention, MediaScribe, Langfuse, MinIO/Postgres/Temporal, WebView/cabinet, or deployment.
- **Evidence Record**: Metadata-only proof collected by static inspection, existing test commands, graph generation, or documentation review.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of required surfaces in FR-003 have an audit section with inspected-source evidence, entrypoints, and confidence/limits.
- **SC-002**: 100% of findings use one of the four required classifications and include evidence plus a validation requirement or explicit reason validation is deferred.
- **SC-003**: The dependency graph covers Python server imports, Swift package targets, shell/infra entrypoints, and production Docker/runtime dependencies.
- **SC-004**: The runtime-flow map covers all required flows from capture through deploy/support without private content in committed evidence.
- **SC-005**: The roadmap contains only small PR batches, and every batch names required checks before implementation.
- **SC-006**: No product/runtime code files, dependency declarations, lockfiles, migrations, generated release files, or production state are changed by the first-stage audit.
- **SC-007**: The final report answers the five user questions plainly and distinguishes proven evidence from inference.

## Assumptions

- The worktree for 072 is a clean branch/worktree from fresh `origin/master`.
- Existing project scripts and standard command-line tools are enough to build the first dependency and entrypoint evidence map.
- Dynamic runtime validation may be required before later refactor PRs, but 072 itself stops at documentation, graph evidence, and roadmap generation.
- GitHub issue sync and production deploy are out of scope for this first-stage read-only audit unless the user explicitly asks later.
