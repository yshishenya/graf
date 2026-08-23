# Operations Checklist: Billing acquiring and promo closeout

- [x] Test and production YooKassa environments stay separate.
- [x] Checkout remains default-off until Feature 140 gates are approved.
- [x] Campaign provisioning has dry-run, explicit execute and disable paths.
- [x] Provider canary, receipt/VAT, webhook, renewal, refund observation and
  four-eyes approval remain required before launch.
- [x] Rollback/stop procedure remains in `docs/runbooks/billing-launch.md`.
