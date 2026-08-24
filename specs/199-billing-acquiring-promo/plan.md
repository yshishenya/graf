# Implementation Plan: Доразвитие биллинга, эквайринга и промокодов

**Branch**: `codex/199-billing-acquiring-promo` | **Date**: 2026-08-23 | **Spec**: [spec.md](spec.md)

## Summary

Довести уже реализованный Feature 140 до понятного checkout preview и
операционно выпускаемых промокодов. Используются существующие Jinja/FastAPI
routes, `checkout_preview`, `PromotionCampaign`/`PromotionRedemption`, CSRF,
rate-limit, maintenance RLS и YooKassa launch gates. Новых provider SDK,
публичного admin API, migration и оплаты из preview не добавляется.

## Technical Context

**Language/Version**: Python 3.13; Jinja/HTML; минимальный JavaScript не нужен.

**Primary Dependencies**: FastAPI, SQLAlchemy, existing `httpx` YooKassa client,
pytest and Ruff.

**Storage**: Existing PostgreSQL billing catalog and promotion tables; preview is
ephemeral.

**Testing**: `uv run pytest` with `PYTHONPATH=src`, focused contract/unit tests,
then `infra/scripts/ci-local.sh --fast`.

**Risk / Validation Lane**: high-risk active Spec Kit slice. Money, provider,
secrets and RLS require existing Feature 140 gates and repository fast lane.

**Release Gate**: no production deploy in this slice; `cd-remote.sh --dry-run`
only after validation. `--execute` requires separate explicit approval and all
Feature 140 launch evidence.

**Target Platform**: Linux Docker server and browser-owned cabinet.

**Project Type**: FastAPI web service plus operations CLI.

**Performance Goals**: Preview adds one bounded catalog/campaign read and no
external provider call; normal checkout idempotency and provider timeouts remain
unchanged.

**Constraints**: No raw promo code in URL, analytics, logs, JSON output or
database; no reservation during preview; checkout and renewal remain fail-closed.

**Scale/Scope**: One campaign lookup per preview and one operator campaign
operation at a time; existing campaign counters remain the concurrency authority.

## Constitution Check

- PASS: money mutation stays server-owned and provider hosted.
- PASS: no secret/raw code is committed, logged or exposed to desktop.
- PASS: no refund API or user-facing refund workflow is added.
- PASS: RLS/CSRF/rate-limit and existing launch gates remain mandatory.
- PASS: change follows high-risk Spec Kit lane and keeps production default-off.

## Validation Plan

1. Run Feature 140 artifact consistency check with `SPECIFY_FEATURE_DIRECTORY`
   explicitly set; record open external gates without marking them complete.
2. Run Feature 199 quickstart and focused promo/UI/CLI tests.
3. Run `git diff --check` and `infra/scripts/ci-local.sh --fast` before closeout.
4. Run `infra/scripts/cd-remote.sh --dry-run --branch
   codex/199-billing-acquiring-promo` only after a clean validated tree; do not
   execute production deployment or provider mutation in this turn.

## Project Structure

```text
specs/199-billing-acquiring-promo/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── http-interface.md
│   └── operations.md
├── checklists/
│   ├── operations.md
│   ├── requirements.md
│   └── security.md
└── tasks.md

apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py
apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_checkout_content.html
apps/server/scripts/manage_promo_campaign.py
apps/server/tests/contract/test_billing_ui.py
apps/server/tests/unit/test_promo_campaign_cli.py
```

**Structure Decision**: Reuse the existing server-rendered billing surface and
maintenance scripts; do not add a second service, SPA or admin product.

## Complexity Tracking

No constitution violation or new abstraction is required.
