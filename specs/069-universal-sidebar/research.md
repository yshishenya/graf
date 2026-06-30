# Research: Universal Cabinet Sidebar

## Decision: Use one server-owned cabinet shell/sidebar contract

**Rationale**: The current cabinet is server-rendered and already centralizes most page rendering through `_page_shell(...)`. Jinja supports reusable template units and template composition, so the smallest durable architecture is to move the duplicated full-page shell/sidebar markup into one shared cabinet shell contract while keeping pages as content templates.

**Alternatives considered**:

- Keep separate page-owned sidebars: rejected because meetings and calendar settings already drift in brand/header/toggle behavior.
- Introduce a client-side component layer: rejected because the existing cabinet does not need a new frontend runtime to solve shared layout.
- Merge admin navigation now: rejected because admin has a different role and information architecture.

**Sources**:

- Jinja template documentation: https://jinja.palletsprojects.com/en/stable/templates/

## Decision: Preserve content-only fragment boundaries

**Rationale**: The cabinet uses dynamic partial updates. htmx supports targeting and selecting pieces of responses, so full shell rendering must stay separate from fragment rendering. Full page responses may contain the shell; fragment responses must contain only the intended content region.

**Alternatives considered**:

- Let fragments include a shell and rely on client selection: rejected because it allows accidental nested shells.
- Make every dynamic update reload a full page: rejected because it degrades current meeting list and settings workflows.

**Sources**:

- htmx documentation: https://htmx.org/docs/

## Decision: Treat the sidebar as the primary navigation landmark

**Rationale**: A repeated primary navigation region needs a stable accessible purpose across pages. The current active item behavior should expose exactly one current destination, while keyboard focus must remain visibly distinct from selected state.

**Alternatives considered**:

- Use visual active state only: rejected because assistive technology users need a programmatic current destination.
- Hide labels in compact embedded mode without accessible names: rejected because compact rail must remain usable with keyboard and assistive technology.

**Sources**:

- WAI navigation landmark guidance: https://www.w3.org/WAI/ARIA/apg/patterns/landmarks/examples/navigation.html
- MDN `aria-current`: https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Attributes/aria-current
- WCAG Focus Visible: https://www.w3.org/WAI/WCAG22/Understanding/focus-visible.html

## Decision: Keep desktop embedded navigation web-owned

**Rationale**: The native app should own capture controls and local safety, not product navigation. The same server-rendered sidebar can adapt to embedded routes and compact rail behavior without reintroducing native product navigation.

**Alternatives considered**:

- Recreate product navigation in the native app: rejected by product direction and because it creates a second source of truth.
- Hide cabinet navigation in desktop embedded mode: rejected because settings and meetings would become harder to reach and would diverge from web behavior.

## Decision: Validate by contract tests and existing integration routes

**Rationale**: This feature is primarily a markup/layout contract. Tests should assert one shared shell, one primary sidebar, correct active states, content-only fragments, and desktop embedded rail contract. Full local CI remains the closeout gate because the feature touches shared user-facing UI.

**Alternatives considered**:

- Screenshot-only validation: useful later but insufficient as the primary gate because source/route contracts are already testable.
- Manual-only validation: rejected because future regressions would be easy when adding pages.
