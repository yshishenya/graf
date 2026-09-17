# Проверка F239

## До реализации

Ветка `codex/239-simple-meeting-minutes`, локальная `.specify/feature.json`
указывает F239. Reviewer checklist проверяется заново, не копируется из #6787.
Analyze: нет открытых CRITICAL/HIGH. Tasks связаны с недублирующими issues.

## Целевые проверки

Из `apps/server`: `uv run --extra dev pytest` с конкретными unit/contract
файлами протокола. Integration — `scripts/run_local_postgres_tests.sh`
с точным списком изменённых тестов. Не запускать полный локальный CI.
Фактические команды/результаты записать в `validation.md` после исполнения.

Созданные проверки; команды из apps/server:

```sh
uv run --extra dev pytest tests/unit/test_meeting_protocol.py tests/unit/test_meeting_protocol_rendering.py -q
scripts/run_local_postgres_tests.sh tests/integration/test_meeting_protocol_generation.py -q
```

Для живой проверки нужны отдельные PostgreSQL DB, MinIO bucket, Temporal
namespace/task queue и dev prompt label, а также локальная авторизованная
сессия владельца и CSRF. Нельзя подключать исполняющие worker/server к
production DB/очереди. Действующие TWOBRAIN_* настройки загружаются из
приватного окружения, не печатаются и не записываются в репозиторий.
`TWOBRAIN_OUTCOME_PROMPT_LABEL=dev`; общий порт 18081 выбирается только если
свободен. В отдельных терминалах из apps/server с одним dev окружением:

```sh
uv run alembic upgrade head
uv run uvicorn twobrain_rec_server.main:create_app --factory --host 127.0.0.1 --port 18081
uv run python -m twobrain_rec_server.workflows.worker
```

Через авторизованный GRAF интерфейс отправить
`POST /api/v1/cabinet/meetings/{meeting_id}/summary-candidates` с
`template_key` существующего профиля, его `template_version` и
`request_intent: "manual_format"` (без request_intent_id). Для повторного
обновления — `request_intent: "manual_refresh"`, уникальный request_intent_id
и expected_current_outcome_set_id текущей ревизии. Ожидается HTTP 202,
затем опубликованное состояние accepted. Состояние читать
`GET /api/v1/cabinet/meetings/{meeting_id}/summary-candidates/{candidate_id}`.
Не вызывать gateway напрямую вместо HTTP/Temporal проверки.

Проверить: исходный prompt, schema/config, неизменность слов, точные refs,
dev/production pinning, один вызов/повтор без inference, expiry/cancel/
deletion/source/access race, HTML/MD/JSON/XLSX, исторические документы,
независимую доставку наблюдений и неизменные retries.

## Реальная генерация

Изолированные GRAF server/worker с существующими разрешёнными LiteLLM/Langfuse.
Production-источники читать существующим read-only мостом, не менять записи.
Сделать inventory, выбрать три разные осмысленные встречи, одна ≥3600 секунд.
Остальные явно «не проверено». Запускать обычным HTTP-путём через Temporal,
дождаться публикации, открыть UI, таймкоды, выгрузки. Проверяющий сам читает
весь протокол и весь источник: темы, факты/числа, решения, задачи/владельцы/
сроки, поправки, возражения, альтернативы, ограничения, зависимости, связность.
Семь controls SC-002; на синтетическом источнике — вторая доступная модель,
выбранная только в Langfuse. Записать время и результат каждой попытки.

Общую ошибку исправлять в общем тракте, затем повторять затронутые проверки.
Старый результат не объявлять проверкой нового кода/промпта. Приватные тексты
только в разрешённом контуре; git/PR — агрегаты без ключей, контента, signed
URLs и реальных идентификаторов встреч/пользователей.

## PR

Converge, проверка сложности/diff, `git diff --check`, целевые тесты,
changelog F239, совместимый Alembic head, отсутствие конфликтов с master.
После подтверждения коммита — push, GitHub `governance-fast` на точном SHA,
`validate-pr-metadata.py --expected-sha <SHA>`. Не merge, не production labels,
не deploy. Full CI релизного кандидата — отдельному релизному оператору.

## Предпосылки отдельного релиза

1. Применить `0088_meeting_protocol` после `0087_merge_calendar_timezone`.
   Миграция сохраняет историю, добавляет nullable protocol_json и расширяет
   owner/due до Text. Не запускать старые миграции/код ветки #6787.
2. Установить для GRAF API/worker
   `TWOBRAIN_LITELLM_REQUEST_TIMEOUT_SECONDS=240`. Измеренный длинный вызов
   занял 200.5 секунды; прежние 120 секунд недостаточны. Существующие 5 минут
   Temporal activity, retries, LiteLLM и Nginx не изменяются. Новое значение
   пока проверено только в изолированной среде, production не настроен.
3. В отдельном разрешённом релизе перенести проверенные версии из
   `release-prompts.md` на production-метки с чтением точной версии/hash.
   Подготовлены все 9 встроенных профилей и custom. Модель/параметры — Langfuse,
   не переменная GRAF. Существующие production v5 не совместимы с новым
   полным контрактом: нельзя выкатывать новый worker без согласованной
   смены промптов. На время перехода остановить выдачу новых попыток,
   закончить текущие, обновить сервер/worker и метки, затем возобновить.
4. Проверить после релиза обычную генерацию, повторное открытие, таймкод и
   выгрузку. Удалённый локальный генератор не является запасным вариантом.
   Jailbreak сохранять включённым; его отказ не обходить.

На отдельном стенде, созданном копированием источников без ingest, запустить
существующую `reconcile_missing_summary_defaults` в его собственной БД или
использовать обычный ingest. Иначе даже принятый документ без default marker
не выбран обычной страницей. Это подготовка стенда, не новый продуктовый шаг.
