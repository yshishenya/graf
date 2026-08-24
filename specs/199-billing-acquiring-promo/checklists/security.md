# Security Checklist: Billing acquiring and promo closeout

- [x] Raw promo codes are not persisted, logged, placed in URLs or analytics.
- [x] Preview remains authenticated, owner-only, CSRF-protected and rate-limited.
- [x] Campaign writes use the existing maintenance RLS boundary.
- [x] Checkout revalidates catalog, eligibility, floor, consent and launch gates.
- [x] No provider mutation is reachable from preview or provisioning dry-run.
- [x] No secrets, payment data or private meeting data enter evidence.
