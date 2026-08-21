# Contract: Public Funnel

## Routes

| Route | Purpose | Required primary action |
|---|---|---|
| `/` | Explain GRAF, audience, result and price | Navigate to `/download` |
| `/download` | Show platform availability and requirements | Download the universal `graf.pkg` |
| `/login?next=/meetings` | Existing user entry | Existing auth flow, unchanged |
| `/privacy` | Personal-data policy | Read-only legal page |
| `/cookies` | Cookie/localStorage disclosure | Read-only legal page |
| `/terms` | Product use and recording responsibility | Read-only legal page |
| `/offer` | Payment, renewal, cancellation and refund terms | Synchronized with checkout truth |
| `/analytics-consent` | Exact analytics disclosure | Reflect immediate loading |

## Landing order

Header; hero without product image; audience and pain points; one product stage with three accessible tabs; pricing; FAQ; final CTA; legal footer.

All primary download actions use `href=/download`. No JavaScript-only navigation is allowed.

## Download handoff

- Exactly one fingerprinted package link to `downloads/graf.pkg`.
- One universal installer for Apple Silicon and Intel, minimum macOS 14.5.
- Windows and Linux are planned, visible and non-clickable.
- Package replacement remains the existing read-only runtime-mount process.

## Paid offer

- Monthly: 1,000 RUB.
- Annual: 10,000 RUB.
- Exact annual saving: 2,000 RUB.
- Trial: 7 days under current eligibility rules.
- Price display and offer version stay mutually consistent through the active catalog; checkout acceptance additionally requires current launch-gate evidence.
- If sale readiness is false, production publication of a payable claim is blocked.

## Accessibility

- Product tabs implement `tablist`, `tab`, `tabpanel`, `aria-selected`, roving focus and arrow/home/end behavior.
- Without JavaScript, all three results remain readable.
- Pricing and FAQ use native controls or equivalent keyboard semantics.
- Focus is visible; reduced motion is respected; no meaning relies on color alone.
