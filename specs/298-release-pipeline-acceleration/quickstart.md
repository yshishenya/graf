# Quickstart: проверка ускорения релизного конвейера

**Feature**: `298-release-pipeline-acceleration`

Все команды выполняются из корня репозитория в этой рабочей копии.

## 1. Инвентарь фаз

```sh
cd apps/server
PYTHONPATH=src .venv/bin/python -m pytest --collect-only -q \
  -p no:cacheprovider -p tests.fixtures.test_resources \
  --graf-collection-file /tmp/phases.json tests >/dev/null
python3 - <<'PY'
import json
v = json.load(open('/tmp/phases.json'))
print({k: len(x) for k, x in v.items()})
print(len(set(v['parallel'] + v['performance'] + v['strict'])) == len(v['baseline']))
PY
```

Ожидается: объединение фаз равно `baseline`; в `strict` нет тестов с
изолированным кластером без общей базы и без `serial_performance`.

## 2. Контракты изолированного кластера и выбора доказательств

```sh
cd apps/server
PYTHONPATH=src .venv/bin/python -m pytest -q \
  tests/contract/test_isolated_postgres_cluster.py
PYTHONPATH=src .venv/bin/python -m pytest -q \
  tests/contract/test_ci_cd_contract.py -k "openapi or copy_and_account or release_full"
cd ../..
apps/server/.venv/bin/python -m pytest -q tests/governance/test_test_resources.py
```

## 3. Ранняя проверка контракта через настоящий раннер

```sh
cd apps/server
bash scripts/run_local_postgres_tests.sh --focused -q \
  tests/contract/test_openapi_contract_drift.py
```

Ожидается `postgres_test_result=pass`; при расхождении контракта — падение до
дорогих фаз релиза.

## 4. Параллельные наборы

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q -n 4 -p no:cacheprovider \
  tests/contract/test_ci_cd_contract.py \
  tests/contract/test_local_postgres_test_runner.py
```

## 5. Workflow и документация

```sh
python3 scripts/validate-full-ci-workflow.py .github/workflows/release-full.yml
python3 scripts/check-development-process.py
git diff --check
```

## 6. GitHub и релиз

1. Открыть PR из `298-release-pipeline-acceleration` в `master` с точным SHA.
2. Дождаться `governance-fast`, `macos-pr`, `pr-metadata`.
3. После слияния запустить один `release-full` на замороженном кандидате и
   сравнить длительности job и доказательство покрытия шардов.
4. Закрыть T008 и umbrella issue #8161 только после приёмки.

## Что считается провалом

- Объединение фаз не равно полному сбору или содержит повторы.
- В strict попал тест с общей строгой базой или настенными таймерами.
- Появились новые skip, падения или таймауты.
- Доказательство покрытия шардов неполное.
- `release-full` не сократил критический путь.
