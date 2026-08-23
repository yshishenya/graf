# Data model: meeting summary experience

Новая database migration не требуется. Feature использует существующую immutable lineage.

## Existing entities

### Meeting

- `current_outcome_set_id`: единственный accepted pointer.
- `deletion_epoch`, deletion state and access context: hard fences для generation/acceptance.

### MeetingOutcomeSet

- Immutable result for one transcript/template/generator lineage.
- `status`: available/partial/blocked.
- `revision_state`: candidate/accepted/rejected/stale/expired.
- `generator_kind`: AI or historical deterministic provenance.
- Template key/version, source fingerprint, content hash, accepted/generated timestamps.

### MeetingOutcomeItem

- Category, order, atomic text, optional owner/due only for action items.
- One to eight exact transcript source references.

### MeetingOutcomeGenerationAttempt

- Candidate lifecycle, request intent, idempotency key, template/prompt/model provenance, failure code and bounded metadata.
- `automatic_baseline` distinguishes system initial generation from `manual_format` and `manual_refresh`.

### OutcomeDispatchIntent / Generation Call

- Durable dispatch/inference/observability lineage. No inference retry after an ambiguous response-bearing boundary.

## State transitions

```text
no accepted result
  -> automatic candidate queued/generating
  -> validated available
  -> accepted atomically only if current_outcome_set_id is still null

accepted result exists
  -> manual format/refresh candidate
  -> ready preview
  -> accepted only by explicit user action
  -> previous accepted row remains immutable
```

Terminal/invalid paths preserve the accepted pointer. Source change, deletion epoch change, access loss, template/prompt mismatch or validation failure prevents acceptance.

## Compatibility

- Existing accepted deterministic rows remain readable/shareable/exportable until replaced or deleted under existing lifecycle rules.
- New revision-scoped deterministic extraction is not published as ready user content.
- No backfill rewrites historical accepted truth.
