# Implementation Plan: Code Optimization

**Branch**: `codex/074-code-optimization` | **Date**: 2026-07-01 |
**Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/074-code-optimization/spec.md`

## Summary

Run a Ponytail-led cleanup slice whose product value is smaller, safer runtime
code. This slice is deletion/shrink-first: inspect real callers and runtime
entrypoints, classify candidates, then implement only the first small batch
where evidence proves the code is dead or redundant and validation preserves the
active product.

## Technical Context

**Language/Version**: Python server, Swift macOS app, shell infra/scripts

**Primary Dependencies**: Existing project dependencies only; no new cleanup
dependency may be added

**Storage**: No schema or storage behavior changes

**Testing**: `pytest` via `uv --project apps/server`, SwiftPM/Xcode commands as
needed for touched macOS paths, shell checks, and repository `infra/scripts/ci-local.sh`

**Risk / Validation Lane**: Significant/high-risk cleanup. Removing code can
break implicit contracts, routes, scripts, packaging, auth/session, deletion,
capture, processing, or deploy behavior.

**Release Gate**: No deploy. Production deploy requires a separate user request.

**Target Platform**: Server runtime, macOS app runtime, infra/script entrypoints

**Project Type**: Self-hosted web service plus macOS desktop app

**Performance Goals**: Reduce maintenance surface without changing user-visible
behavior

**Constraints**:

- No new dependencies
- No split-only PRs counted as optimization
- First implementation PR must have net runtime LOC delta <= 0
- No weakened tests
- No production deploy

**Scale/Scope**:

- Baseline runtime files counted on 2026-07-01: 416 Python/Swift/shell files
- Baseline runtime LOC: Python 35,847; Swift 53,152; shell 5,196

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Capture-first integrity: PASS. Cleanup must not change capture behavior unless
  separately specified and validated.
- Visible consent/user control: PASS. Cleanup must not alter recording visibility
  or stop paths.
- Data boundary/secret discipline: PASS. Evidence must remain metadata-only; no
  secrets or private content in audit notes.
- Deletion truth/lifecycle accounting: PASS. Cleanup around deletion must retain
  truthful reports and lifecycle accounting.
- Spec-driven delivery: PASS. Lane selected as significant/high-risk cleanup and
  full Spec Kit flow is used.

## Validation Plan

1. Build candidate evidence with source searches and runtime entrypoint checks.
2. For the chosen first batch, run the smallest focused test set for touched
   files.
3. Run `@ponytail-review` style diff review before closeout.
4. Run `git diff --check`.
5. Run `infra/scripts/ci-local.sh` before PR because runtime code changes.
6. Report net runtime LOC and dependency delta in the PR.

## Project Structure

### Documentation (this feature)

```text
specs/074-code-optimization/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── contracts/
│   └── cleanup-candidate-contract.md
├── quickstart.md
├── checklists/
│   ├── requirements.md
│   └── cleanup-safety.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/src/       # Python server candidates
apps/server/tests/     # Python validation
apps/macos/            # Swift/macOS candidates and validation
infra/                 # Docker/ops script candidates
scripts/               # repo automation candidates
```

**Structure Decision**: This slice does not introduce new runtime structure.
It removes or shrinks existing runtime code only when evidence and validation
support the change.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
