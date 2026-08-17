# Data Model: macOS Dev Channel and Native Home

No server data or database migration is introduced.

## Channel identity

- `production`: existing `pro.2brain.graf`, application-support `GRAF`,
  production Sparkle metadata.
- `local`: existing disposable `pro.2brain.graf.local` behavior.
- `dev`: stable installed `pro.2brain.graf.dev`, application-support
  `GRAF Dev`, loopback-only origin, no Sparkle feed.

The channel is derived from explicit process configuration and bundle metadata;
it is not user-editable at runtime.

## Navigation state

The existing WKWebView truth remains authoritative:

- safe back/forward entries from `backForwardList`;
- current safe document for reload;
- `fallbackRequest` for canonical Home.

No persisted native history or second route source is added.
