# Предварительный технический выпуск T058

Lane: high-risk, часть уже согласованной Feature 239. Refs #6642,
#6630–#6634. Этот выпуск не закрывает основную фичу и приёмку корпуса.

## Граница

- Сохраняется действующий плоский outcome schema, текст промптов и renderer
  из master. Новый protocol pipeline, verifier, миграция и UI сюда не входят.
- Единственный исполняемый config — v5. Модель и присутствующие параметры
  берутся из точной версии Langfuse; шаблоны кода содержат только schema.
- Технический root — `graf-outcome-root-bundle-v2`, export — v2. Он сохраняет
  точные версии/хеши children, но не содержит дополнительного ограничения
  модели. Root v3 с runtime hash относится к последующему выпуску протоколов.
- Исторические roots, calls и observations не переписываются. Старые calls
  допускаются к доставке observations по исходным хешам, но не к новому
  исполнению/публикации через старый config.

## Проверки до PR

```sh
cd apps/server
uv run --extra dev --extra evaluation pytest -q \
  tests/unit/test_outcome_prompts.py tests/unit/test_prompt_bundle.py \
  tests/unit/test_prompt_optimization.py tests/unit/test_gepa_prompt_optimizer.py \
  tests/unit/test_litellm_gateway.py tests/unit/test_langfuse_observability.py \
  tests/contract/test_langfuse_runtime_contract.py
```

Из корня репозитория:

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused \
  tests/unit/test_summary_candidate_revisions.py \
  tests/unit/test_trusted_outcome_publication_boundary.py \
  tests/integration/test_outcome_generation_dispatch.py \
  tests/integration/test_recording_workflow_deletion_races.py \
  tests/integration/test_outcome_generation_workflow.py \
  tests/integration/test_meeting_outcomes_generation.py \
  tests/integration/test_meeting_outcomes_deletion.py -q
```

Обязательны independent review, проверка отсутствия старого механизма в
runtime/tests/infra и `governance-fast` на точном SHA PR. Общие задачи
протоколов остаются открытыми; partial PR использует только `Refs`.

Для этого среза синтетические настройки и закрепление тестовой попытки
находятся в `apps/server/tests/fixtures/outcome_prompts.py`. Упомянутый в T054
`meeting_protocol.py` относится к последующему выпуску нового протокола.
Changelog использует текущий формат `changes/unreleased/F239.yaml`.

## Согласованная активация

После merge, release-full и CD dry-run на зафиксированном кандидате:

1. Подготовить новые unlabelled Langfuse configs из exact source versions;
   сохранить фактические модельные параметры, получить новые необходимые
   подтверждения качества, root и export. Прежние подтверждения не копировать.
2. Приостановить новые AI-запуски, generation/optimizer/evaluator dispatch;
   завершить либо явно закрыть текущие попытки. Не повторять ambiguous calls.
3. Проверить отсутствие второго model lock в ACL ключа ГРАФ. Не менять
   обычные права, ключи, бюджеты, частоту запросов и провайдерские маршруты.
4. Согласованно переключить GRAF/root/LKG и удалить в LiteLLM только callback,
   его регистрацию, mount и четыре специфичные для него переменные окружения.
5. Проверить синтетические вызовы нескольких моделей тем же ключом, exact
   request/config, nullable reported provenance и сохранность observations.
   Только после успешной проверки возобновить AI.
6. Завершить обычные release gates и сохранить metadata-only evidence.

Односторонняя активация несовместима со старым GRAF/hook и запрещена.
Операционный откат возможен только согласованным восстановлением прежних
образов и конфигурации; совместимая legacy-ветвь в новом коде не добавляется.
