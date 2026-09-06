# MediaScribe v0.5.3 boundary contract

## Accepted result shape

GRAF consumes the public `/v1` result. `diarization` may be absent, `null` or a list. Each list item requires `start`, `end`, `speaker` and `text`; `source_role` is optional and is one of `mic`, `incoming`, `mixed` when present. `words` is optional or null and, when present, contains WordItem objects with required `word` and optional nullable `start`, `end`, `probability`.

## Client obligations

- Use only `/v1` public routes.
- Preserve one idempotency key and equivalent multipart body for an uncertain upload outcome.
- Use `Retry-After`, bounded jitter/fallback and durable Temporal waits.
- Stop on terminal errors and do not treat `queue_position` as ETA.
- Read downloads only from provider result references; never persist signed URLs.
- Preserve complete segment text even when word timing is incomplete.
- Treat provider diarization rows as final blocks; do not locally merge or split them.

## GRAF projections

The typed boundary may retain forward-compatible provider extras in memory, but user/API projections are allowlisted. Safe projections expose GRAF artifact state, source-role labels and bounded diagnostics, not credentials, signed URLs, private provider error detail or raw provider payloads.
