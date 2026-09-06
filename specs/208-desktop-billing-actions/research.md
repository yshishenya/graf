# Research: Desktop Billing Actions

## Decision 1: Use the current server-rendered forms as route inventory

- **Decision**: Allow exactly the user-visible billing POST paths already present in cabinet templates and matching server handlers.
- **Rationale**: This is the smallest complete source-backed scope and prevents speculative routes.
- **Alternatives considered**: Allow every path under `/billing` — rejected because it weakens the fail-closed desktop boundary.

## Decision 2: Extend the existing shared helper

- **Decision**: Add exact component patterns to `isBillingRoute`.
- **Rationale**: Every embedded navigation already passes through this helper; one change fixes all callers.
- **Alternatives considered**: Special-case individual buttons in WebView delegate — rejected because sibling forms would remain broken.

## Decision 3: Preserve original POST requests

- **Decision**: Do not change `DesktopCabinetNavigationRequestPolicy`; it already reloads only GET requests that need desktop headers.
- **Rationale**: POST body, CSRF field and idempotency-sensitive request must not be reconstructed or replayed.
- **Alternatives considered**: Inject desktop headers by reloading POST — rejected due duplicate/mutation risk.

## Decision 4: Separate code proof from payment proof

- **Decision**: Focused validation classifies all actions without submitting forms. Installed-app QA starts with promo preview; payment start remains an explicitly authorized test-shop action.
- **Rationale**: Route correctness can be proven without creating another payment.
- **Alternatives considered**: New end-to-end payment during every regression run — rejected as unnecessary and stateful.
