# Implementation Plan: Безопасная инвентаризация и retirement legacy

**Branch**: `codex/220-legacy-retirement` | **Date**: 2026-08-31 | **Spec**: [spec.md](spec.md)

## Summary

Сначала создаём детерминированный metadata-only inventory legacy-контуров на exact SHA, затем классифицируем их и создаём маленькие task-backed retirement slices. Governance scanner запрещает новый legacy, а protected domains получают отдельные migration/Temporal/Sparkle gates.

## Technical Context

**Language/Version**: Python project tooling and POSIX shell; first slice is documentation, metadata and validators.

**Primary Dependencies**: Existing stdlib validators, Spec Kit, Git/GitHub CLI and existing migration/Temporal/Sparkle inspection scripts.

**Storage**: Git-tracked contracts plus metadata-only evidence; no production or user-data writes.

**Testing**: Validator self-tests, governance pytest suite, shell syntax checks, Feature 220 quickstart and `infra/scripts/ci-local.sh --fast`.

**Risk / Validation Lane**: `significant-feature`; governance and compatibility are shared/high-risk surfaces.

**Release Gate**: No deploy in Feature 220; runtime retirement requires a later approved release gate.

**Target Platform**: macOS development workstation and Linux/CI repository tooling.

**Project Type**: Governance tooling and maintenance program for a backend/frontend/desktop product.

**Performance Goals**: Inventory completes within 60 seconds and is deterministic on repeated runs.

**Constraints**: Metadata-only output, no secrets/raw content, exact-SHA provenance, fail-closed incomplete evidence, no production mutation.

**Scale/Scope**: All known GRAF legacy categories, split into independently reviewable contours and slices.

## Constitution Check

- Pass: no capture, auth, deletion or production behavior changes in the inventory slice.
- Pass: production data and migration pointers remain protected; Feature 221 owns existing Dev drift.
- Pass: no new aliases, fallbacks, flags or dependencies are introduced.
- Pass: retained compatibility is time-bounded and task-backed.
- Pass: evidence excludes secrets, raw audio, transcript text and private meeting content.
- Pass: root `AGENTS.md` and root `CHANGELOG.md` remain stable; feature owns its spec and fragment.

## Validation Plan

1. Run Feature 220 quickstart and metadata-only inventory fixtures.
2. Run validator self-tests and changed-path Legacy Impact checks.
3. Run `pytest -q tests/governance` and `infra/scripts/ci-local.sh --fast` on the PR-ready exact SHA.
4. Do not run production CD or repair the existing Dev volume in this feature.
5. Require domain-specific backup/restore, replay, signing and rollback evidence in later retirement slices.

## Project Structure

```text
specs/220-legacy-retirement/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── inventory.md
│   └── retirement-slice.md
├── checklists/requirements.md
└── tasks.md

changes/unreleased/F220.yaml
scripts/validate-legacy-impact.py
scripts/check-development-process.py
tests/governance/
```

**Structure Decision**: This is a governance/maintenance slice. Inventory contracts and fixtures live with the feature; generic validators are extended only when a failing test demonstrates a missing guard.

## Complexity Tracking

No constitution violations. Runtime deletion, data migration and production release are separate features.
