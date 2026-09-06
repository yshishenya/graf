## Feature identity

- Feature ID: `F___`
- Umbrella issue: `#___`
- Spec task IDs: `T___`

## Как проверено

- Exact source SHA и observed SHA:
- CI evidence:
- Обязательный PR gate: GitHub `governance-fast` на exact SHA —
  PASS/FAIL/BLOCKED, ссылка на run:
- Локальный `infra/scripts/ci-local.sh --fast` — только ручная диагностика или
  offline fallback; локальное evidence не заменяет GitHub check.

## Risk / validation lane

- Lane:
- Почему выбран этот lane:
- Stale-SHA / cancellation state:

## Issues

- `Refs #___` или `Part of #___` для частичной связи;
  `Fixes #___` только при полном закрытии issue.

## Legacy Impact

- Classification: `remove` / `retain-with-exception` / `untouched`
- Removed or preserved paths:
- Exception owner/expiry/removal trigger/retirement task (если применимо):

## Перед merge

- [ ] Feature ID, task IDs, issue links и exact SHA согласованы.
- [ ] Validation evidence записан.
- [ ] Legacy Impact заполнен.
