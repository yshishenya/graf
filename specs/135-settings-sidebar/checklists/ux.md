# UX Quality Checklist: Боковая навигация настроек

**Feature**: [spec.md](../spec.md)

## IA and interaction

- [x] The sidebar is the primary settings navigation mechanism.
- [x] All five actionable categories are visible without horizontal scrolling;
  `/settings` remains a compact overview entry point.
- [x] Group labels describe user tasks, not authorization scopes.
- [x] The order is stable across browser and embedded surfaces.
- [x] The active category is visible and remains a link-consistent state; the
  overview page has no false active item.
- [x] Calendar and account provider-link subflows map to their parent item.

## Accessibility

- [x] Navigation uses semantic links rather than tabs or scripted controls.
- [x] The navigation has one clear landmark label.
- [x] Active state uses both visual treatment and `aria-current`.
- [x] Focus remains visible independently of hover and color.
- [x] Link targets meet the 44px minimum.
- [x] Group headings are not keyboard stops.
- [x] The 320px flow does not depend on horizontal scrolling.
- [x] Long labels wrap without widening the content beyond the viewport.

## Trust and product boundaries

- [x] The existing explicit route map remains the source of truth.
- [x] Scope copy remains visible in the category content.
- [x] Recording stays a native macOS handoff.
- [x] CSRF, auth, mutation and safe-account contracts are explicitly protected.
- [x] The structural reference does not import Krisp branding or copy.
