# Security and privacy checklist: Feature 195

**Статус**: частично закрыт локальными code/contract checks; live security
verification и production evidence остаются незакрытыми.

## Trust boundary

- [x] MediaScribe credentials exist only in server/worker secret storage.
- [x] Browser and macOS app cannot call MediaScribe directly or choose provider URLs.
- [x] All processing/detail/retry commands enforce workspace and meeting access plus CSRF where applicable.
- [x] Provider job ids, idempotency keys, request bodies and signed URLs are never ordinary user-facing data.
- [x] Relative provider download paths are resolved server-side and allowlisted.

## Data minimization

- [x] Temporal input/history contains only bounded identifiers, stage, safe code and timestamps.
- [x] Logs and analytics exclude audio, transcript, summary, speaker labels, filenames and free-form provider details.
- [x] `X-Request-ID` is treated as support metadata and redacted from public/share projections.
- [x] Provenance is bounded and policy-approved; model/build metadata cannot contain content.
- [ ] Provider raw payload retention and deletion behavior are documented and tested.

## Retry and abuse controls

- [x] Manual retry is authorized and idempotent across tabs/devices.
- [x] A retryable state cannot be used to create a second provider job.
- [x] Unknown upload outcome always reconciles with the same key/body before any new attempt.
- [x] New key/provider job requires explicit user action after terminal evidence and new quota admission.
- [x] Countdown endpoint/fragment does not cause one request per visible second.
- [x] Provider 429/503 and local command retries have bounded backoff and no thundering herd.

## Deletion and content exposure

- [x] Transcript remains hidden until same-attempt diarization readiness is validated.
- [x] Summary failure cannot accidentally hide or re-publish unrelated artifacts.
- [x] Delete fences prevent late import, replay and stale workflow from resurrecting content.
- [x] Provider `202 cancelling` is never presented as completed deletion.
- [x] Exports/downloads obey artifact state and existing access/deletion policy.
- [x] No real private meeting data is used in specs, fixtures, screenshots or logs.

Отметки основаны на source review, contract/unit tests и полном local CI. Не
подменяют live provider, production Temporal, penetration test или deployed
secret/config audit.
