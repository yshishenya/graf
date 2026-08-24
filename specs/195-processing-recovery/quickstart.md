# Quickstart acceptance scenarios

**Feature**: `195-processing-recovery`
**Назначение**: локальная acceptance-матрица Feature 195. Сценарии ниже не
являются production smoke и не подключаются к реальному MediaScribe без
отдельного разрешения.

## Текущее evidence

Проверено на текущем dirty worktree `195-processing-recovery`:

- `20 passed` — focused unit/contract suite для recovery, v1 MediaScribe,
  Temporal workflow, safe provenance и download boundary.
- `1240 passed` — повторный `infra/scripts/ci-local.sh --fast` после
  provenance-only regression check; Ruff/compile также pass.
- `3413 passed, 1 skipped` — полная parallel PostgreSQL server matrix;
  `52 passed, 1 skipped` — strict RLS matrix.
- `762 passed` — macOS Swift tests; macOS ContractValidation, legacy-audio
  guard, Python compile, Ruff и production compose validation — pass.
- `56 passed` — отдельный focused PostgreSQL processing/export/migration
  запуск через isolated disposable runner; дополнительно `10 passed` для
  result-idempotency и worker-restart regression suites.
- `git diff --check` — pass; unmerged paths — none.

Проверены кодом и локальными контрактными тестами: transcript visibility,
independent summary projection, bounded retry parsing/scheduling, generation
fence, manual Update/Signal boundary, same-key unknown-outcome reconciliation,
new-attempt admission, safe `/v1` MediaScribe contract, allowlisted artifact
downloads, bounded durable provenance, deletion pending truth и desktop status
projection. Не проверены в этой сессии: live MediaScribe, production Temporal
cluster/worker restart, browser E2E/screenshots, dashboards/analytics in a
live source and production deletion receipts.

## Test fixture boundary

Использовать fake MediaScribe transport и synthetic WAV fixture. Не использовать
реальные встречи, transcript, audio, credentials или provider production jobs.
Каждая fixture job должна иметь:

- opaque fake job id;
- deterministic `X-Request-ID`;
- configurable `Retry-After`/`next_retry_at`;
- explicit `code`, `retryable`, `status`, `queue_state`;
- same-key replay and conflict behavior.

## Scenario matrix

| ID | Setup | Expected result |
|---|---|---|
| Q1 | transcript available, diarization absent | transcript tab hidden; processing explains speaker attribution pending |
| Q2 | transcript + diarization ready, summary running | transcript visible; summary independently «готовится» |
| Q3 | transcript + diarization ready, summary failed | transcript remains visible; summary has separate failure action |
| Q4 | `409 result_not_ready`, `Retry-After=30` | durable `next_attempt_at`; countdown uses server timestamp; no busy polling |
| Q5 | retryable 503 without valid hint | bounded fallback schedule; no false exact promise; manual button visible |
| Q6 | countdown active, manual check | old generation no-op; one same-job check; timer reset; button busy/disabled |
| Q7 | automatic operation in-flight + manual click | no parallel operation; UI reads current state |
| Q8 | POST response lost after provider accepted | same multipart/key reconciliation finds original job; zero duplicate jobs |
| Q9 | same key with changed body | `409 idempotency_conflict`; no automatic re-upload |
| Q10 | `failed/invalid_audio_payload` | no countdown; human copy; explicit new attempt only after user action |
| Q11 | result imported, summary fails | transcript/diarization/playback remain available |
| Q12 | worker crash after submit | restart reconciles same job/key and resumes |
| Q13 | worker crash after import | hash/idempotency prevents duplicate segments and preserves availability |
| Q14 | delete while polling/import | deletion epoch blocks late write; provider receipt required |
| Q15 | unknown provider status/queue state | raw bounded value retained; UI safe «состояние уточняется», no false terminal |
| Q16 | background tab/refresh | countdown recalculated from server timestamp; list/detail/desktop parity |

## Minimum executable checks for implementation phase

1. API adapter contract tests assert every new polling/result request starts with
   `/v1` and records response headers.
2. Result projection tests assert the visibility invariant for all combinations
   of transcript/diarization/summary states.
3. Retry state tests assert valid hint, missing hint, invalid hint, deadline,
   manual override and duplicate commands.
4. Idempotency tests assert lost POST response produces one fake provider job and
   same-key conflict never retries with a new key.
5. Temporal time-skipping tests assert durable sleep and stale generation no-op.
6. Restart tests inject a crash at every stage boundary and compare the final
   PostgreSQL projection/hash.
7. Deletion tests assert `202 cancelling` is not shown as completed and late
   result cannot resurrect content.
8. Browser/embedded tests assert keyboard focus, disabled/busy button,
   screen-reader announcement, reduced-motion and background refresh.
9. Analytics tests assert allowlisted metadata only and no meeting/title/file/
   provider-id/content fields.

## Evidence to collect later

For each implementation slice attach:

- fixture name and expected machine states;
- database projection before/after;
- Temporal workflow/run version and time-skipping result;
- UI screenshot or browser assertion for list/detail/embedded surfaces;
- no-secret/no-content scan result;
- exact test command and pass/fail output.

Не прикладывать raw audio, transcript, provider JSON, signed URLs, API keys или
реальные private meeting titles.

## Closeout boundary

Эта feature-ветка не готова считаться production-release evidence: для этого
нужны живые MediaScribe и Temporal проверки, browser/embedded E2E,
операционные dashboards/alerts и отдельное approval на deployment. Commit,
push, PR и deploy в рамках этой проверки не выполнялись.
