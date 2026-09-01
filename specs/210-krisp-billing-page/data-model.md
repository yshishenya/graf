# Data Model: billing presentation

Feature 210 does not add tables, migrations or provider objects. It reorganizes
existing safe projections.

## BillingPresentationState

Ephemeral server view model assembled from existing workspace, catalog,
subscription, payment method, billing operation and invoice data.

- current plan label and state: free, trial, personal, active,
  cancelled-renewal or expired;
- billing owner/role and selected workspace identity;
- current/list price, cycle, next billing date and storage/usage summary;
- payment method display mask or empty state;
- latest operation/invoice safe number, amount, date and status;
- capabilities: can compare, checkout, manage, resume, cancel, refresh or only view;
- availability: ready, pending, reconciliation, manual resolution, unavailable.

Invariant: unavailable or non-owner states never infer monetary data or expose a
mutation action. Pending states expose at most one safe continuation.

## PlanChoice

Existing catalog projection for a real GRAF plan and cycle.

- plan code and truthful display name;
- month/year cycle;
- list amount and optional discount/saving already calculated by the server;
- real included capabilities and limitations;
- selected state and safe checkout link.

Invariant: browser choice is presentation only; checkout re-reads the approved
catalog and validates the cycle.

## CheckoutSummary

Existing ephemeral preview containing plan/cycle, list amount, one applicable
discount, amount due today, future amount, next charge date, receipt contact and
offer/recurring consent requirements.

Invariant: preview creates no invoice, operation, promo reservation or provider
request. Only existing `POST /billing/checkout/start` can mutate money state.

## InvoiceHistoryItem

Existing safe invoice projection: safe number, amount/currency, cycle, status,
created/paid dates, discount summary, masked payment method and receipt link
state. Provider identifiers, credentials and payloads are excluded.

## ReferenceDeviation

Metadata-only QA record with surface, observed reference behavior, GRAF
behavior, reason (`truthfulness`, `accessibility`, `security`, `legal`,
`privacy`, `unsupported capability`) and acceptance. It is evidence, not a
runtime entity.
