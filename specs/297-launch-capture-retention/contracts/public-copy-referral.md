# Contract: Public copy and referral

## Offer / checkout

- `recurring_consent` remains `checked` by default in `billing_checkout_content.html`.
- Offer must state: “Автопродление включено по умолчанию. Его можно снять до оплаты; разовая оплата доступна без автопродления.”
- Offer must not state: “Согласие не должно быть заранее отмечено” or equivalent.
- Offer and landing must state: “Одна запись — до 4 часов (14 400 секунд)” or equivalent.
- The 4-hour limit must match `Settings.max_recording_duration_seconds` (hard `le=14_400`).
- Checkout must keep the existing required offer consent and optional recurring consent semantics. Routes, CSRF, authorization, form method and quote/offer-version validation must not change; a regression test must cover them.
- No change to price, catalog, invoice, payment provider or renewal schedule.

## Referral

- Routes: `GET /r/{token}` and `GET /referral/{token}`.
- Active token: HTTP 200, invitation page.
- Expired/unknown/disabled: HTTP 410, clear unavailable page.
- Database unavailable: HTTP 503, retryable; this is not a 500 and must be documented in live checks.
- Never HTTP 500 for a token-shaped or arbitrary token.
- `public_analytics` may be absent; the auth analytics partial must use a safe default.
- No token, email or private path in logs/evidence.

## Regression checks

- Render referral page with and without `public_analytics`.
- Live HTTP check with valid, expired and unknown token.
- Template contract test for offer wording and 4-hour limit.
- No “без ограничения длительности” in `/offer` or `/`.
- Checkout still has exactly one `recurring_consent` checked checkbox and it is not `required`.
