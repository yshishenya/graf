# Data Model: Yandex ID account selection

No new persisted entities or fields are introduced.

- The provider callback continues to yield the verified Yandex provider
  subject.
- The existing GRAF browser session remains the only internal session created
  by this flow.
- OAuth codes, tokens, raw profiles, and provider cookies remain transient and
  are not added to logs or evidence.
