# Contract: Desktop Billing Action Routes

All entries are same-origin and remain subject to existing server authorization, CSRF, tenant and billing gates.

## Static action paths

| Path | User action |
|---|---|
| `/billing/checkout/preview` | Calculate checkout price and discount |
| `/billing/checkout/start` | Start the authoritative checkout operation |
| `/billing/discounts/apply` | Select a promo code |
| `/billing/discounts/remove` | Remove selected promo code |
| `/billing/trial/activate` | Activate an eligible trial |
| `/billing/payment-method/delete` | Delete an allowed saved payment method |
| `/billing/subscription/cancel` | Disable future renewal |
| `/billing/subscription/resume` | Resume renewal with explicit consent |

## Dynamic action paths

| Pattern | Constraint |
|---|---|
| `/billing/checkout/status/{safe_number}/refresh` | `safe_number` passes existing safe path-component validation |
| `/billing/checkout/status/{safe_number}/continue` | `safe_number` passes existing safe path-component validation |

## Negative contract

- Additional segments are blocked.
- Unknown action names are blocked.
- Unsafe dynamic path components are blocked.
- Query and fragment never expand the path allowlist.
- External hosts and non-HTTP(S) schemes keep their existing decisions.
