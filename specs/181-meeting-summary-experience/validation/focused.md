# Focused validation

Дата: 2026-08-21

Команда:

```sh
bash apps/server/scripts/run_local_postgres_tests.sh \
  tests/integration/test_meeting_outcomes_generation.py \
  tests/integration/test_outcome_generation_dispatch.py \
  tests/unit/test_outcome_prompts.py \
  tests/contract/test_summary_template_ui_contract.py \
  tests/integration/test_cabinet_meeting_outcomes.py -q
```

Результат: `100 passed`, 2 предупреждения, exit code 0; isolated PostgreSQL container удалён wrapper-скриптом. Время pytest: 113.73 s, полный focused wrapper: 119 s.

Проверено:

- deterministic extraction не становится готовыми или принятыми итогами новой revision-scoped встречи;
- automatic, manual-format и refresh результаты остаются candidates до явного принятия;
- user acceptance сохраняет source, deletion, expected-current и idempotency fences;
- replay после provider ACK loss переиспользует durable validated response без второго inference;
- nine-format prompt contracts, personal default, rendering, candidate controls и browser/desktop parity проходят общий focused suite.

Предупреждения относятся к pytest assert-rewrite для уже импортированного fixture plugin и Starlette `httpx` deprecation; падений или Feature 181 regressions нет.

После финального Ponytail-упрощения повторно запущены затронутые generation/prompt/UI contract tests: `74 passed`, 2 тех же предупреждения, exit code 0. Затем повторный `ci-local --fast` подтвердил `1130 passed`, lint и compile pass.
