# Implementation Plan: Process Closeout And Issue Truth

**Branch**: `codex/234-process-closeout` | **Date**: 2026-09-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/234-process-closeout/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Make feature allocation bounded and fail-closed, then make task/issue closure
auditable and keep the PR templates aligned with the GitHub Actions gate. The
implementation reuses the existing claim script, validators and guidance; it
does not add a second tracker or a background service.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.11+, Markdown/YAML

**Primary Dependencies**: existing `gh` CLI, GitHub Actions, Spec Kit scripts

**Storage**: Git refs, ignored `.specify/feature.json`, shared local claim file,
GitHub Issues

**Testing**: pytest governance suite, script self-tests, workflow validators

**Risk / Validation Lane**: significant-feature; this changes shared governance,
feature identity and merge/closeout behavior.

**Release Gate**: no production deploy; merge requires GitHub `governance-fast`.

**Target Platform**: GitHub Actions runner and macOS/Linux developer worktrees

**Project Type**: repository governance/tooling

**Performance Goals**: online candidate allocation under 15 seconds; no full
history scan in claim/allocation path.

**Constraints**: no secrets or meeting data; no production mutation; preserve
manual local CI fallback; do not rewrite user worktrees.

**Scale/Scope**: one public repository, parallel feature worktrees, current
issues/PRs and F233 reconciliation.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

PASS. The change preserves exact-SHA checks, reviewer-owned checklists, linear
history, zero required approvals for the sole owner, and the local CI fallback.
It adds no capture, auth, privacy, storage or production behavior. Root
`AGENTS.md` remains a stable router; feature context is per-worktree.

## Validation Plan

1. `python3 scripts/claim-feature.py --self-test` and a live bounded allocation
   rehearsal on a clean worktree.
2. `python3 scripts/check-development-process.py --self-test` and governance
   validators, including PR metadata and changelog checks.
3. Focused pytest for changed governance scripts and `actionlint` for workflow
   syntax.
4. GitHub `governance-fast` on the exact PR SHA; no deploy gate applies.

## Project Structure

### Documentation (this feature)

```text
specs/234-process-closeout/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
scripts/claim-feature.py
scripts/check-development-process.py
scripts/validate-pr-metadata.py
tests/governance/
.github/pull_request_template.md
harness/templates/pull-request.md
docs/agent-guidance/
```

**Structure Decision**: Reuse existing governance scripts, templates and
guidance. Add no new runtime package; add only metadata/spec evidence and the
smallest validator or tests needed to enforce the closeout invariant.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | Existing repository surfaces are sufficient. |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
