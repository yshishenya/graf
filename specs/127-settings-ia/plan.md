# Implementation Plan: единая архитектура настроек

**Branch**: `127-settings-ia` | **Date**: 2026-07-25 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/127-settings-ia/spec.md`

## Summary

Исправить главный вход в настройки, собрать существующие web surfaces в
list-detail IA и дать каждой поддерживаемой категории канонический путь. Общий
shell должен одинаково работать в браузере и embedded desktop webview,
показывать scope/role до изменения и сохранять существующие server-side
контракты календарей, summary templates, spaces, provider links и auth devices.

Срез сознательно не добавляет новую settings schema. Календарь остаётся
самостоятельной integration page, account получает безопасную проекцию уже
существующих auth данных, а запись — только web-to-native handoff.

## Technical Context

**Language/Version**: Python 3.11+ server code, Jinja templates, vanilla
JavaScript/CSS; the corrective embedded-parity slice also updates the Swift
macOS route policy and its focused tests.

**Primary Dependencies**: FastAPI, Starlette, Jinja2, SQLAlchemy async,
existing cabinet rendering/helpers, HTMX where already used; no new package.

**Storage**: Existing PostgreSQL models and RLS/tenant context. No migration,
new table or new client-side settings store.

**Testing**: `pytest` contract/unit/integration suites under `apps/server/tests`;
existing static HTML and no-secret contract tests; repository gate
`infra/scripts/ci-local.sh`.

**Risk / Validation Lane**: **high-risk-feature / significant-feature**.
Причина — user-facing settings IA пересекается с auth, devices, privacy,
calendar credentials, accessibility and native recording handoff. Required:
full Spec Kit flow, UX/security requirements checklists, focused quickstart and
repository CI gate. Capture behavior itself remains out of scope.

**Release Gate**: The original server-only slice had no deploy gate. The
post-release embedded-parity correction uses the repository release guidance;
versioning, macOS feed publication and production rollout require explicit user
approval and the mandatory local CI/CD evidence.

**Target Platform**: Authenticated browser cabinet and macOS embedded desktop
webview; native macOS recording settings remain authoritative but are not
modified.

**Project Type**: Server-rendered web application with a desktop webview shell.

**Performance Goals**: Settings overview and category pages must keep the
existing no-store behavior and avoid unbounded per-item queries. Existing
calendar rendering and summary API behavior must not regress; the new account
projection uses bounded current-user/current-workspace reads.

**Constraints**:

- Global settings navigation MUST target `/settings` or `/desktop/settings`.
- Existing deep links and action endpoints remain compatible.
- Use fixed allowlisted return paths; never accept an arbitrary open redirect.
- Preserve session auth, CSRF, tenant context, RLS and audit behavior.
- Never render provider subjects, candidate contact data, credentials, tokens,
  raw audio or transcript/meeting content.
- Do not add a global web recording toggle or revive removed audio routing.
- Keep Russian product copy and clean-room GRAF visual language.

**Scale/Scope**: Six supported settings destinations, about eleven existing
calendar provider entries, current-user devices/providers, and both browser and
embedded variants. No new persisted entity.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / gate | Status | Evidence and plan |
|---|---|---|
| Capture-first native MVP | PASS | No capture pipeline, routing, upload or native policy changes. Recording page is a truthful handoff only. |
| Visible consent and user control | PASS | No hidden recording control; manual start/stop, visible indicator and one-action Stop remain unchanged. |
| Plaintext observability and secret custody | PASS | No transcript/model change; account/calendar pages exclude subjects, credentials and tokens; calendar secrets remain server-side. |
| Deletion truth | PASS | No new deletion promise or lifecycle state; calendar disconnect copy remains bounded by GRAF control. |
| Spec-driven delivery | PASS | Full specify → clarify → plan → checklist → tasks → analyze → issue sync → implement; focused tests and CI required. |
| Accessibility and brand distance | PASS | Semantic headings, scope copy, keyboard/focus/error requirements and existing clean-room shell are explicit in the UI contract. |

No constitution amendment is needed: `.specify/memory/constitution.md` has no
placeholders and the feature does not change project governance.

## Validation Plan

1. Focused unit/contract tests for navigation, settings render surfaces,
   account-safe projection, route aliases, CSRF and no-secret output.
2. Existing calendar/provider/summary/workspace integration tests plus new
   settings route scenarios from `quickstart.md`.
3. Manual browser and embedded smoke for discoverability, role/scope, empty and
   unavailable states, dirty/save/error behavior and keyboard dialog focus.
4. macOS route-policy tests and an installed-client smoke proving the embedded
   settings link loads instead of entering the blocked-route state; the native
   recording settings handoff remains separate.
5. `git diff --check` and `infra/scripts/ci-local.sh` before closeout.
6. No hardware capture run and no raw meeting-content evidence; release/deploy
   evidence is required only for the explicitly approved corrective rollout.

## Technical Approach

### 1. Centralize settings routing and common shell

Create `apps/server/src/twobrain_rec_server/cabinet/web_routes/settings.py` as
the single owner of browser/desktop settings pages and remove the duplicated
root handlers from `browser.py` and `desktop.py`. Register explicit routes for
overview, recording, summaries, workspace and account; keep calendar and
provider-link routers as their existing domain routes.

Update `cabinet_navigation` to target the overview, and add one shared
settings-navigation macro/template used by all category pages. Pass `embedded`
to a fixed route map so desktop parity does not depend on string concatenation
in individual templates.

### 2. Split current flat content without changing domain APIs

Replace the root card list with an overview and move existing controls into
category templates. Reuse:

- `BUILT_IN_TEMPLATES` and `/api/v1/cabinet/summary-templates` for summaries;
- `list_active_workspaces` and `list_workspace_join_offers` for workspace/team;
- provider-link start/confirm routes for account;
- `get_calendar_settings_surface` and all existing calendar actions for
  integrations;
- existing auth device revoke authorization for account;
- a static recording handoff for native macOS settings.

Add `AccountSettingsSurface` in `cabinet/view_models.py` and a bounded query
projection in `cabinet/queries.py`. It must use explicit user/workspace filters
and safe labels; it must not expose raw auth identities.

### 3. Preserve security and mutation semantics

Add fixed embedded/browser aliases for workspace return actions where needed,
keep `WebCSRFDependency` on every mutation, and pass only allowlisted category
return targets. Reuse the existing `revoke_device` authorization/audit path
from the web adapter rather than copying its membership checks.

Keep summary default constraints visible in copy: owner-only and built-in-only.
Keep calendar credential handling server-side, preserve truthful disconnect
copy, and do not turn read-only conflict preview into a fake action.

### 4. Apply focused accessibility and interaction fixes

- Convert settings titlelines/section labels to semantic `h1`/`h2`.
- Add scope/role/status and intentional empty/unavailable states.
- Restore opener focus after calendar provider dialogs and support native
  cancel/close behavior.
- Mark grouped settings forms for dirty/save/error state; preserve values after
  safe failures and do not echo secrets.
- Keep buttons for actions and links for navigation; make conflict choices
  clearly informational until a supported mutation exists.

### 5. Documentation and release readiness

Update `CHANGELOG.md` in Russian under `[Unreleased]`, keep the feature artifacts
in sync, and record focused/CI evidence without private meeting content.

## Project Structure

### Documentation (this feature)

```text
specs/127-settings-ia/
├── spec.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/settings-ui.md
└── checklists/
    ├── requirements.md
    ├── ux.md
    └── security.md
```

### Source Code (repository root)

```text
apps/server/src/twobrain_rec_server/
├── cabinet/
│   ├── queries.py
│   ├── rendering.py
│   ├── rendering_shared.py
│   ├── view_models.py
│   ├── static/cabinet/cabinet.css
│   ├── static/cabinet/cabinet.js
│   ├── templates/cabinet/components/settings_navigation.html
│   ├── templates/cabinet/pages/settings_content.html
│   ├── templates/cabinet/pages/settings_account_content.html
│   ├── templates/cabinet/pages/settings_recording_content.html
│   ├── templates/cabinet/pages/settings_summaries_content.html
│   ├── templates/cabinet/pages/settings_workspace_content.html
│   └── web_routes/
│       ├── settings.py
│       ├── browser.py
│       ├── desktop.py
│       ├── spaces.py
│       └── provider_links.py
└── api/auth.py                         # existing revoke contract reused

apps/server/tests/
├── contract/test_settings_ui_contract.py
├── contract/test_provider_link_settings_contract.py
├── unit/test_cabinet_navigation_model.py
└── unit/test_cabinet_view_models.py
```

**Structure Decision**: Keep the existing cabinet module and server-rendered
templates. A dedicated `web_routes/settings.py` is the smallest shared owner
for browser/desktop parity; no new frontend project or component framework is
introduced.

## Phase 0 Research Output

See [research.md](research.md). All technical unknowns that affect scope are
resolved: existing APIs/models are reused, no migration is needed, and capture
policy remains native-only.

## Phase 1 Design Output

See [data-model.md](data-model.md), [contracts/settings-ui.md](contracts/settings-ui.md)
and [quickstart.md](quickstart.md). Post-design constitution review remains
PASS: the account projection has explicit secret boundaries, the recording
surface is a handoff, and calendar lifecycle semantics remain unchanged.

## Complexity Tracking

No constitution violations or new architectural dependency require a complexity
exception. The dedicated settings route module removes duplicated browser/
desktop branching rather than introducing a second UI framework.
