# Contract: Product Telemetry Gate

**Feature**: `094-product-activation-analytics`

## Purpose

The telemetry gate is the one low-friction personal acceptance that allows
normal desktop app, cabinet, and authenticated product use with bounded product
activation analytics.

## Gate Copy Must Disclose

- required Terms version
- Privacy/Personal Data processing documents
- PostHog as primary product analytics workspace if approved
- Yandex as web/ad/Webvisor/offline-conversion surface if approved
- event classes and product activation purposes
- replay/Webvisor boundaries
- direct desktop provider egress if approved
- retention/deletion limits
- provider-held aggregates and exported report limits
- forbidden data categories that will not be collected
- what happens if the user withdraws or refuses updated mandatory terms

## Gate States

| State | Product Access | Analytics Behavior |
| --- | --- | --- |
| `not_seen` | block normal product use | no product analytics |
| `accepted` | normal product use allowed | approved analytics only |
| `withdrawn` | limited to account/legal/export/deletion flows | stop future product analytics |
| `terms_update_required` | block normal use until accepted | stop new product analytics until accepted |
| `refused_updated_terms` | limited to account/legal/export/deletion flows | stop future product analytics |

## UX Rules

- One clear acceptance step during onboarding or first authenticated product use.
- No repeated prompts unless terms or telemetry scope changes.
- No hidden acceptance.
- No deceptive copy.
- No pretense that "accept all" authorizes unlimited future collection.
- Workspace/admin policy may require telemetry for normal product use but cannot
  secretly accept personal telemetry terms for the user.

## Implementation Blockers

- missing legal review
- missing product owner approval of gate copy
- missing provider list
- missing direct desktop egress disclosure when direct route is used
- missing retention/deletion statement
- missing forbidden-field list
- missing withdrawal/refusal behavior
- telemetry scope broader than approved contracts
