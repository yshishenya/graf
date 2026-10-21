# Quickstart: Feature 227

## Preflight

```sh
python3 scripts/validate-agent-context.py
python3 scripts/check-development-process.py
python3 scripts/check_spec_kit_governance.py
```

## Local contract checks

```sh
PYTHONDONTWRITEBYTECODE=1 pytest -q tests/governance/test_ci_evidence_producer.py \
  tests/governance/test_ci_guard.py \
  tests/governance/test_governance_workflow.py \
  tests/governance/test_release_candidate.py
python3 scripts/validate-governance-workflow.py --self-test
```

## Event fixtures

Validate synthetic PR, manual and `merge_group` payloads. A merge-group fixture
must prove synthetic SHA, base SHA and PR mapping. Changed SHA or final tree
drift must produce a terminal non-success receipt.

## Действующий serial сценарий и регрессия происхождения

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q \
  tests/governance/test_release_train.py \
  tests/governance/test_release_candidate.py \
  tests/governance/test_merge_group_mapping.py \
  tests/governance/test_ci_event_identity.py \
  tests/governance/test_governance_workflow.py
python3 scripts/validate-release-train.py --self-test
```

`test_release_train.py` создаёт временный Git repo и вызывает настоящий
release-candidate с отдельным synthetic commit, как serial release operator.
PR checks и Full CI в fixture подставлены: это проверка контрактов, не GitHub
приёмка. Serial train сохраняет три PR и пустые merge-group collections.
Несвязанная с source база должна отклоняться даже при связи с synthetic,
без manifest/identity на диске. Временные repo создаются pytest отдельно от рабочих копий.

## PR и release gates

Локальный `ci-local.sh --fast` — диагностический путь. Для PR обязательны
`governance-fast`, `macos-pr`, `pr-metadata` на точном SHA и текущей основе:

```sh
python3 scripts/validate-pr-checks.py --repository yshishenya/graf --pr <номер>
```

Выпуск в этот срез не входит. Действующий operator `scripts/release.sh` собирает
реальные PR proofs, создаёт synthetic commit и замораживает train/candidate на
фактическом source. Один authoritative GitHub `release-full` запускается только
для одобренного frozen candidate по действующей инструкции выпуска. Локальный
`--full` не заменяет этот gate. Не запускать выпуск для проверки данного среза.

Native `merge_group` rehearsal и authoritative API mapping T029/T031 остаются
отдельными открытыми условиями перед будущим включением очереди. Синтетические
fixtures и serial train их не выполняют. Защита GitHub не меняется.

## Pinned harness

Матрица Python 3.9/3.12 из закреплённого SHA и successful run описаны в
[research.md](research.md#r8--закреплённая-матрица-переносимого-инструментария).
Не обновлять pin и не считать исторический run текущей проверкой продукта.

## Повторная защита потребителей — 21.10.2026

Тот же test_release_train.py параметризует полноценный serial freeze → candidate
→ Full fixture → attest → decide. Для legacy-unrelated записываются прежний
manifest и согласованная immutable identity. Для replace-graft обычный
merge-base принимает подменённую связь, raw --no-replace-objects её отвергает.
Все четыре потребителя и новый freeze при graft должны отказать по ancestry;
все исходные документы/identity побайтово сохранены, новых candidate/go/decision
записей нет. Стабильный файл decision.lock может быть создан существующим
decide до проверки train; он не является decision/identity. Положительная
матрица отдельно проходит без подмен. Production и настоящего Full здесь нет.
