# Quickstart: Feature 228 legacy retirement process

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
`contracts/`, `quickstart.md` и `tasks.md` существуют; все reviewer-owned
checklist items остаются unchecked.

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
infra/scripts/ci-local.sh --fast
```

В PR записываются risk lane `significant-feature`, exact source SHA, feature
ID/umbrella issue/task IDs, `Legacy Impact: untouched`, `legacy_new=0`,
`unowned_legacy=0`, `expired_exceptions=0` и открытые reviewer/convergence
gates. Full CI выполняется только на замороженном будущем release candidate.
