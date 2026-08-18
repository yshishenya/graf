# Implementation Plan: Непрерывная навигация кабинета

**Branch**: `codex/159-cabinet-navigation-continuity` | **Date**: 2026-08-17 | **Spec**: [spec.md](spec.md)

## Summary

Закрепить один понятный shared cabinet shell для браузера и embedded WebView:
стабильный sidebar toggle, отдельное пространство поиска, web-only download CTA,
безопасное профильное меню и settings mode, который заменяет содержимое той же
primary rail. Auth UI только приводится в соответствие с проверенным контрактом;
backend auth semantics и settings category/form ownership остаются без изменений.

## Technical Context

**Language/Version**: Python >=3.13, Jinja2, vanilla JavaScript/CSS

**Primary Dependencies**: Existing FastAPI cabinet rendering, Jinja templates,
local HTMX 2.x, existing `cabinet.js` and `cabinet.css`; no new dependency

**Storage**: Existing account/workspace/settings projections; no migration,
localStorage or new persistent state

**Testing**: Focused pytest unit/contract/integration suites, `node --check`,
synthetic browser/embedded render matrix, `infra/scripts/ci-local.sh --fast`

**Risk / Validation Lane**: `high-risk-feature` — shared user-facing UX,
accessibility, profile data projection and auth-adjacent surfaces; no capture or
backend auth semantics change

**Release Gate**: `no deploy` — no production or public release is requested;
implementation commit requires explicit user approval after validation

**Target Platform**: Modern browsers and macOS embedded WebView cabinet surface

**Project Type**: Server-rendered web cabinet with embedded desktop surface

**Performance Goals**: No additional network request or client state store for
shell controls; initialization remains bounded and idempotent after partial updates

**Constraints**: Preserve existing URLs, auth/CSRF/tenant/role/billing gates,
native recording boundary, Russian localization, clean-room design, narrow
viewport reachability and safe profile fields

**Scale/Scope**: One shared shell, seven existing settings categories, browser/
embedded parity, synthetic-only validation; no new data model

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Capture-First MVP Integrity: PASS — no native capture route, permissions,
  recording controls or audio path change; settings recording remains a native
  handoff.
- Visible Consent and User Control: PASS — no recording indicator, Record/Stop,
  policy or automatic-recording control is removed or hidden.
- Privacy and secret discipline: PASS — profile menu consumes only existing safe
  display projection; evidence excludes credentials, tokens, audio and meeting
  content.
- Auth and tenant boundaries: PASS — unknown-email, signup, invitation/provider,
  CSRF, session, exact-email, rate-limit, role, billing and tenant semantics are
  preserved and regression-tested.
- UI/accessibility/clean-room: PASS — one semantic rail, keyboard/focus state,
  Russian copy, narrow/reduced-motion coverage and original GRAF composition are
  required.
- Spec-driven delivery: PASS — spec, clarify audit, research, contract,
  checklists, tasks, analyze and focused/fast validation are required.

## Validation Plan

1. Run focused source/contract tests for shared shell, settings IA, auth routes
   and static assets.
2. Run `node --check apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`.
3. Run the synthetic browser/embedded matrix at desktop and narrow sizes for
   light/dark, keyboard, reduced-motion, missing/long profile data and repeated
   partial initialization.
4. Run the existing disposable Postgres runner for `test_settings_ia_flow.py`
   and any auth/session integration coverage that requires it.
5. Run `infra/scripts/ci-local.sh --fast` once at slice closeout and record exact
   SHA/result in quickstart and evidence.
6. Do not deploy, publish, notarize or change native macOS shell in this slice.

## Project Structure

### Documentation (this feature)

```text
specs/159-cabinet-navigation-continuity/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── cabinet-navigation-continuity.md
├── checklists/
│   ├── requirements.md
│   ├── ux.md
│   └── security.md
└── tasks.md
```

### Source Code

```text
apps/server/src/twobrain_rec_server/cabinet/
├── rendering_shared.py
├── rendering.py
├── view_models.py
├── static/cabinet/cabinet.css
├── static/cabinet/cabinet.js
└── templates/cabinet/
    ├── auth/login.html
    ├── components/sections.html
    ├── components/settings_navigation.html
    └── pages/settings_*.html

apps/server/tests/
├── unit/test_cabinet_web_shell.py
├── contract/test_cabinet_static_assets_contract.py
├── contract/test_account_routes.py
├── integration/test_settings_ia_flow.py
└── integration/test_web_owner_session_context.py
```

**Structure Decision**: Reuse the existing server-rendered shell and view-model
contracts. Keep route handlers and auth services authoritative; place markup in
Jinja, visual rules in the existing CSS, bounded DOM behavior in the existing JS,
and regression assertions beside current tests.

## Complexity Tracking

No constitution violations. Ponytail ceiling: one shared shell initializer and
server-owned route truth; add a separate client state layer only if a future
interaction cannot remain idempotent with the existing DOM contract.
