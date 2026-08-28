# Data Model: Desktop Billing Actions

No persistent entities or migrations are added.

The feature changes only navigation classification. Existing invoice, payment operation, subscription, promotion, referral, trial and payment-method models remain authoritative on the server.

## Route classification inputs

- Same-origin URL path components.
- Optional safe invoice number path component.
- Exact action component from the approved contract.

## State transitions

None are introduced. After navigation is allowed, existing server handlers own all billing state transitions and validation.
