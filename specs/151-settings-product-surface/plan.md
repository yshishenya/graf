# Implementation Plan: Продуктовый раздел настроек

**Branch**: `151-settings-product-surface` | **Date**: 2026-08-16 | **Spec**: [spec.md](spec.md)

## Summary

Довести существующий server-rendered кабинет GRAF до визуального и IA-паритета с Open Design: единый overview, scope-first карточки, grouped navigation, активное состояние и responsive settings-only CSS. Все реальные формы и серверные границы переиспользуются.

## Technical Context

**Language/Version**: Python 3.11, Jinja, HTMX, vanilla JavaScript/CSS, Swift WebKit embedding

**Primary Dependencies**: Existing FastAPI cabinet rendering, existing Jinja templates, existing cabinet.css; no new dependency

**Storage**: Existing account preferences, workspace, calendar, notification and billing projections; no migration

**Testing**: Focused Python template/view-model tests, existing account/settings contract suites, browser matrix at 1280×720 and 390×844, `infra/scripts/ci-local.sh --fast`

**Risk / Validation Lane**: high-risk-feature — account/security and user-visible settings UX

**Release Gate**: No production execution; normal release gates remain unchanged. Implementation commit requires explicit user approval after validation.

## Constitution Check

- PASS: capture remains macOS system-audio-first and manual capture controls are unchanged.
- PASS: auth, CSRF, tenant, owner, re-auth and payment gates remain server-owned.
- PASS: no raw audio, transcript text, credentials or private meeting content enters evidence.
- PASS: settings copy remains truthful about GRAF-controlled deletion, billing and capture boundaries.
- PASS: no new dependency, schema migration or parallel local settings store.

## Implementation Approach

1. Reuse `settings_category_navigation()` as the single category source.
2. Keep the existing `settings_content.html` overview and section templates; adjust only copy/layout primitives needed for prototype parity.
3. Reuse `settings_navigation.html` for the active `aria-current` contract and grouped rail.
4. Tune settings-scoped CSS tokens: 6–8px working radii, thin separators, transparent overview cards, rectangular scope badges, open list rows, and the existing purple accent only for focus/primary action.
5. Keep form submission and all result/unavailable states server-backed; use existing `cabinet.js` only for progressive enhancement.
6. Validate desktop and mobile screenshots plus focused route/template contracts before the repository fast gate.

## Files

- `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_content.html`
- `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/settings_navigation.html`
- `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`
- `apps/server/src/twobrain_rec_server/cabinet/view_models.py` only if existing category copy/route metadata needs correction
- `apps/server/tests/` or existing focused settings/template test locations
- `CHANGELOG.md`

## Validation Plan

- Render settings overview and every category route using existing test harness.
- Assert seven categories, exact scope labels, one active `aria-current`, and truthful recording/billing boundary copy.
- Run browser matrix at `1280×720` and `390×844`; assert zero horizontal overflow and visible focus.
- Run focused account/settings/calendar/billing suites and `infra/scripts/ci-local.sh --fast`.
