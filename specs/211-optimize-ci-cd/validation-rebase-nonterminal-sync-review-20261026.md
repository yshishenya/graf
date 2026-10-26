# T101 — независимая проверка squash после нетерминального sync merge

Проверяющий `/root/growth_security_gate`, 26.10.2026.
Рабочая копия `/Users/yshishenya/.codex/worktrees/growth-guide-links/crisp`.
Исходная ветка `codex/211-release-rebase-proof`, HEAD
`a1603a4c3714f4dbf242c1c06311a9543861cb9e`.
Область — замечание P2 review4378496721 PR #7745, минимальная маршрутизация
исторического source на существующее доказательство synced squash.

## Гейт требований: PASS

Перечитаны все шесть вопросов reviewer checklist rebase-proof:6 `[x]`,0 `[ ]`.
Отметки не менялись. FR-008 и T101.4 требуют сохранить ранее отдельно
доказанные формы; источник с sync merge и обычным commit над ним остаётся
synced source. Однородительский последний commit не доказывает линейности
всего диапазона. Исправление выбора ветки является устранением регрессии,
новое продуктовое/доверительное требование не требуется.

Различаются две формы, и их границы сохраняются:

- Линейный source replay: доказан полный исходный диапазон N без merges,
  затем каждое промежуточное target tree либо независимый squash prefix.
- Ранее поддержанный synced squash: точный final tree равен проверенному
  source head, настоящий squash parent — его предок, точное число commits
  parent..head равно записи PR. Этот proof применим независимо от того,
  находится ли sync merge непосредственно на вершине source или под
  последующим обычным commit. Сам sync не выдаётся за линейный replay.

Terminal-sync rebase остаётся отдельным более узким доказательством с
проверкой каждой пары и исходной sync tree. Новое исправление не разрешает
произвольный nonlinear rebase, неверные counts/parents, изменённый final,
target advancement после synced source или обход через malformed Git output.

Scoped-разрешение F211
`.dev/release/f211-scoped-reading-authorization-20261026.json` проверено:
все7 исходных SHA-256 обязательных якорей совпали. Применимые текущие
T101 требования и зависимости маршрутизации прочитаны; это не новое полное
чтение продуктовых PRD/status.

## Самостоятельное воспроизведение до исправления

Reviewer создал отдельный временный Git с синтетическими файлами, без данных
пользователей. Последовательность: base → source commit; независимый target
commit; merge target в source; обычный source commit сверху; squash с точным
head tree и parent=checked target. API base намеренно показывает поздний
merge, исходная checked base определяется из доказанной истории.

Настоящие functions загружены в память из неизменных Git objects:

- До T101, `2df314e5ca8549e636d386cdb68fecc861ddf015`: **PASS**, возвращён
  точный checked target parent.
- На `a1603a4c3714f4dbf242c1c06311a9543861cb9e`: **FAIL**,
  `ValueError: merge/source range must be linear`.

У source head ровно один parent, но в диапазоне есть merge; записанный count3.
Таким образом подтверждены конкретная регрессия и применимость прежнего
synced-squash proof. Временные HEAD/refs/index до и после вызовов совпали;
временный репозиторий автоматически удалён. Активные Git/checkout/refs/index
не менялись. Это воспроизведение не является приёмкой будущего исправления.

## Независимая приёмка конечных байтов: PASS

Проверен незакоммиченный delta поверх указанного HEAD. Изменение validator
ограничено выбором ветки: перед linear proof выполняется настоящий
`rev-list --merges --max-count=1 merge_parent..head`. Пустой вывод сохраняет
linear path; единственный полный SHA направляет nonlinear source в прежний
synced-squash proof. Неизвестный либо многострочный вывод отвергается;
ошибка Git не поглощается и не превращается в разрешающий fallback.
Новые SHA не используются как доверительное доказательство: все прежние
проверки ancestry/count/exact final tree остаются обязательными.

Reviewer загрузил конечные байты validator в память и выполнил **22 отдельных
положительных/отрицательных проверки** на настоящем временном Git, отдельно
от авторских pytest fixtures:

- Один sync с0,1,2 обычными commits сверху:3 положительных сценария возвращают
  ровно исходный checked target parent, хотя API base уже продвинут дальше.
- Для каждой из этих форм неверный count, неверный final tree, прежний parent
  и unrelated root parent:12 сценариев отвергнуты.
- Два sync с обычным commit над каждым, три sync с двумя обычными commits
  над каждым:2 положительных сценария возвращают точный последний checked
  target parent.
- Два sync и неверный count: отказ. Два sync, затем несинхронизированное
  target-only изменение и настоящий aggregate squash на advanced target:
  отказ `synced source requires the exact checked final tree`. Этот патч
  не расширяет прежнюю границу synced proof на такой target advancement.
- Инъекции ошибки нового Git command, `unknown` и двух SHA:3 отказа;
  разрешающий результат не получен.

Во всех22 сценариях HEAD/refs/index временного репозитория до и после helper
совпали. Временные репозитории автоматически удалены; данные синтетические.
Активные Git/checkout/refs/index не менялись.

Повторно просмотрены вызывающие `validate_trusted`, `ci-pr-scope.resolve`,
`validate-pr-checks.code_snapshot/verify`: они продолжают использовать
возвращённую checked base и прекращают проверку при ошибке. Историческая
checked base не заменена moving API base; выдача trusted-result всё ещё
требует успешных identity/metadata/diff и двух API snapshots.

Авторский before-log независимо прочитан:2 FAIL/10 PASS, падают именно
положительные нетерминальные формы с1 и2 followups. Конечный профильный
набор завершён: **475 PASS за88.10s**. Прочитан static log: ruff,
agent-context, changelog-fragments, legacy-impact, development-process,
spec-kit-governance — PASS. Эти журналы автора не выдаются за отдельный
повторный запуск reviewer; собственное исполнение reviewer —22 сценария выше.

## Точные SHA-256 проверенных байтов

| Артефакт | SHA-256 |
| --- | --- |
| `scripts/validate-pr-metadata.py` | `1d45434a65a4bc0f88b3e0d615b468020531b7dd61ecd91cd0c06d9cbe7dd772` |
| `tests/governance/test_pr_metadata_event.py` | `c57cabae1dd3177fac1b3d6d213d7b37213651243bd7ca60e48a93ad3e290436` |
| `tests/governance/test_pr_checks.py` | `1002b386c118b01015e4caa037b2163b07d7c71468e3abef976db386820bcae0` |
| `.dev/release/t101-nonterminal-before.log` | `264593a559788133927c4794630827e52744a1acc1d63ee9545a650d122bad5a` |
| `.dev/release/t101-nonterminal-focused.log` | `84c48e632ae2c940b2a183eb088a6f05e14b3f22fd2615781228d4edab5b11ff` |
| `.dev/release/t101-nonterminal-static.log` | `efec9e349ff42ff060b84ebaa0cba30f75105e10976fbefac9fea1bb3797c75f` |

Checklist `rebase-proof.md` повторно прочитан после приёмки: **6 `[x]`,0 `[ ]`**;
отметки не менялись. Новых замечаний в узкой области исправления нет.
Reviewer изменил только этот отчёт; код/tests/requirements/tasks/checklist/
Git/GitHub/release/deploy не менял. `git diff --check` выполнен отдельно.

Это локальная scoped-приёмка перечисленных конечных байтов. Exact-SHA/base
проверки PR после нового commit, слияние, T102/live verifier/Full/dry-run/
backup/CD/public acceptance и результаты продвижения остаются отдельными
гейтами; их прохождение этот отчёт не заявляет.
