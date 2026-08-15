# Quickstart: embedded billing

1. Launch the notarized GRAF app with a valid desktop session.
2. Open Settings → «Тарифы и оплата».
3. Confirm the page renders inside the app and no browser window opens.
4. Navigate through plans, usage, history, payment method, subscription, checkout and operation status.
5. With a test-shop confirmation URL on `yookassa.ru`/`api.yookassa.test`, confirm provider navigation is allowed and return goes to local billing status.
6. Confirm an unallowlisted HTTPS host and non-HTTPS provider URL are blocked.
7. Run the focused XCTest target and `infra/scripts/ci-local.sh --fast`.
