# Research: Feature 225

## Исторические факты — 2026-08-31

- `scripts/claim-feature.py --json` предложил завышенный номер.
- Единственный источник этого числа — ref
  `codex/turn-diffs/captures/synthetic-session/99999999-synthetic/base`.
- Product branch/spec/issue IDs находятся в диапазоне до Feature 224.
- Online `gh api` без timeout может зависнуть; при ошибке текущий suggestion ошибочно продолжал работу с пустым GitHub set.

## Решения

1. Игнорировать только известный служебный namespace
   `codex/turn-diffs/captures/`.
2. Сохранить текущую regex-модель для обычных refs `<number>-<slug>`.
3. Добавить regression test с high numeric service ref и normal product ref.
4. Ограничить GitHub subprocess bounded timeout, валидировать paginated response и использовать strict fail-closed для online suggestion.

## Rejected alternatives

- Игнорировать все большие номера: может скрыть реальную feature.
- Использовать только максимальный номер GitHub: не учитывает local/remote refs
  и создаёт race.
- Удалить служебный ref: это внешнее destructive действие и не нужно для
  исправления allocator.
- Показывать `github-checked` после ошибки API: это создаёт ложное доказательство свежести.
