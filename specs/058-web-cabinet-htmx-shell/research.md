# Research: Web Cabinet HTMX Shell

## Decision: Server-Rendered Jinja Templates

**Decision**: Use Jinja2 3.1.6 with FastAPI/Starlette template responses for cabinet HTML.

**Rationale**: The current cabinet is already server-rendered but trapped in a 3,491-line `web.py` that mixes routes, CSS, HTML, inline JavaScript, and helper rendering. Jinja moves presentation into templates without changing the product ownership model or adding a client application.

**Alternatives considered**:

- Continue Python string rendering: rejected because it preserves the monolith and makes component reuse brittle.
- React/Vue/Svelte/Next: rejected because the cabinet does not need a client app, hydration, client stores, or a frontend build pipeline.
- Web Components UI kit: rejected for this slice because it adds runtime/theming contracts before the server-rendered boundary is cleaned up.

## Decision: Static CSS Tokens, No Tailwind

**Decision**: Use one local `cabinet.css` file with CSS custom properties, semantic component classes, responsive rules, focus states, and no build step.

**Rationale**: The repository currently has no frontend build pipeline. The product already has a specific dark/light-neutral visual language, Russian copy constraints, deletion truth states, embedded WebView constraints, and metadata-safe evidence requirements. A static CSS/token layer removes inline CSS from `web.py` while keeping the smallest operational surface.

**Alternatives considered**:

- Tailwind v4: rejected for feature 058 because it introduces a new toolchain before the HTML/CSS split is complete.
- daisyUI/Flowbite/shadcn/ui: rejected because they bring external component vocabulary, styling contracts, or React-oriented assumptions that do not own 2brain Rec deletion/auth/WebView semantics.
- Storybook/component preview app/design-system package: rejected because fixtures and runtime checks are enough until reuse exceeds the cabinet.

## Decision: Centralized Lucide-Style Inline SVG Icons

**Decision**: Keep the existing Lucide-style inline SVG path subset as the cabinet icon vocabulary and centralize it in the Jinja component layer.

**Rationale**: Lucide is an SVG icon library, not a UI framework. The current `_ui_icon()` helper already uses 24x24 inline SVG with `currentColor`, rounded line caps/joins, and stroke width 2. Centralizing this prevents ad hoc emoji, Unicode symbols, and one-off SVG styles.

**Alternatives considered**:

- Icon fonts: rejected because they add font assets and can degrade accessibility/fallback behavior.
- CDN icon scripts: rejected because the cabinet must avoid CDN runtime assets.
- Hand-drawn per-page SVG: rejected because it causes visual drift.

## Decision: Vendored HTMX 2.x Only For Bounded Enhancements

**Decision**: Vendor `htmx.org` 2.0.10 locally and use it only for bounded cabinet regions such as list filtering/sorting, fragment refresh, and mutation feedback.

**Rationale**: HTMX fits the server-owned truth model: the server still decides meeting state, authorization, deletion lifecycle, and rendered copy. Local vendoring avoids CDN dependencies and keeps deployment self-contained.

**Stable dependency evidence**: On 2026-06-26, the selected local asset is pinned as `htmx.org` 2.0.10 with a source/license manifest at `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/htmx-2.0.10.source.txt`. Pre-release HTMX lines remain out of scope for this feature.

**Alternatives considered**:

- HTMX v4 or prerelease lines: rejected because the feature requires stable components only.
- Custom `fetch()` for all interactions: rejected because it repeats partial-update plumbing and already created a CSRF-sensitive delete path.
- Global boosted navigation for the entire shell: rejected because it can blur full-page and fragment contracts, especially in WebView/auth/error states.

## Decision: Session-Bound CSRF For Unsafe Web Actions

**Decision**: Add a session-bound anti-forgery guard for unsafe browser/WebView cabinet actions. Forms and HTMX requests submit the token through hidden fields or `X-CSRF-Token`; failures return bounded copy and do not mutate state.

**Rationale**: The cabinet uses cookie-authenticated owner sessions. `SameSite=Lax`, `Secure`, and `HttpOnly` are necessary but not enough for unsafe same-origin browser actions. Delete/share/export/retention/account actions must fail closed when CSRF proof is absent or stale.

**Alternatives considered**:

- Rely only on SameSite cookies: rejected because the spec requires anti-forgery in addition to cookie attributes.
- Per-page ad hoc nonce: rejected because unsafe action handling must be consistent across browser and WebView routes.

## Decision: Exact Desktop Route Kinds

**Decision**: Replace broad substring route blocking with exact route-kind classification for desktop embedded navigation.

**Rationale**: The current route policy allows list/detail/auth and blocks broad words such as `delete`, `settings`, and `upload`. This risks accidental blocks as the server-owned cabinet grows, for example deletion-report and future online sections. Exact route kinds make review, auth recovery, safe help links, blocked native/local routes, and unknown routes testable.

**Alternatives considered**:

- Keep substring matching: rejected because it can block safe online routes and hide contract drift.
- Let WebView navigate freely: rejected because native capture/local routes must never be controlled by remote HTML.

## Decision: Incremental Migration Order

**Decision**: Deliver the refactor in four safe steps: tests/contracts first, template/static foundation, list/auth migration, detail/deletion/desktop route migration.

**Rationale**: The cabinet is actively changing. The smallest safe path is to preserve URLs and existing route handlers while moving rendering behind them one surface at a time.

**Alternatives considered**:

- Full rewrite of all pages at once: rejected because it hides regressions and delays validation.
- Only split CSS from `web.py`: rejected because it leaves HTML and inline JavaScript duplication in place.
