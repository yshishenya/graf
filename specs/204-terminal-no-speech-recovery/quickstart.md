# Quickstart Acceptance: Feature 204

## Focused scenarios

1. Создать synthetic finalized meeting и импортировать result с
   `no_recognizable_speech`; проверить `manual_action=new_attempt`.
2. Вызвать admission; проверить `attempt_ordinal + 1`, новый workflow id и
   отсутствие мутации старого result/job.
3. Получить status до provider completion; проверить active state,
   `attempt_in_flight=true`, старый result не переводит projection в terminal.
4. Повторить admission во время active workflow; проверить
   `already_in_flight`/единственный active workflow.
5. Проверить quota/source/deletion/Temporal dispatch failure fences.

## Commands

```sh
pytest -q apps/server/tests/integration/test_processing_failures.py \
  apps/server/tests/contract/test_processing_status_contract.py
git diff --check
infra/scripts/ci-local.sh --fast
infra/scripts/ci-local.sh --full
```

## Production evidence

После exact-SHA deploy использовать существующую no-speech запись. Сохранять
только meeting UUID suffix, workflow/attempt ordinals, provider job count,
status codes, timestamps и health/smoke results. Не сохранять контент,
provider JSON, audio, title или credentials.

### Выполненная production-проверка

- Release `v2026.08.25.12` опубликован и выкачен в production; после следующего
  release train финальный runtime оказался на свежем `master` SHA
  `320a273e41e78c9d5a3c1ac1c3b760c23b1c63a2`, который содержит этот фикс.
- На финальном runtime `/api/v1/health/live` и `/api/v1/health/ready` вернули
  `200`; Temporal cluster health, processing worker readiness и MediaScribe
  `/health` прошли. Все production-сервисы Compose были healthy.
- Для записи с UUID-суффиксом `e9ae` попытка `4` завершилась со статусом
  `processed`; provider job — `ready`, provider attempt `1/3`, job count `1`,
  result count `1`, result status `imported`. Старые попытки не изменились.
- У этой записи причина результата — `no_recognizable_speech`; поэтому
  `transcript_status=unavailable`, `diarization_status=unavailable`,
  `summary_status=not_requested`, а сегменты не публикуются. Это ожидаемый
  no-speech результат, а не зависший recovery.
- В production также есть импортированные результаты с доступными transcript и
  diarization: агрегатная проверка показала 37 результатов в состоянии
  `transcript_status=available` и `diarization_status=available`. Для текущего
  production-контура summary не запрашивается (`TWOBRAIN_MEDIASCRIBE_SUMMARIZE`
  выключен), поэтому summary-flow этим smoke не подтверждается.

## Выполненное локальное evidence

- Feature 204 focused PostgreSQL matrix: `19 passed`.
- Expanded MediaScribe/Temporal/recovery matrix: `104 passed`.
- Production-found lazy Temporal recovery regression: focused matrix `26
  passed`, including no-speech new-attempt API dispatch without a preloaded
  `app.state.temporal_client`.
- Production-found durable-wait regression: focused PostgreSQL recovery matrix
  `3 passed`, включая повторное использование существующего provider job после
  `WAITING_RETRY` без нового submit.
- `git diff --check` и touched-file Ruff: pass.
- `infra/scripts/ci-local.sh --fast`: `1229 passed`, lint/compile/macOS guard pass.
- `infra/scripts/ci-local.sh --full` на exact release tree: macOS `766 passed`,
  server `3439 passed, 1 skipped`, strict RLS `52 passed, 1 skipped`,
  lint/compile, compose validation и evidence scan pass.
- Production execute повторил обязательный full gate на pinned master SHA перед
  remote backup, migration, deploy и smoke.
- RLS hardening sub-step внутри локального runner сообщил `blocked`, потому что
  production probe не выполняется против disposable PostgreSQL; это не является
  доказательством production RLS и требует отдельного production evidence.

## Production evidence

Feature 204 закрыта после exact-SHA release gate, production deployment и
metadata-only smoke на существующей no-speech записи.
