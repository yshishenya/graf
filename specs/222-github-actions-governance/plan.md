# Implementation Plan: Автоматические SHA-bound PR-проверки

**Branch**: `codex/222-github-actions-governance` | **Date**: 2026-08-31 | **Spec**: [spec.md](spec.md)

**Umbrella issue**: [#6155](https://github.com/yshishenya/graf/issues/6155)

## Summary

Добавить один bounded GitHub Actions workflow для PR, который вызывает уже
существующий fast lane, проверяет exact SHA, отменяет устаревшие запуски и
публикует только безопасное metadata-only evidence. После contract validation
оператор отдельно включает Actions и required check на `master`.

## Technical Context

**Language/Version**: YAML, POSIX shell, Python 3.9+ stdlib

**Primary Dependencies**: существующие `infra/scripts/ci-local.sh`,
`scripts/emit-ci-evidence.py`, `scripts/validate-ci-evidence.py`, GitHub Actions

**Storage**: ephemeral runner workspace; uploaded JSON artifact with allowlisted
metadata only; no product database changes

**Testing**: workflow contract tests, validator tests, local `--fast` on the
feature SHA, GitHub PR run after merge to a test branch

**Risk / Validation Lane**: `significant-feature`; governance/CI boundary with
mandatory clarify, checklist, analyze and convergence

**Release Gate**: no product release or deployment; Actions/branch-protection
changes are an explicit post-merge operator action

## Constitution Check

- Capture-first MVP integrity: PASS; no capture code touched.
- Plaintext observability: PASS; only metadata-only evidence is uploaded.
- Repository hygiene: PASS; no secrets or private paths in artifacts.
- Spec-driven delivery: PASS; full GRAF sequence and reviewer-owned checklist.
- Ponytail: PASS; reuse existing local CI/evidence scripts and add one thin workflow.

## Architecture and Data Flow

```text
pull_request(head_sha)
  -> concurrency group pr-${{ number }} (cancel stale)
  -> checkout exact head_sha
  -> compare requested/checkout/source SHA
  -> infra/scripts/ci-local.sh --fast
  -> validate metadata-only evidence
  -> upload one safe artifact
```

The workflow must never call `cd-remote.sh`, release publication, migration
mutation, Docker volume deletion, or product secret paths. `workflow_dispatch`
requires an explicit full SHA and is for audit/retry only.

## Implementation Phases

### Phase 0 — Contract and reviewer gate

- finalize exact job/check name and artifact schema;
- generate security/infra checklist and run analyze;
- sync executable tasks to GitHub issues.

### Phase 1 — Workflow and tests

- add `.github/workflows/governance-fast.yml` with exact-SHA guard and
  `cancel-in-progress: true`;
- add contract tests for YAML text, event scope, forbidden commands, artifact
  allowlist and stale status;
- add a changelog fragment and operator documentation.

### Phase 2 — GitHub enablement and convergence

- validate on a disposable PR/test branch;
- enable Actions and required check on `master` only after evidence;
- rerun analyze/converge and record the API snapshot in the PR.

## Project Structure

```text
.github/workflows/governance-fast.yml
scripts/validate-governance-workflow.py
tests/governance/test_governance_workflow.py
docs/agent-guidance/release-and-validation.md
changes/unreleased/F222.yaml
specs/222-github-actions-governance/{spec,plan,tasks,quickstart}.md
```

## Complexity Tracking

No new service, dependency, database schema, or parallel Dev runtime is
introduced. GitHub configuration is intentionally separate from product
release automation.
