# Quickstart: Feature 225

## Проверка allocator

```sh
python3 scripts/claim-feature.py --self-test
python3 scripts/claim-feature.py --json
```

Ожидается, что internal Codex refs не влияют на `next_available`, а реальные
feature branches/specs/issues продолжают учитываться. Если GitHub API недоступен
или отвечает неверной структурой, online-команда завершается ошибкой; она не
выдаёт неполное значение как `github-checked`. Для strict claim нужен открытый
umbrella issue и чистый worktree; `--offline` только draft.

## Governance validation

```sh
python3 scripts/check_spec_kit_governance.py
python3 scripts/check-development-process.py
# Для PR: GitHub governance-fast на точном SHA; локальный --fast только диагностика.
```

Не записывать service refs, machine paths, secrets или private data в evidence.

Номер вручную не угадывать. Начинать новую фичу от проверенного актуального master, получать предложение через общий allocator и повторять его проверку при резервировании. Старый `spec_next` не подтверждает занятость. Политика F259 исключает историческую F6788 только из начала последовательности, но сохраняет её занятость.
