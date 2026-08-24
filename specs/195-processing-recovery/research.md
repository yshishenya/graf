# Research: восстановление обработки и ранняя расшифровка

**Feature**: `195-processing-recovery`
**Дата**: 2026-08-23
**Статус**: подготовка к реализации; код и runtime не меняются

## Как читать источники

Источники имеют разный статус и не должны смешиваться:

1. Запрос владельца продукта — источник пользовательского результата:
   расшифровка доступна только после готовой диаризации; при временном сбое
   видны следующий запуск, countdown и ручная кнопка.
2. `/Users/yshishenya/Downloads/openapi-v1.json` — машинный HTTP-контракт
   MediaScribe v1: пути, схемы, HTTP-коды и заголовки.
3. `/Users/yshishenya/Downloads/mediascribe-client-api.md` — семантика
   контракта: идемпотентность, retry, deletion, polling, result и runtime
   capabilities.
4. `/Users/yshishenya/Downloads/mediascribe-codex-client-migration.md` —
   инструкция клиенту по миграции. Это не разрешение на изменение GRAF и не
   замена OpenAPI; спорные детали проверяются по OpenAPI и runtime.
5. Исходный код GRAF — фактическое текущее поведение и границы переиспользования.
6. Product Design, Data Analytics и Temporal skills — методика проектирования,
   а не дополнительные продуктовые требования.

При расхождении статическая документация не должна превращаться в обещание
runtime: перед реализацией capability snapshot и `/version` нужно проверить в
целевом окружении.

## Что есть сейчас в GRAF

Проверенный поток находится на серверной стороне:

- `mediascribe/client.py` уже отправляет single/dual-track на `/v1`, но
  `poll_job()` и `fetch_result()` всё ещё используют `/jobs` и `/jobs/{id}/result`;
- клиент отбрасывает body и почти все полезные headers ошибки, включая
  `Retry-After`, `Location`, `X-Request-ID`, machine `code` и `retryable`;
- `MediaScribeJobStatus` закрыт перечислением старого набора состояний, поэтому
  forward-compatible неизвестные значения не могут быть сохранены безопасно;
- большой `run_processing_pipeline_activity` объединяет submit, polling и import.
  Внутри есть обычный `asyncio.sleep`, а не durable Temporal timer;
- текущая политика Temporal повторяет Activity, но не моделирует отдельные
  stages, provider job reconciliation и ручную команду пользователя;
- `ProcessingStatusResponse` сообщает только общий state и boolean-флаги, без
  `next_attempt_at`, retry class, manual action и независимого состояния
  каждого артефакта;
- `review_status()` возвращает `partial`, если готов только transcript или
  только diarization, а `transcript_state()` допускает текст с
  `partial_transcript`. Это прямо противоречит новой границе: обычный экран
  расшифровки не показывает текст до подтверждённой диаризации;
- copy для временных ошибок частично существует, но generic fallback
  «Обработка требует проверки оператором» не говорит, потеряна ли запись,
  когда будет следующий запуск и что может сделать пользователь.

При этом уже есть полезная база, которую следует сохранить:

- workspace-scoped `ProcessingWorkflow`, `MediaScribeJob`, `ProcessingResult`,
  `TranscriptSegment` и `DiarizationSegment`;
- unique-ограничения для active workflow, idempotency key и external job;
- deletion epoch/fence, result hash и audit event primitives;
- content-safe meeting review model, CSRF, RLS и server-only API key boundary;
- отдельный GRAF-owned summary/outcome pipeline и существующие экспортные
  ограничения.

## Что даёт MediaScribe v1

Новая интеграция должна использовать только `/v1`:

| Задача | Контракт |
|---|---|
| Runtime capabilities | `GET /v1/capabilities` |
| Runtime/build provenance | `GET /version` |
| Single-track upload | `POST /v1/audio/transcriptions` |
| Dual-track upload | `POST /v1/audio/transcriptions/dual-track` |
| Восстановление списка | `GET /v1/audio/transcriptions` |
| Статус job | `GET /v1/audio/transcriptions/{job_id}` |
| Полный result | `GET /v1/audio/transcriptions/{job_id}/result` |
| Отдельный provider summary | `GET /v1/audio/transcriptions/{job_id}/summary` |
| Удаление | `DELETE /v1/audio/transcriptions/{job_id}` |
| Receipt удаления | `GET /v1/audio/transcriptions/{job_id}/deletion` |
| Авторизованные downloads | только URL из `result.downloads` |

Важные сигналы:

- upload отвечает `202 Accepted`; это приём job, а не готовность результата;
- `status` (`uploaded`, `transcribing`, `diarizing`, `summarizing`, `ready`,
  `failed`, `deleting`) и `queue_state` (`waiting_for_dispatch`, `queued`,
  `processing`, `retrying`, `completed`, `failed`, `deleting`) — разные оси;
- `GET result` возвращает `409` с `code=result_not_ready`,
  `retryable=true`, `Retry-After`, `X-Job-Status` и `X-Queue-State`, пока
  result не готов;
- `summary` может быть `null`, `running`, `ready` или `failed` независимо от
  доступности transcript/diarization;
- ready result содержит transcript, diarization, overlap intervals, acoustic
  turns, `provenance` и относительные download URLs;
- если речь не распознана, возможен успешный result с
  `transcript_status=unavailable` и `transcript_reason=no_recognizable_speech`;
- решение о повторе принимается по machine `code`, `retryable`, HTTP-коду и
  `Retry-After`, а не по свободному тексту `detail`;
- потерянный ответ upload восстанавливается тем же multipart body и тем же
  `Idempotency-Key`. Новый ключ до reconciliation запрещён;
- `DELETE` может вернуть `200` с completed receipt или `202` с
  `Location`/`Retry-After`; окончательное удаление следует считать только по
  durable receipt.

## Продуктовые решения

### Первый полезный результат

`first_usable_result = transcript + confirmed diarization` для одного
`media_revision_id` и одной `processing_attempt_id`. Пока diarization не
подтверждена для той же попытки:

- provider transcript можно импортировать как внутренний промежуточный слой,
  но он не попадает в обычную вкладку «Расшифровка», export или search;
- UI показывает, что распознавание продолжается и speaker attribution ещё не
  готова;
- summary/playback не могут открыть transcript раньше этой границы.

После готовой диаризации transcript становится доступен независимо от summary.
Ошибка summary не меняет доступность transcript и имеет собственный action.
Пустой transcript с `no_recognizable_speech` — честный terminal artifact state,
а не бесконечный spinner.

### Retry и ручная команда

Нужно различать три класса:

| Класс | Пример | Автоматический retry | Действие пользователя |
|---|---|---:|---|
| `retryable` | `result_not_ready`, 429/503, timeout GET | да, по durable schedule | «Проверить сейчас» для той же job |
| `unknown_outcome` | timeout/502 после POST upload | reconciliation тем же key/body | не новая загрузка; показать «проверяем» |
| `terminal` | `invalid_audio_payload`, `job_failed`, idempotency conflict | нет | исправить запись или явно начать новую попытку |

В UI слово «перезапустить» не должно означать новый upload, пока provider job
ещё существует. Для активной/неопределённой job кнопка — «Проверить обработку»
и означает немедленно проверить/продолжить ту же логическую попытку. Новый
provider job создаётся только отдельным подтверждённым действием после
подтверждённого terminal failure и получает новый business attempt и новый
idempotency key.

`next_attempt_at` хранится на сервере. Countdown — проекция этой даты, а не
локальный источник истины. При ручной команде server-side claim/sequence
сбрасывает старый timer; повторный клик, другая вкладка и проснувшийся старый
timer получают актуальное состояние и не создают вторую операцию.

### UX-решение

Состояние на экране должно отвечать на четыре вопроса:

1. Что происходит сейчас?
2. Безопасна ли уже подготовленная расшифровка?
3. Нужно ли действие пользователя?
4. Когда будет следующая автоматическая проверка?

Для временного сбоя рекомендуемая структура copy:

> Сервис временно не ответил. Запись сохранена, GRAF попробует проверить её
> снова через `N` минут. Можно не ждать — проверить сейчас.

Это сообщение показывается только при `retryable` и не обещает точный срок,
если provider не дал валидный hint. При terminal failure copy объясняет
причину и следующий путь, без HTTP-кода, provider job id или сырого detail.

## Temporal: рекомендуемая роль

Temporal нужен как durable coordinator, а не как пользовательская база статусов:

```text
submit_or_reconcile
        |
        v
await_provider_result --(workflow.sleep(next_attempt_at))--+
        |                                                |
        v                                                |
import_result --> project_artifact_states --> GRAF summary
        |
        +-- manual Update: claim same retry slot / check same job
```

Практики:

- workflow-код только детерминированный; I/O, HTTP, DB и parsing выполняются в
  Activities;
- ожидание — `workflow.sleep()` с абсолютным server-owned deadline, не
  `asyncio.sleep()` в workflow и не браузерный таймер;
- одна Activity — одна bounded операция. Upload/reconcile, status, result,
  import и summary не должны быть одной четырёхчасовой Activity;
- automatic/manual retry сериализуются через workflow Update (рекомендуемый
  API для пользовательской команды с ответом) и DB row lock/unique fence.
  Signal допустим только как fallback для не требующих ответа внутренних
  событий;
- Activity RetryPolicy применяется к безопасным transport failures. Terminal
  provider codes и недоказанный POST outcome должны возвращаться в workflow как
  бизнес-состояние, а не бездумно ретраиться SDK-политикой;
- длинные upload/download/import Activities используют heartbeat и проверяют
  cancellation/deletion epoch;
- в Temporal history не кладутся аудио, transcript, summary, multipart body,
  signed URL, API key и большой provider JSON. В history идут только UUID,
  stage, safe code, timestamps, attempt number и bounded metadata;
- миграция уже запущенных workflow требует `workflow.patched`/versioning,
  совместимых payloads и replay tests; смена одного класса workflow без этого
  может сломать replay;
- task queue сначала общая с admission/rate limit и метриками fairness. Очередь
  на каждого tenant не нужна, пока измерения не покажут starvation;
- PostgreSQL остаётся authoritative для UI, RLS и deletion fences. Temporal
  query/read model можно использовать только как служебное дополнение.

## Data Analytics решения

Измеряем outcome, а не количество внутренних polling calls:

- time to first usable result (upload accepted → transcript + diarization
  visible);
- retryable failure rate и доля автоматических recovery;
- manual retry rate, duplicate-click suppression и manual retry success;
- unknown upload outcome reconciliation success;
- summary readiness/failure отдельно от transcript;
- terminal failure rate с безопасным reason code;
- restart recovery и stale timer incidents;
- deletion requested → provider confirmed.

Каждое событие — allowlist и metadata-only: surface, bounded duration/size
bucket, artifact state, safe reason code, retry class, attempt ordinal. Нельзя
отправлять meeting id, title, filename, provider job id, transcript, audio,
speaker label или свободный provider detail.

## Решения, которые оставить до реализации

- точные caps retry/deadline/fallback и правила jitter — configuration/ops
  decision после capability snapshot и нагрузочного теста;
- фактическая поддержка Temporal Update в установленной версии SDK и способ
  graceful fallback для старых worker;
- минимальный additive schema diff против legacy rows;
- будет ли provider summary сохраняться как отдельный опциональный artifact
  source; он не заменяет GRAF-owned summary без отдельного quality gate;
- политика восстановления старых failed meetings, если source revision или
  idempotency evidence уже утрачены.
