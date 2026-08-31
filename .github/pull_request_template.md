## Кратко

-

## Feature identity

- Feature ID: `F___`
- Umbrella issue: `#___`
- Spec task IDs: `T___`
- Branch/spec directory match:

## Что изменилось

-

## Как проверено

- Focused-проверки:
- `infra/scripts/ci-local.sh --fast`: requested/effective lane, components,
  coverage, next gate, result, duration:
- `infra/scripts/ci-local.sh --full`: exact SHA, result, duration, collection
  count/digest (только для frozen release candidate):
- `infra/scripts/cd-remote.sh --dry-run`: result / not applicable:
- Exact source SHA и observed SHA в evidence:

## Risk / validation lane

- Lane:
- Что запускалось:
- Более широкие gate не запускались, потому что:
- Release/deploy gate:
- Performance gate: report-only / required / not applicable; почему:
- Stale-SHA / cancellation state:

## Issues

Используй `Fixes #...`, `Closes #...` или `Resolves #...` только для issues,
которые этот PR закрывает полностью. Для частичной работы используй `Refs #...`
или `Part of #...`.

-

## Что не входит

-

## Legacy Impact

- Classification: `remove` / `retain-with-exception` / `untouched`
- Removed or preserved paths:
- Exception owner/expiry/removal trigger/retirement task (если применимо):
- Нового legacy alias/fallback/flag/dependency/fixture/test/docs path не добавлено:

## Release / versioning

- [ ] Если PR готовит релиз, выбран правильный тип версии:
      CalVer `vYYYY.MM.DD.N` для продукта/apps/services или SemVer
      `vMAJOR.MINOR.PATCH` для libraries/CLI/extensions/bootstrap.
- [ ] Читаемый postfix релиза записан в GitHub Release title, а не в stable tag.
- [ ] `changes/unreleased/F<feature-id>.yaml` добавлен и проверен; root
      `CHANGELOG.md` меняет только release operator при freeze candidate.
- [ ] Release notes включают validation evidence, compatibility/migration notes
      и known limitations.

## Перед merge

- [ ] Описание PR написано на русском и понятно не только инженеру.
- [ ] Все полностью закрываемые issues перечислены через closing keywords.
- [ ] Частичные или связанные issues перечислены через `Refs` / `Part of`.
- [ ] Risk / validation lane выбран и обоснован.
- [ ] Validation evidence записан в PR.
- [ ] Feature ID, umbrella issue, task IDs и exact SHA согласованы.
- [ ] Legacy Impact заполнен; `legacy_new=0`, `unowned_legacy=0`,
      `expired_exceptions=0`.
- [ ] Для каждого закрываемого issue после проверки будет добавлен подробный
      русский closure comment.
