# Implementation Plan: Надёжный allocator свежих Feature ID

**Branch**: `codex/225-feature-id-allocator` | **Date**: 2026-08-31 | **Spec**: [spec.md](spec.md)

**Umbrella issue**: [#6189](https://github.com/yshishenya/graf/issues/6189)

## Summary

Устранить ложную коллизию, фильтруя только Codex service refs до извлечения
Feature ID, и закрепить поведение regression test. Остальная collision safety
не меняется.

## Technical Context

**Language/Version**: Python 3.9+ stdlib

**Primary Dependencies**: `scripts/claim-feature.py`, pytest/governance tests,
GitHub CLI/API

**Storage**: shared local claim lock/state; no schema or product data changes

**Testing**: self-test, validator safety tests, exact-SHA fast CI

**Risk / Validation Lane**: `significant-feature`; governance change with
clarify, checklist, analyze, task sync and convergence

**Release Gate**: no product release/deploy; reusable harness release remains
separate

## Constitution Check

- Capture/privacy/product runtime: PASS; untouched.
- Feature traceability: PASS; issue #6189 and allocator regression test.
- Repository hygiene: PASS; no private refs in committed evidence.
- Spec-driven delivery: PASS.
- Ponytail: PASS; one namespace guard, no dependency.

## Architecture and Data Flow

```text
git refs -> service namespace filter -> canonical numeric branch IDs
spec dirs + GitHub markers ------------------------------┘
                         -> occupied set -> next_available / claim
```

## Implementation Phases

### Phase 0 — Contract and reviewer gate

- finalize service-ref boundary;
- generate governance checklist;
- run analyze and sync task issues.

### Phase 1 — Filter and regression tests

- filter `codex/turn-diffs/captures/` in `_ids_from_refs`;
- add self-test and validator safety fixture.

### Phase 2 — Validation and convergence

- run self-test, governance tests and fast CI;
- verify `next_available` after excluding service refs;
- run converge and keep reserved IDs unchanged.

## Project Structure

```text
scripts/claim-feature.py
tests/governance/test_validator_safety.py
specs/225-feature-id-allocator/{spec,clarifications,research,plan,tasks,quickstart}.md
specs/225-feature-id-allocator/checklists/requirements.md
changes/unreleased/F225.yaml
```

## Complexity Tracking

No new dependency, service, storage schema, branch policy or product behavior.
