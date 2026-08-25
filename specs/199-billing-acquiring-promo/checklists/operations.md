# Operations Checklist: Billing acquiring and promo closeout

- [x] Test and production YooKassa environments stay separate.
- [x] Checkout remains default-off until Feature 140 gates are approved.
- [x] Campaign provisioning has dry-run, explicit execute and disable paths.
- [x] Provider canary, receipt/VAT, webhook, renewal and refund observation
  remain required before production launch.
- [x] Rollback/stop procedure remains in `docs/runbooks/billing-launch.md`.
- [x] Pre-`provider_id` recovery reuses the existing operation/key and stops at
  provider-key expiry without creating a second charge identity.
- [x] Status refresh distinguishes a real provider poll from `processed=0`.
