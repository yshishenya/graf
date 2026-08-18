# Research: Понятный toggle боковой панели

**Date**: 2026-08-18

## Sources and applied principles

- WAI-ARIA Authoring Practices, `Tooltip Pattern`, accessed 2026-08-18:
  https://www.w3.org/WAI/ARIA/apg/patterns/tooltip/ — a tooltip supplements
  an already named control; focus must expose the same help as hover and the
  tooltip must not become a competing interactive target.
- WCAG 2.2, Success Criterion 1.4.13 Content on Hover or Focus, accessed
  2026-08-18: https://www.w3.org/WAI/WCAG22/Understanding/content-on-hover-or-focus.html
  — hover/focus content needs predictable visibility and must not obscure the
  triggering control or prevent access to adjacent content.
- MDN, `aria-expanded`, accessed 2026-08-18:
  https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Attributes/aria-expanded
  — state is exposed on the control that owns the expandable region.

## Clean-room decision

Krisp-style compact rails and familiar panel icons are treated only as broad
interaction references already captured by Feature 069/159. GRAF keeps its
existing shell, icon set, Russian copy and layout. The minimal improvement is a
non-interactive tooltip driven by the existing action label, not a copied
component or onboarding pattern.

## Decision

Use the current shared button and dynamic `setRailPinned` state as the single
source of truth. Add a CSS hover/focus tooltip using the current action text;
keep the native `title` as a fallback. Do not add a tooltip library, new state,
or a second control.

