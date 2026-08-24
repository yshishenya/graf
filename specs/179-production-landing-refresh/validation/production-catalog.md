# Production catalog status

Status: PROVISIONED; PAID CHECKOUT REMAINS FAIL-CLOSED.

On 2026-08-24 the approved catalog was provisioned through the production
`rec-maintenance` role on runtime SHA `65d46da918361ecba0845a67a69a2ef22f82deae`.
The readback returned exactly these immutable `billing_plan_versions` rows:

- `personal` v1, month: 100,000 minor RUB units (1,000 RUB), RUB;
- `personal` v2, year: 1,000,000 minor RUB units (10,000 RUB), RUB;
- both rows: 2,000,000,000 bytes, unlimited processing, enabled for checkout,
  `offer_version=personal-2026-08-21`, no expiry.

The same readback found zero invoices, billing operations and saved payment
methods created by this action. Public `/offer` shows both approved prices;
checkout and provider observation remain disabled. No provider payment or
receipt mutation was performed.
