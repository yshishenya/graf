# Implementation Plan: Web Cabinet HTMX Shell

**Branch**: `058-web-cabinet-htmx-shell` | **Date**: 2026-06-26 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/058-web-cabinet-htmx-shell/spec.md`

## Summary

Refactor the server-owned cabinet from the current monolithic Python string renderer into a small server-rendered cabinet shell with reusable Jinja components, one static CSS/token layer, centralized Lucide-style inline SVG icons, locally vendored HTMX 2.x for bounded region updates, and explicit CSRF protection for unsafe cookie-authenticated actions. The native macOS shell keeps capture-critical controls and local offline/upload truth; the WebView owns only online cabinet navigation and review surfaces.

## Technical Context

**Language/Version**: Python >=3.13 for `apps/server`; Swift 6.0 / macOS 14 for desktop WebView route-policy validation.

**Primary Dependencies**: Existing FastAPI stack (`fastapi>=0.115,<1`, currently locked as 0.136.3); add Jinja2 3.1.6 (`jinja2>=3.1.6,<4`) for server templates; vendor `htmx.org` 2.0.10 as a local static asset; keep existing inline Lucide-style SVG icon subset.

**Storage**: No database schema changes. Existing Postgres/MinIO/Temporal/deletion lifecycle data remains authoritative through `queries.py`, `view_models.py`, `access.py`, `egress.py`, and deletion services.

**Testing**: `pytest`/`pytest-asyncio` for server unit, integration, and contract tests; SwiftPM XCTest for macOS route policy and native shell invariants; Playwright/Chromium runtime checks for rendered HTML behavior and viewport overflow where needed.

**Target Platform**: Docker-hosted FastAPI server plus standalone browser and macOS `WKWebView` embedded cabinet.

**Project Type**: Server-rendered web service with a native macOS trust shell host.

**Performance Goals**: Full page and fragment rendering must stay within existing local test expectations; enhanced list updates visibly complete within one second for the current cabinet list limit; no added frontend build step in local CI.

**Constraints**: No Tailwind, UI-kit, SPA framework, CDN UI asset, external font, component preview app, design-system package, or frontend build pipeline in this slice. Unsafe cookie-authenticated actions require CSRF. Evidence remains metadata-only.

**Scale/Scope**: Current cabinet list/detail/deletion/auth surfaces plus future-ready navigation slots; one feature slice with at least four independently verifiable migration steps.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Reason |
|------|--------|--------|
| Capture-first MVP integrity | PASS | Capture, Stop, permissions, local queue, upload truth, and diagnostics remain native. |
| Visible consent and user control | PASS | WebView content cannot own or hide active capture truth; native Stop remains reachable. |
| Data boundary and secret discipline | PASS | No raw audio/transcript/secrets/signed URLs/private paths in templates, logs, evidence, or diagnostics. |
| Deletion truth and lifecycle accounting | PASS | Existing bounded deletion copy and deletion-report truth are preserved and centralized in components. |
| Spec-driven delivery with testable gates | PASS | Spec and clarify are complete; this plan creates research, data model, contracts, and quickstart before tasks. |
| UX, accessibility, localization, brand distance | PASS | Original 2brain Rec UI is preserved; Russian copy, WCAG target/focus basics, and clean-room review are explicit gates. |
| Deployment and validation discipline | PASS | Uses feature quickstart plus `infra/scripts/ci-local.sh`; no deploy is planned by this slice. |

## Project Structure

### Documentation (this feature)

```text
specs/058-web-cabinet-htmx-shell/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── cabinet-shell-contract.md
└── tasks.md              # Created by $speckit-tasks, not by this plan
```

### Source Code (repository root)

```text
apps/server/
├── pyproject.toml
├── src/twobrain_rec_server/
│   ├── main.py
│   ├── auth/
│   │   ├── dependencies.py
│   │   └── csrf.py
│   └── cabinet/
│       ├── web.py
│       ├── templates.py
│       ├── access.py
│       ├── egress.py
│       ├── queries.py
│       ├── view_models.py
│       ├── templates/cabinet/
│       │   ├── base.html
│       │   ├── auth/
│       │   ├── components/
│       │   ├── fragments/
│       │   └── pages/
│       └── static/cabinet/
│           ├── cabinet.css
│           ├── cabinet.js
│           └── htmx-2.0.10.min.js
└── tests/
    ├── contract/
    ├── integration/
    └── unit/

apps/macos/
├── RecApp/Sources/Cabinet/
└── Shared/Tests/
```

**Structure Decision**: Keep business/data/auth/lifecycle logic in existing server modules. `web.py` remains the FastAPI HTML route boundary and should stop owning bulk CSS, HTML strings, and inline JavaScript. Jinja templates own presentation composition, `cabinet.css` owns visual tokens/classes, `cabinet.js` owns only small component behavior not covered by native HTML/HTMX, and `htmx-2.0.10.min.js` is the only progressive enhancement library. macOS changes stay limited to exact route-kind policy and native/WebView shell invariants.

## Phase 0: Research

See [research.md](./research.md).

## Phase 1: Design And Contracts

See [data-model.md](./data-model.md), [contracts/cabinet-shell-contract.md](./contracts/cabinet-shell-contract.md), and [quickstart.md](./quickstart.md).

## Post-Design Constitution Check

| Gate | Status | Reason |
|------|--------|--------|
| Capture-first MVP integrity | PASS | Contracts keep native capture and local upload truth outside server-rendered UI. |
| Visible consent and user control | PASS | Desktop invariants and route policy tests remain explicit validation requirements. |
| Data boundary and secret discipline | PASS | Contract requires metadata-only evidence and safe template data only. |
| Deletion truth and lifecycle accounting | PASS | Contract keeps deletion report, bounded copy, and unsafe action handling server-owned. |
| Spec-driven delivery with testable gates | PASS | Plan artifacts are complete enough for checklist, tasks, analyze, and implementation. |
| UX, accessibility, localization, brand distance | PASS | Component catalog, Lucide icon vocabulary, CSS tokens, Russian copy, and target/focus gates are fixed. |
| Deployment and validation discipline | PASS | Quickstart includes targeted checks and canonical local CI; no release action is included. |

## Complexity Tracking

No constitution violations. The slice deliberately rejects a frontend build pipeline, external UI framework, and broad design-system package.
