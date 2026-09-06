# Implementation Plan: F242

**Branch**: `codex/242-cabinet-audit-fixes` | **Date**: 2026-09-06 | **Spec**: [spec.md](spec.md)

## Summary

Пять исправлений: частичное обновление preferences; профиль во всех authenticated billing/deletion shell; общий native trial disclosure; рабочий раздел помощи; читаемый formatter и краткий pending placeholder.

## Technical Context

- Python 3.12, FastAPI, SQLAlchemy, Jinja2; существующие pytest и node contract harness.
- Storage: PostgreSQL, существующие UserIdentity/WorkspaceSubscription/TrialActivation, без миграций.
- Risk / validation lane: **high-risk-product**, account preferences, billing UX, deletion shell.
- Release gate: **no deploy**; результат — PR, не merge/release.
- Platform: browser и embedded cabinet. Новые зависимости/endpoint/service не нужны.
- Performance: profile lookup один раз на full page, не в polling fragments; нет новых фоновых вызовов.

## Constitution Check

До исследования и после проектирования: PASS. Clarify актуален; сохраняются auth/tenant/CSRF, trial/денежные правила, deletion boundaries, capture/AI/provider credentials. Independent requirements checklist review до реализации; task ownership в GitHub. Только synthetic evidence, без screenshots в git. Legacy classification: untouched, legacy_new=0, unowned_legacy=0, expired_exceptions=0.

## Approach and structure

Исходники под `apps/server/src/twobrain_rec_server/`:
- `cabinet/web_routes/settings.py`: atomic validation supplied preferences, existing row lock, preserve omitted fields.
- `cabinet/templates/cabinet/components/sections.html`: theme-only menu form и общий trial confirmation macro.
- `cabinet/web_routes/billing.py`: existing get_account_profile_view во всех full shell; TRIAL_DAYS для предварительных/фактических labels; decimal formatter.
- `cabinet/web_routes/{fair_use,referrals}.py`: тот же profile helper для соседних full shell. Общий theme control скрыт без достоверного profile; narrow sharing не получает дополнительные приватные данные.
- `cabinet/deletion_rendering.py`, `cabinet/web_routes/deletion.py`, `cabinet/web_routes/desktop.py`: profile argument и authenticated full-page callers.
- `cabinet/templates/cabinet/pages/billing_{overview,plans,history}_content.html`: confirmation/help; `meeting_detail_content.html`: pending copy.
- `apps/server/tests/{unit,contract}/`: regressions рядом с существующими проверками.
- `changes/unreleased/F242.yaml`: owned changelog; feature-only spec/evidence.

## Validation Plan

Сначала failing regressions, затем scoped unit/contract и изолированные handler checks. Не использовать fixture client с общим dev DB. Browser QA changed synthetic renders wide/390px, keyboard/no-JS trial, theme fields/pending hooks. Полный CI только для frozen release; authoritative PR gate — GitHub governance-fast exact SHA. Локальный fast — diagnostic/fallback. Независимая проверка корректности и Ponytail review до converge/PR.

## Complexity Tracking

Исключений нет. Native details вместо modal controller; существующий endpoint/профиль вместо новых моделей.
