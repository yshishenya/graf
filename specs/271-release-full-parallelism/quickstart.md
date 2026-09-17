# Quickstart: Полное использование параллелизма в релизном прогоне

## Предварительные условия

- Публичный репозиторий `yshishenya/graf`, права на запуск workflow.
- Локально: `uv`, Docker, PostgreSQL-контейнер поднимает сам скрипт набора.
- `gh` авторизован.

## Сценарий 1. Значение потоков в релизной задаче (FR-001, FR-003)

```sh
grep -n "GRAF_TEST_WORKERS" .github/workflows/release-full.yml
```

Ожидается `GRAF_TEST_WORKERS=8` в задаче Ubuntu.

```sh
grep -n "workers > " apps/server/scripts/run_local_postgres_tests.sh
```

Ожидается граница 8: значение внутри диапазона 1–8.

## Сценарий 2. Контрактные проверки

```sh
python3 scripts/validate-full-ci-workflow.py .github/workflows/release-full.yml
```

Ожидается `full-ci-workflow: OK`.

```sh
GRAF_TEST_WORKERS=2 bash apps/server/scripts/run_local_postgres_tests.sh \
  --focused tests/contract/test_ci_cd_contract.py -q
```

Ожидается `postgres_test_result=pass`, включая проверку диапазона потоков.

## Сценарий 3. Статические проверки идут один раз (FR-002)

```sh
python3 scripts/validate-full-ci-workflow.py .github/workflows/release-full.yml
```

Валидатор требует, чтобы `ruff check` и `compileall` выполнялись ровно один
раз и до тестов. Изменение числа потоков этого не затрагивает.

## Сценарий 4. Локальный замер на том же наборе (SC-002)

```sh
GRAF_TEST_REPORT_DIR=/tmp/graf-w4 GRAF_TEST_WORKERS=4 \
  bash apps/server/scripts/run_local_postgres_tests.sh --full -q
GRAF_TEST_REPORT_DIR=/tmp/graf-w8 GRAF_TEST_WORKERS=8 \
  bash apps/server/scripts/run_local_postgres_tests.sh --full -q
```

Сравнить `postgres_test_phase=parallel ... duration_seconds` в обоих выводах.

## Сценарий 5. Прогон релиза на новом дереве (FR-004, SC-002)

```sh
git fetch origin master
SHA=$(git rev-parse origin/master)
gh workflow run release-full.yml --ref master \
  -f candidate_id="rc-$(date -u +%Y%m%dT%H%M%SZ)" -f requested_sha="$SHA"
```

Затем записать длительности задач:

```sh
gh run view <run-id> --json jobs \
  --jq '.jobs[]|"\(.name) \(.startedAt) -> \(.completedAt)"'
```

Сравнить с прогоном `35183409199` (26 мин 55 с).

## Сценарий 6. Состав проверок не изменился (SC-003)

```sh
gh run download <run-id> -n "$(gh api repos/yshishenya/graf/actions/runs/<run-id>/artifacts \
  --jq '.artifacts[]|select(.name|startswith("graf-test-timings"))|.name')" -D /tmp/ci-after
python3 -c "
import json,pathlib
rows=[json.loads(l) for l in (pathlib.Path('/tmp/ci-after')/'parallel.jsonl').read_text().splitlines() if l.strip()]
print('случаев', len(rows), 'сумма', sum(r.get('duration') or 0 for r in rows))
"
```

Число случаев и итог набора должны совпасть с прогоном `35183409199`
(13431 случай, 4852 с).

## Откат

```sh
sed -i '' 's/GRAF_TEST_WORKERS=8/GRAF_TEST_WORKERS=4/' .github/workflows/release-full.yml
```

Один коммит, состав проверок не меняется.
