# Implementation Plan: Надёжный RLS release gate

**Branch**: `codex/fix-rls-ci-runtime` | **Date**: 2026-08-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/167-rls-ci-runtime/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Полный локальный gate должен запускать RLS hardening validation через
project-managed Python runtime. Используем существующий `uv`-runtime и
`PYTHONPATH=src` из server-проекта, добавляем контрактную проверку команды и
сохраняем текущий fail-closed boundary, порядок стадий и cleanup disposable
ресурсов.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: POSIX shell; Python 3.13 project runtime via `uv`

**Primary Dependencies**: Existing `apps/server` lockfile and `uv` environment; no new dependency

**Storage**: Disposable loopback PostgreSQL used only by the RLS probe; no schema change

**Testing**: Existing pytest contract tests, direct RLS probe, deployment evidence scan, exact-SHA full local gate

**Risk / Validation Lane**: `release-deploy` / high-risk release-readiness; the change controls whether database security validation runs before production deployment

**Release Gate**: `cd dry-run` before production approval; `cd execute` remains the separate production gate and reruns full CI

**Target Platform**: macOS development host running the local release scripts and Linux production validation environment

**Project Type**: Release validation scripts for a web service and macOS product

**Performance Goals**: Add no extra test suite or database probe; invoke the existing RLS check once per full gate

**Constraints**: No production database target; no secret output; no weakened evidence/RLS guards; no new dependency; preserve stage order

**Scale/Scope**: One shared local gate command, one RLS validation entrypoint, one contract test surface, and release documentation

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

*GATE: PASS before Phase 0.*

- Capture-First MVP Integrity: PASS — no capture, audio, permission, or recording behavior changes.
- Visible Consent And User Control: PASS — no user-facing capture controls change.
- Plaintext Observability For Internal MVP: PASS — the fix preserves metadata-only release evidence and does not add credentials or content egress.
- Deletion Truth And Lifecycle Accounting: PASS — no product data or lifecycle behavior changes.
- Public macOS Distribution And Update Integrity: PASS — no signing or artifact path changes; the release gate remains a prerequisite.
- Spec-Driven Delivery With Testable Gates: PASS — this slice uses the required spec, clarify decision, plan, checklist, tasks, analyze, and implementation evidence.

## Validation Plan

1. Run the focused RLS boundary contract selection and `git diff --check`.
2. Run the RLS script with no URL and confirm a blocked, no-probe result.
3. Run the RLS script against a named loopback disposable database and confirm direct probe pass plus cleanup.
4. Run `infra/scripts/scan-deployment-evidence.sh docs/deployments/2brain-rec`.
5. Run `infra/scripts/ci-local.sh --full` once on the exact release-candidate SHA with the disposable URL; this is required because the shared release gate changed.
6. Run `infra/scripts/cd-remote.sh --dry-run --branch master`; production `--execute` is deferred until the explicit release gate is met and will repeat full CI.

## Project Structure

### Documentation (this feature)

```text
specs/167-rls-ci-runtime/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Not needed: internal release script, no public contract
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
infra/scripts/ci-local.sh
apps/server/scripts/verify_rls_hardening.py
apps/server/tests/contract/test_rls_production_boundary.py
docs/agent-guidance/release-and-validation.md
CHANGELOG.md
```

**Structure Decision**: Reuse the existing shell gate and server contract test;
the only runtime change is the command that invokes the existing RLS script.
No new package, service, schema, or abstraction is introduced.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | No constitution violation. |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
