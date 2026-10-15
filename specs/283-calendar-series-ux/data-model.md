# F283 data model

No storage changes. Series and recording linkage remain F279 authoritatively scoped identities.

- View: all (legacy), upcoming (ends_at > anchor), history (ends_at <= anchor).
- Cursor context: existing owner/session/workspace/series/from/to; new views also view/anchor. Anchor is timezone-aware UTC server time, immutable across pages. No authority comes from client fields. Mixed view/session/range cursor →422.
- Row projection: existing privacy-masked event fields, authorised recordings, recordings_partial; temporal_state derived from signed anchor (upcoming/ongoing/history), no hidden timestamps added.
- Client transient state: active view, cursor, loaded count, current request controller and identity. Clear on close/switch, reauthorize on refresh. No persistent cache or cross-series data.
