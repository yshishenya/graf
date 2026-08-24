# Contract: Browser Yandex ID account selection

## Authorization request

When `/login/yandex/start` creates a Yandex authorization redirect, the URL
MUST retain the existing `response_type`, `client_id`, `state`, and
`redirect_uri` parameters and add:

- `force_confirm=1`

The parameter MUST be present for Yandex only. VK ID authorization URLs MUST
remain unchanged.

## Callback and session

- The existing callback state, browser nonce, token exchange, client binding,
  and profile verification MUST remain in force.
- A GRAF session MUST be issued only for the verified provider subject returned
  by the Yandex callback.
- Provider denial or cancellation MUST remain a bounded failure with no OAuth
  material in the response or logs.

## Acceptance evidence

Automated tests prove URL construction and provider isolation. Manual browser
evidence with two Yandex accounts proves the provider actually lets the user
select the intended account.
