# Implementation Plan: Быстрый и доказуемый CI/CD

**Branch**: `211-optimize-ci-cd` | **Date**: 2026-08-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/211-optimize-ci-cd/spec.md`

## Summary

Убрать две причины лишнего времени: неявный `full` при запуске общего CI и ручной full перед тем же deploy. Общий runner требует явный lane, `fast` выбирает затронутые компоненты консервативно, а `cd-remote.sh --execute` после синхронизации exact SHA выполняет один authoritative full. Все остальные production gates остаются без изменений.

## Technical Context

**Language/Version**: Bash 3.2-compatible shell; existing Swift and Python application toolchains unchanged

**Primary Dependencies**: Git, `shasum`, existing `uv`, pytest, SwiftPM, Docker Compose; no new dependency

**Storage**: No new storage

**Testing**: pytest contract tests invoking the CLIs in disposable repositories; focused shell syntax checks; feature quickstart; explicit `--fast`; final `--full`

**Risk / Validation Lane**: high-risk feature — infrastructure, validation governance and production preflight behavior change

**Release Gate**: user approved commit, push, PR, merge, tag, release and production execute

**Target Platform**: trusted macOS release workstation plus Linux-compatible shell paths used by server test/deploy helpers

**Project Type**: monorepo with macOS desktop app, Python server, local CI and SSH-driven production CD

**Performance Goals**: small server-only changes avoid Swift validation; macOS-only changes avoid PostgreSQL/server validation; component-only fast p50 is at most 25% of the `1406.36s` full baseline; the normal execute flow runs full CI once before remote production actions

**Constraints**: fail closed for unknown/shared/high-risk paths; preserve security/privacy/RLS/backup/smoke/rollback/notarization gates; Bash 3.2 compatibility

**Scale/Scope**: one local CI entrypoint, one deploy entrypoint, one server test runner, active operator guidance and contract tests; immutable image registry delivery excluded

## Constitution Check

*GATE: Passed before Phase 0 and re-checked after Phase 1.*

- **Spec-first / high-risk governance**: PASS — specification, clarification scan, plan, contracts, quickstart, checklist, tasks and analyze precede implementation.
- **Privacy and secret custody**: PASS — no new persisted evidence or sensitive data path.
- **Security and trust boundaries**: PASS — authoritative full runs only after exact-SHA sync and cannot bypass the remaining production gates.
- **Testability and evidence**: PASS — CLI/deploy ordering and failure paths have runnable contracts; final full repository gate remains required.
- **Minimality / dependency policy**: PASS — receipt helper and local attestation complexity are deleted; no dependency is added.
- **Release integrity**: PASS — exact-SHA, backup, restore, RLS, secret, health, smoke and rollback rules remain untouched.

Post-design re-check: PASS. The design uses the existing deploy entrypoint for the single authoritative full and preserves the remote runtime path.

## Validation Plan

1. Static/focused: `bash -n` for changed shell scripts; Ruff/Python compile; CLI contract and documentation consistency tests.
2. Contract scenarios: missing mode, component mapping, unknown/shared escalation, dirty-tree rejection, post-full candidate drift and deploy ordering.
3. Feature quickstart: exercise real CLI help/error and deploy dry-run without production access.
4. Repository fast lane: run explicit `infra/scripts/ci-local.sh --fast`; this infrastructure diff must conservatively expand to full.
5. Repository full lane: run once on the frozen PR candidate after review.
6. CD: after merge, run dry-run and approved execute from synchronized `master`; execute owns the authoritative full.
7. Consistency: compare active guidance, PR template, `--help`, contract and actual output; scan active docs for bare ambiguous CI invocation.

## Project Structure

### Documentation (this feature)

```text
specs/211-optimize-ci-cd/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── ci-cd-cli.md
├── checklists/
│   ├── requirements.md
│   └── operational-readiness.md
└── tasks.md
```

### Source Code (repository root)

```text
infra/scripts/
├── ci-local.sh
├── cd-remote.sh
└── README.md

apps/server/
├── scripts/run_local_postgres_tests.sh
└── tests/contract/test_ci_cd_contract.py

docs/agent-guidance/release-and-validation.md
docs/current-product-status.md
.github/pull_request_template.md
AGENTS.md
CHANGELOG.md
```

**Structure Decision**: Keep orchestration in the two existing operator entrypoints and behavioral contracts in the existing server contract tests. Add no helper, service or dependency.

## Complexity Tracking

No constitution violations or new architectural layers require justification.
