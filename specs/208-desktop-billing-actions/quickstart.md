# Quickstart: Desktop Billing Actions

## Prerequisites

- Run from the clean Feature 208 worktree.
- Do not create a new payment during focused validation.
- Keep YooKassa in test-shop; do not edit production runtime configuration or database state.

## Focused validation

```sh
swift test --package-path apps/macos --filter DesktopCabinetBillingHandoffTests
swift test --package-path apps/macos --filter DesktopCabinetRoutePolicyTests
swift build --package-path apps/macos
```

Expected:

- Every path in `contracts/desktop-billing-routes.md` is `.allow` with billing route kind.
- Unknown static and dynamic sibling routes remain `.blockWithMessage`.
- Existing offer, referral, payment-provider and billing GET tests still pass.

## Repository gate before PR

```sh
infra/scripts/ci-local.sh --fast
```

Full CI is reserved for the exact release candidate.

## Installed-app smoke after signed release

1. Confirm the installed version and test-shop environment.
2. Open `Тариф и оплата → Выбрать тариф`.
3. Calculate the existing promo preview and confirm the checkout remains visible.
4. Confirm subscription, invoice and receipt state are unchanged by preview.
5. Exercise payment start only under the user's explicit test-payment authorization and never create a duplicate payment.
6. Confirm no supported action shows `Функция недоступна`.

Release proof additionally requires exact SHA, full CI, Developer ID, notarization, stapling, Gatekeeper, Sparkle publication and installed-app validation.
