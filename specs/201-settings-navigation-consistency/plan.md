# Implementation Plan: Единая информационная архитектура меню GRAF

**Branch**: `201-settings-navigation-consistency` | **Date**: 2026-08-25 | **Spec**: [spec.md](spec.md)

## Summary

Расширить существующий shared profile menu до Krisp-like IA: account, appearance,
settings, disabled help/resources/support actions, logout and quit. Reuse the
existing theme picker, profile shell and logout form. Add one allowlisted native
WebView quit message for embedded desktop; browser stays disabled.

## Technical Context

**Language/Version**: Python 3.12, Jinja2, vanilla JavaScript, CSS, Swift/WebKit

**Primary Dependencies**: existing cabinet templates/static assets and WebKit bridge

**Storage**: existing account preferences only; no migration

**Testing**: focused pytest unit/contract tests, integration settings flow, Swift bridge contract tests, CI fast

**Risk / Validation Lane**: `high-risk-feature` — user-facing navigation, theme and app lifecycle UX

**Release Gate**: Пользователь запросил выпуск и полную выкладку после focused validation; полный CI явно исключён из этого closeout с зафиксированным риском.

## Constitution Check

- Capture/privacy/auth/data boundaries: **PASS** — no capture, provider, session or secret-flow changes.
- Accessibility/truthfulness: **PASS** — disabled actions are semantic; browser does not pretend to close a tab.
- Clean-room UX: **PASS** — only IA and behavior are used as reference, with existing GRAF tokens/assets.
- Spec-driven delivery: **PASS** — active slice updated with requirements, UX checklist, tasks, analysis and focused validation.

## Validation Plan

1. Render browser and embedded meeting shells and assert exact menu order, submenu counts, disabled states and surface-aware routes.
2. Run focused profile/settings tests and the disposable-Postgres settings-flow integration tests.
3. Run native bridge contract tests if Swift toolchain is available.
4. Run `infra/scripts/ci-local.sh --fast` because the shared user-facing shell and native bridge changed.
5. Для явно запрошенного релиза использовать точный post-merge SHA и одобренный путь `--skip-local-ci`; production evidence остаётся отдельным от focused validation.

## Structure Decision

Reuse `sections.html`, existing cabinet CSS/JS and `EmbeddedCabinetWebView.swift`.
No new frontend dependency, component system, endpoint or data model.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| One native message handler | A WebView cannot safely terminate the macOS app through server HTML alone. | `window.close()` is unreliable and would falsely promise browser behavior. |
