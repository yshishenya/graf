# Implementation Plan: Ускорение релизного конвейера

**Feature**: `298-release-pipeline-acceleration`

**Branch**: `298-release-pipeline-acceleration`

**Input**: `specs/298-release-pipeline-acceleration/spec.md`

## Summary

Изменить планирование тестовых ресурсов и подготовку CI так, чтобы
самодостаточные strict-доказательства исполнялись параллельно, а общие строгие
доказательства и настенные таймеры оставались последовательными. Добавить
дешёвые контрактные проверки на PR, сократить глубину checkout релизных job и
параллелить подпроцессные наборы. Набор тестов, точный SHA, доказательство
покрытия и авторитетный `release-full` не меняются.

## Technical Context

- Сервер: Python 3.13, pytest 9.1.1, pytest-xdist 3.8.0, PostgreSQL 17, Docker.
- CI: GitHub-hosted Ubuntu 24.04 и macOS 15.
- Плагин фаз: `apps/server/tests/fixtures/test_resources.py`.
- Раннер: `apps/server/scripts/run_local_postgres_tests.sh`.
- Полный прогон: `.github/workflows/release-full.yml`.
- Быстрый лейн: `infra/scripts/ci-local.sh` и `.github/workflows/governance-fast.yml`.

## Constitution Check

- Изоляция и точный SHA сохраняются.
- Доказательство покрытия шардов не ослабляется.
- Никаких секретов, приватных данных или продуктовых компромиссов.
- Изменение относится к инфраструктуре релиза и проходит полный релизный гейт.

## Design

### 1. Маршрутизация strict по замыканию фикстур

- `ISOLATED_CLUSTER_FIXTURE = postgres_isolated_cluster_database_url`.
- `SHARED_STRICT_FIXTURES = {migrated_postgres_urls, postgres_advisory_lock}`.
- `phase_for(item)`:
  - strict-маркер и изолированный кластер без общих фикстур и без
    `serial_performance` → `parallel`;
  - иначе strict-маркер → `strict`;
  - `serial_performance` → `performance`;
  - остальное → `parallel`.
- Изолированная фикстура добавлена в `POSTGRES_FIXTURES`, чтобы ресурсный
  маркер был корректным.
- Тесты мониторинга с настенными границами помечены `serial_performance`:
  они остаются в strict.

### 2. Бюджет готовности изолированного кластера

- Общий бюджет готовности 60 с на обе попытки старта.
- Каждый вызов docker не дольше `min(15, остаток бюджета)`.
- Очистка — отдельный лимит 30 с.
- При отказе сообщение содержит стадию; секреты не печатаются.

### 3. Ранние поведенческие доказательства

- `scripts/ci-behavior-tests.py`:
  - `openapi-contract` → `test_openapi_contract_drift.py` для `api/*`,
    `main.py`, файла контракта; требует postgres-раннер;
  - `copy-conventions` → `test_copy_convention_contract.py` для шаблонов и
    модулей презентации;
  - `account-routes` → `test_account_routes.py` для auth/cabinet-модулей и
    шаблонов.
- Обязательные имена тестов проверяются по AST и JUnit, как у существующих групп.

### 4. Checkout и параллельные наборы

- `release-full`: reserve/phases/shard/macos — `fetch-depth: 1`; static — `2`
  ради fallback `HEAD^` в проверке процесса.
- Governance и контракты раннера — `-n 4`; `pytest-xdist==3.8.0` закреплён в
  toolchain обоих workflow.
- В локальной среде без xdist governance идёт последовательно с сообщением.

## Files

- `apps/server/tests/fixtures/test_resources.py`
- `apps/server/tests/fixtures/postgres_test_database.py`
- `apps/server/tests/integration/test_billing_monitoring_postgres.py`
- `apps/server/tests/contract/test_isolated_postgres_cluster.py`
- `apps/server/tests/contract/test_ci_cd_contract.py`
- `apps/server/pyproject.toml`
- `scripts/ci-behavior-tests.py`
- `infra/scripts/ci-local.sh`
- `.github/workflows/governance-fast.yml`
- `.github/workflows/release-full.yml`
- `docs/agent-guidance/release-and-validation.md`
- `tests/governance/test_test_resources.py`
- `changes/unreleased/F298.yaml`

## Validation Strategy

1. Focused: контракты изолированного кластера, тесты выбора доказательств,
   governance-предохранитель.
2. Инвентарь фаз: объединение равно baseline, strict содержит только общие и
   настенные доказательства.
3. CI-контракты: полный набор с `-n 4`, без новых skip.
4. Workflow: `validate-full-ci-workflow.py` и контракты релизного workflow.
5. GitHub: `governance-fast`, `macos-pr`, `pr-metadata` на точном SHA PR.
6. Релиз: один `release-full` на замороженном кандидате; сравнить длительности
   и доказательство покрытия.

## Risks and Rollback

- Риск: неизвестная общая фикстура в переносимой группе. Мера: консервативное
  замыкание, явный список общих фикстур, предохранитель в governance.
- Риск: настенные проверки под нагрузкой. Мера: `serial_performance` для
  известных случаев; при появлении новых — тот же маркер.
- Риск: checkout без истории ломает проверку процесса. Мера: depth 2 для static
  и существующий fallback `HEAD^`.
- Откат: вернуть прежнюю маршрутизацию и глубину checkout; тесты не меняются.

## Deferred

- Балансировка шардов по длительности — по данным нового прогона.
- Частичный повтор упавших job — отдельный дизайн per-slot receipts.
- Шаблонная база в контейнере — после повторного профилирования.
