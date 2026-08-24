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
- automatic, manual-format и refresh результаты становятся current только после
  trusted publication; отдельный accept/reject UX не требуется;
- user acceptance сохраняет source, deletion, expected-current и idempotency fences;
- replay после provider ACK loss переиспользует durable validated response без второго inference;
- nine-format prompt contracts, personal default, rendering, candidate controls и browser/desktop parity проходят общий focused suite.

Предупреждения относятся к pytest assert-rewrite для уже импортированного fixture plugin и Starlette `httpx` deprecation; падений или Feature 181 regressions нет.

После финального Ponytail-упрощения повторно запущены затронутые generation/prompt/UI contract tests: `74 passed`, 2 тех же предупреждения, exit code 0. Затем повторный `ci-local --fast` подтвердил `1130 passed`, lint и compile pass.

## Latest rerun

Дата: 2026-08-24

После prompt corrections повторно выполнен текущий focused command без
вывода содержимого встреч: `91 passed`, 2 предупреждения, exit code 0;
isolated PostgreSQL container удалён wrapper-скриптом. `infra/scripts/ci-local.sh
--fast` на том же состоянии: `1232 passed`, server lint и Python compile pass,
exit code 0.

## Latest implementation rerun

Дата: 2026-08-25

После исправления GEPA metric-call accounting и добавления metadata-only
usefulness/pairwise receipt validator focused command расширен двумя
optimizer suites: `140 passed`, 2 предупреждения, exit code 0; isolated
PostgreSQL container удалён wrapper-скриптом. `infra/scripts/ci-local.sh --fast`:
`1234 passed`, server lint и Python compile pass, exit code 0.

## Latest current-worktree rerun

Дата: 2026-08-25

После merge-refresh и исправления trusted-publication regression полный focused
command Feature 181 завершился `104 passed`, 2 предупреждения, exit code 0;
изолированный PostgreSQL container удалён wrapper-скриптом. Затем
`infra/scripts/ci-local.sh --fast` на том же состоянии завершился `1274 passed`,
server lint pass, Python compile pass, exit code 0.

Добавлена metadata-only regression: опубликованный outcome в current default
slot отражается в content-safe processing projection как `available` или
`partial` только для той же processing/media revision и совместимого source
hash. Содержимое встречи в evidence не попадает.
