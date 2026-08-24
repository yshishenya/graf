# Contract: MediaScribe v1 client boundary

**Feature**: `195-processing-recovery`
**Статус**: proposed server-side adapter contract

## Boundary

Только GRAF server/worker обращается к MediaScribe. Browser и macOS app не
получают API key/Bearer token, provider job id, signed download URL или сырой
provider response.

Основной источник формата —
`/Users/yshishenya/Downloads/openapi-v1.json`. Семантика —
`/Users/yshishenya/Downloads/mediascribe-client-api.md`. Legacy `/jobs` и
`/auth/login` не должны использоваться в новом adapter code.

## Operations

| Adapter operation | HTTP | Обязательные правила |
|---|---|---|
| `get_capabilities` | `GET /v1/capabilities` | snapshot с TTL; не зашивать лимиты навсегда |
| `get_version` | `GET /version` | сохранять safe build/provenance metadata |
| `submit_single` | `POST /v1/audio/transcriptions` | multipart, `diarize=true`, unique key |
| `submit_dual` | `POST /v1/audio/transcriptions/dual-track` | обе canonical tracks, unique key |
| `get_job` | `GET /v1/audio/transcriptions/{id}` | сохранить status и queue_state отдельно |
| `get_result` | `GET /v1/audio/transcriptions/{id}/result` | 409 not-ready становится polling decision |
| `get_summary` | `GET /v1/audio/transcriptions/{id}/summary` | не блокирует transcript |
| `list_jobs` | `GET /v1/audio/transcriptions` | cursor opaque; cursor не смешивать с filters |
| `delete_job` | `DELETE /v1/audio/transcriptions/{id}` | 200 и 202 — разные receipt states |
| `get_deletion` | `GET /v1/audio/transcriptions/{id}/deletion` | poll only by retry hint/bounded fallback |
| `download` | URL из `result.downloads` | auth server-side; не конструировать URL вручную |

## Submit contract

`202` означает durable acceptance. Adapter обязан сохранить:

- opaque `job_id` из JSON;
- `Location`, `Retry-After`, `Idempotency-Replayed`, `X-Request-ID`;
- request mode, flags, source fingerprint и exact multipart metadata;
- provider `status`, `queue_state`, `attempt`, `max_attempts` и
  `next_retry_at`, если присутствуют.

Для single используется `file`. Для dual используются `mic_file` и
`incoming_file`. `num_speakers` и `speaker_count_mode` передаются только при
явно принятом GRAF значении; отсутствие параметра означает automatic mode.

`Idempotency-Key` — stable per logical processing attempt. При неизвестном
исходе POST повторяется тем же ключом, тем же содержимым, безопасным именем и
content type. Новый ключ без terminal evidence запрещён.

## Polling contract

`status` и `queue_state` сохраняются независимо. `GET result`:

- `200` — валидировать и импортировать result;
- `409 + code=result_not_ready + retryable=true` — ждать не меньше
  `Retry-After`, затем повторить;
- `409 + job_failed/idempotency_conflict/job_deleting/...` — бизнес-решение,
  не generic retry;
- `404` — unknown/missing/access state, не создавать новый job автоматически;
- `429/502/503/504` — bounded retry по machine code/hint;
- `500` с `retryable=false` — terminal/manual resolution.

Machine code/readiness precedence:

1. `retryable` и `code` из Problem Details;
2. HTTP semantics;
3. `Retry-After`/`next_retry_at`;
4. safe fallback.

Свободный `detail` используется только для server diagnostics, не для
classifier и не как user copy.

## Result contract

Adapter принимает неизвестные будущие поля и сохраняет только allowlisted
нужные данные. Нормализация проверяет:

- `start >= 0`, `end >= start` и корректную последовательность;
- `source_role` как opaque input с явным safe alias map;
- duplicate text не создаётся только из-за наличия transcript и diarization;
- overlaps и dual-track пересечения не отбрасываются как ошибка;
- provenance сохраняется как metadata; отсутствие provenance не подменяется
  догадкой.

Результат импортируется как artifact revision. Для user projection:

```text
transcript_status=available
AND diarization is non-null and validated and non-empty
=> transcript visible
```

Если `transcript_status=unavailable` и
`transcript_reason=no_recognizable_speech`, это terminal transcript state.
Summary `running/ready/failed/null` обрабатывается отдельно.

## Error DTO

Минимальная внутренняя форма без body content:

```text
ProviderError {
  http_status: int | null
  code: safe string | null
  retryable: bool | null
  retry_after_seconds: int | null
  request_id: safe string | null
  job_id: opaque string | null
  error_origin: safe string | null
  egress_state: not_sent | accepted | unknown | response_received
}
```

`errors` из 422 можно использовать для server diagnostics после redaction.
Пароли, API key, multipart body, transcript и audio в error/log не попадают.

## Deletion

`DELETE` idempotent:

- `200`, `state=completed`, `deleted=true` — provider deletion confirmed;
- `202`, `state=cancelling`, `deleted=false` — сохранить `Location` и ждать
  `Retry-After`;
- `GET deletion` до `state=completed` не считается завершением.

При любом late result GRAF проверяет local deletion epoch до commit. После
provider confirmation обычные result/download links удаляются из projection.

## Compatibility and diagnostics

- Проверять `api_contract_version` из `/v1/capabilities` и `/version`;
- неизвестные enum values сохранять в raw bounded field и проектировать в
  `unknown_provider_state`, не падать на Pydantic enum;
- `X-Request-ID` и safe machine codes доступны support flow;
- provider job id хранится только server-side и не является персональным
  идентификатором пользователя;
- contract tests должны доказать отсутствие `/jobs` в новом adapter path.
