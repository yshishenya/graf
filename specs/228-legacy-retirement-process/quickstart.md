# Quickstart: Feature 228 legacy retirement process

> **Пересмотр объёма 26.10.2026:** действующий объём и индивидуальные решения
> заданы в [решении для ранней стадии](scope-decision-20261026.md).
> До его слияния это предложение. После слияния перечисленные там задачи
> отменены как NOT_PLANNED, сохраняют `[ ]` и не подлежат реализации по старому
> плану. Принятые защиты и предметные требования безопасности сохраняются.


Этот quickstart проверяет только контракты планирования и metadata-only
evidence. Он не удаляет runtime legacy, не меняет production, БД, volumes,
Temporal history, TCC или signing trust.

## 1. Проверить активный контекст

```sh
.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
python3 scripts/validate-agent-context.py
python3 scripts/check-development-process.py --self-test
```

Ожидается: active feature указывает на `specs/228-legacy-retirement-process`,
branch и SHA совпадают с текущим worktree, а root `AGENTS.md` остаётся только
маршрутизатором.

## 2. Проверить planning artifacts

```sh
python3 scripts/check_spec_kit_governance.py
git diff --check
```

Ожидается: `spec.md`, `clarifications.md`, `plan.md`, `data-model.md`,
`contracts/`, `quickstart.md` и `tasks.md` существуют. До реализации отдельный
независимый reviewer-агент проверяет каждый пункт обоих чеклистов, отмечает
только подтверждённое и оставляет остальное открытым с причиной. Он меняет
только чеклисты и отдельный отчёт, перечитывает их и записывает итоги.
Агент реализации отметки не меняет; неподтверждённое ревью и открытые
блокирующие замечания останавливают реализацию.

## 3. Проверить безопасный registry fixture

После реализации T008–T014 запустить:

```sh
python3 scripts/legacy-inventory.py --source-sha "$(git rev-parse HEAD)" --metadata-only
python3 scripts/validate-legacy-registry.py governance/legacy/registry.v1.yaml
```

Два запуска на одном exact SHA должны дать одинаковый ordering и digest. В
выводе не должно быть секретов, private paths, raw audio, transcript или
content-bearing database data. `candidate` и `blocked` не являются разрешением
на удаление.

## 4. Проверить no-new-legacy и retirement slice

После реализации T016–T025 запустить focused governance tests:

```sh
PYTHONDONTWRITEBYTECODE=1 pytest -q \
  tests/governance/test_legacy_inventory.py \
  tests/governance/test_legacy_registry.py \
  tests/governance/test_retirement_slice.py
```

Ожидается: incomplete/expired exception, unowned compatibility path,
missing rollback и missing protected-domain evidence блокируются; valid finite
exception проходит.

## 5. Перед PR

```sh
python3 scripts/check-development-process.py --self-test
PYTHONDONTWRITEBYTECODE=1 pytest -q tests/governance
```

В PR записываются risk lane `significant-feature`, exact source SHA, feature
ID/umbrella issue/task IDs, `Legacy Impact: untouched`, `legacy_new=0`,
`unowned_legacy=0`, `expired_exceptions=0` и открытые reviewer/convergence
gates. Коммит выполняется после проверки.
После PR обязательны GitHub `governance-fast`, `macos-pr`, `pr-metadata`
точного SHA и проверенной основы, затем:

```sh
python3 scripts/validate-pr-checks.py --repository yshishenya/graf --pr <номер>
```

Локальный `infra/scripts/ci-local.sh --fast` остаётся только диагностикой или
резервной проверкой. Он не заменяет GitHub и не добавляется вторым обязательным
этапом. Full CI выполняется только на замороженном будущем release candidate.

## Самостоятельный T009/T019

После нового независимого ревью, анализа и сверки трекера выполнить:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q tests/governance/test_validator_safety.py
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q tests/governance/test_pr_metadata_event.py
python3 scripts/validate-pr-metadata.py --self-test
python3 scripts/check-development-process.py --self-test
python3 scripts/check_spec_kit_governance.py
git diff --check
```

Отсутствующие registry/inventory/slice команды выше остаются проверками будущих
задач и не объявляются выполненными. Для T009/T019 нужны отрицательные случаи
восьми обязательных полей, границы даты UTC, связей F###/T###/#issue и проверка
одинакового решения спецификации/PR. Шаблон PR объясняет поля; `remove` и
`untouched` сохраняют прежнее поведение. После PR — три обязательные проверки,
общий валидатор и live-проверка закрытия только #6247/#6257.

## Приёмка пересмотра T037

Исторические команды реестра и сканера выше после принятия решения не нужны.
Для документального пересмотра выполнить:

```sh
python3 scripts/validate-agent-context.py
python3 scripts/check-development-process.py --self-test
python3 scripts/check-development-process.py
python3 scripts/check_spec_kit_governance.py
python3 scripts/validate-legacy-impact.py --feature specs/228-legacy-retirement-process/spec.md
python3 scripts/validate-pr-metadata.py --self-test
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider tests/governance/test_validator_safety.py tests/governance/test_pr_metadata_event.py
git diff --check
```

Отдельно сравнить все исходные 36 строк tasks.md с основой: ни описание, ни
владелец, ни отметка не меняются; новая T037 относится только к документации.
После PR нужны три обычные проверки exact SHA/base и общий валидатор.
После слияния применяется процедура NOT_PLANNED из tracker-policy с
повторным чтением каждого issue; отсутствующая реализация не превращается в PASS.
