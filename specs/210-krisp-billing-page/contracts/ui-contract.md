# UI Contract: GRAF billing hierarchy and states

## Overview

`GET /billing` renders one `h1` and ordered labelled sections:

1. current plan/price/status and one primary action;
2. one upgrade/value offer when truthful and actionable;
3. selected workspace and billing owner/role (truthful seat-management deviation);
4. payment method or named empty state;
5. latest invoice/operation summary plus link to complete history.

Pending, unknown, reconciliation, manual-resolution, disabled-store and
non-owner states suppress competing checkout actions. Each state exposes one
plain-language status and one safe next action at most.

## Plans

`GET /billing/plans` shows only approved GRAF catalog options. Month/year uses a
named fieldset/radio group or equivalent native semantics, has a visible selected
state, and every actionable choice links to the existing checkout with explicit
`cycle`. Price, savings and limitations stay server-authored.

## Checkout

`GET /billing/checkout` renders a compact order summary: selected plan, cycle,
list amount, one discount, amount due today, future renewal, receipt contact and
required offer/recurring consents. Promo disclosure and
`POST /billing/checkout/preview` remain usable without JavaScript and do not
create financial state. Existing start route remains the sole final mutation.

## Shared interaction and accessibility

- Native links/buttons/forms are keyboard reachable in visual order.
- One visible primary action per state; no fake disabled anchors.
- Focus-visible is not clipped; disclosure communicates expanded state; form
  errors are field-associated; async/status text uses the existing status/alert
  live-region contract.
- Controls preserve at least the repository's 40 px critical target contract,
  WCAG 2.2 AA contrast and meaningful accessible names.
- Core navigation, overview, plans, checkout, promo preview and history remain
  meaningful without JavaScript.
- Main content has no horizontal overflow at required viewports or 200% zoom.

## Truthfulness and provenance

GRAF branding/assets/copy are used. KRISP code, assets, fonts, API data and
private screenshots are not used. Geometry may reproduce observed behavior only
where compatible with accessibility, security, law and real GRAF capabilities.
