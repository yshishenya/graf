# Implementation Plan: API Healthcheck Budget

**Branch**: `codex/209-api-healthcheck-budget` | **Date**: 2026-08-28 | **Spec**: [spec.md](spec.md)

## Summary

Согласовать внутренний readiness request budget и общий Docker healthcheck
budget с измеренной production latency. Сохранить `/ready`, bounded failure и
rollback semantics. Изменить одну compose healthcheck и один существующий
контрактный тест.

## Technical Context

**Language/Version**: Docker Compose YAML; Python 3.13 one-line health probe; Python 3.14 test runtime

**Primary Dependencies**: Python stdlib `urllib.request`, Docker Compose, existing pytest contract

**Storage**: N/A; схема и данные не меняются

**Testing**: focused pytest compose contract, rendered compose config, full exact-SHA CI, guarded deploy

**Risk / Validation Lane**: High-risk infrastructure / release-deploy blocker. Полный Spec Kit slice, focused contract, fast PR gate и повторный full exact-SHA production gate обязательны.

**Release Gate**: `cd-remote.sh --dry-run` и затем approved `--execute` только из clean synchronized master; rollback остаётся обязательным

**Target Platform**: Linux production Docker Compose on `2brain.dev`

**Project Type**: Self-hosted web service and deployment pipeline

**Performance Goals**: Принимать measured readiness 3.5–3.6 s; bounded failure at 8 s request / 10 s runner

**Constraints**: Readiness path unchanged; internal budget less than runner budget; no billing/config/data mutation; no manual server edit

**Scale/Scope**: One healthcheck stanza, one existing test, Feature 209 docs

## Constitution Check

*GATE: PASS before and after design.*

- **Production safety**: PASS — rollback remains fail-closed and the change is repository-driven.
- **Exact-SHA truth**: PASS — failed candidate and next candidate are recorded separately; full CI is rerun after the new merge.
- **No secret/config drift**: PASS — runtime environment and secret files are untouched.
- **Billing boundary**: PASS — test-shop values are only read back after deploy; no provider mutation.
- **Minimal root-cause fix**: PASS — one calibrated timeout pair at the healthcheck boundary, no endpoint or readiness rewrite.
- **Validation evidence**: PASS — contract test plus real production timing and guarded rollout.

## Design

1. Keep the existing `/api/v1/health/ready` probe and HTTP error behavior.
2. Set the stdlib request timeout to 8 seconds.
3. Set the Docker healthcheck runner timeout to 10 seconds, preserving a two-second termination margin.
4. Keep interval and retry count unchanged.
5. Extend the existing compose hardening test to pin route and both budgets.

## Validation Plan

1. RED/GREEN: `cd apps/server && uv run --extra dev pytest tests/integration/test_compose_hardening.py -q`.
2. Rendered config: `docker compose --env-file infra/env/rec.production.env.example -f infra/docker-compose.yml config`.
3. Before PR: `infra/scripts/ci-local.sh --fast`.
4. After merge: synchronize exact master SHA, run `infra/scripts/ci-local.sh --full`, then `cd-remote.sh --dry-run --branch master` and approved `--execute`.
5. Verify public live/ready, container health history and bounded YooKassa environment fields only.
6. Continue macOS notarization/Sparkle only after server deploy PASS.

## Project Structure

```text
specs/209-api-healthcheck-budget/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── api-healthcheck.md
├── checklists/
│   ├── requirements.md
│   └── infra.md
└── tasks.md

infra/docker-compose.yml
apps/server/tests/integration/test_compose_hardening.py
CHANGELOG.md
```

## Complexity Tracking

Constitution violations: none.
