# T101 — независимое ревью реализации исторического replay

Проверяющий `/root/growth_security_gate`, 26.10.2026.
Рабочая копия `/Users/yshishenya/.codex/worktrees/growth-guide-links/crisp`,
ветка `codex/211-release-rebase-proof`.
Исходный HEAD `2df314e5ca8549e636d386cdb68fecc861ddf015` плюс незакоммиченный diff.
Полоса: high-risk CI/governance, существующая T101.

**Актуальный итог: scoped PASS кода после исправления P2.** Новых
блокирующих находок на конечных проверенных байтах не выявлено. Собственные
11 проб reviewer прошли. Итоговый полный профиль на этих байтах, exact-SHA/base
PR и T102 release остаются самостоятельными доказательствами. История первого
BLOCK ниже сохранена.

## Первая проверка: BLOCK, одно замечание P2

### P2: неизвестный target rev-list может превратиться в разрешённый squash

Проверенные байты `validate-pr-metadata.py` SHA-256
`ed11e33cb0f61157337d77226f60c03a94dedfb99cb39143fe373e2c30df244c`.
`linear_rows(merge, count)` выбрасывает один ValueError как при допустимой
неподходящей форме N предков, так и при пустом/повреждённом stdout.
Общий `except ValueError` превращает обе ситуации в `target_rows=[]` и
переходит к aggregate. При независимом squash этот путь возвращает PASS.

Это не обход по вредоносному тексту PR и не доказательство порчи Git;
это нарушение явно принятого T101.2/плана: неизвестный вывод Git должен
закрывать проверку, а не становиться неподтверждённым отсутствием replay.

Reviewer самостоятельно воспроизвёл это вызовом настоящего `checked_base`
с синтетическим провайдером Git-команд в памяти. Полная линейная source
цепочка N=2, независимый target prefix, корректный aggregate tree;
единственная аномалия — успешный пустой stdout target `rev-list --parents
--max-count=2`. Фактический результат — возврат source base/PASS вместо
отказа unknown. Проба не записывала Git objects, файлы или внешнее состояние.

Нужно отделить структурно недопустимый stdout/непрерывность от корректно
прочитанной истории, которая просто не имеет N линейных предков. Только
последняя может перейти к независимому squash proof. Добавить regression
на independent-squash, где именно эта ошибка раньше маскировалась PASS.
Автор получил замечание и сообщил о подготовке исправления; будущий PASS
этим первым выводом не предвосхищается.

## Остальная проверенная область

- Новый линейный путь возвращает source base, а не движущийся API base или
  target start. Каждая пара проверяется explicit source-parent merge-tree;
  одинаковый final tree не позволяет пропустить промежуточные проверки.
- Aggregate допускается только после полной проверки независимости prefix:
  объединение путей каждого commit с обеих сторон, NUL, no-renames,
  сохранение whitespace и отношения путь-предок в обоих направлениях.
  Возвраты/rename/delete/file-directory не сокращаются до итогового diff.
- Пересекающийся настоящий squash может получить unsupported — это принятая
  граница; универсальный метод merge не заявляется. Message/author/patch-id/
  PR allowlist не используются.
- Two-parent и terminal-sync обработка остаются отдельными; их текущие
  положительные/отрицательные истории перечитаны. Удаление недостижимой
  старой aggregate ветки не меняет отдельный exact-final sync guard.
- Все callers найдены: trusted metadata, `ci-pr-scope.resolve`,
  `validate-pr-checks.code_snapshot/verify`; конечные PR/source/gate snapshots,
  exact base/head/repository/workflow/run/attempt identity и защита receipts
  не менялись. Новые настоящие scope/full-consumer тесты сохраняют source
  diff/base и отказы wrong receipt base, failed gate и stale metadata.

Прочитаны текущие T101.1–6, plan/research/quickstart/T101–T102 и reviewer
checklist 6/0. Checklist принадлежит другому reviewer, не редактировался.
Прочитан журнал before-fix:8 failed/24 passed; after-fix regression:36 passed;
поздний focused четырёх файлов:282 passed/92.47s. Это исполнение автора,
самостоятельно широкий suite reviewer не повторял. Сообщённый live PR7714
PASS не подменяет проверку конечных байтов нового T101 PR и T102 release.

## Границы

Reviewer может изменять только этот отчёт. Код, тесты, spec/plan/tasks,
checklists, Git/GitHub/release/deploy не менялись; параллельные чужие изменения
сохранены. Первоначальный BLOCK снят повторной проверкой ниже.
Трафик, продажи, production и весь F211/F273 этим ревью не принимаются.

## Повторная проверка исправления P2

Автор удалил широкий catch. Структурная валидация rev-list теперь выполняется
до допуска альтернативной формы: непустой ответ, не больше N строк, точные
SHA всех полей, первый commit равен запрошенному, уникальные commit IDs,
непрерывность однородительских переходов. Только корректно прочитанная
неподходящая N-форма (short/root/merge) даёт возможность отдельно доказать
полный независимый squash prefix. Пустой/повреждённый/несмежный вывод
больше не превращается в разрешение aggregate.

Проверены также смежные строгие отказы: ancestry exit1 означает «не предок»,
а exit>1 является ошибкой; непустой Git path output требует конечный NUL и
не допускает пустые внутренние имена. Whitespace в настоящем имени
сохраняется, `surrogateescape` не превращает байты имени в потерянный путь.

На текущих байтах reviewer самостоятельно вызвал настоящий checked_base
в памяти с подменой только провайдера Git-команд. **11/11 PASS**:

- empty/invalid/noncontiguous/missing-first/duplicate target history
  отвергаются;
- ancestry error, неизвестный не-NUL path output и ошибка Git diff отвергаются;
- неизвестный и многострочный tree output отвергаются;
- здоровый независимый squash проходит и возвращает source base, отличную
  от движущейся API base.

Это проверки поведения настоящего helper, без файловых/Git/сетевых мутаций;
они не заменяют настоящий временный Git suite автора. Поздний промежуточный
журнал `t101-focused-reviewed.log` завершён286 PASS/97.77s, но запуск начался
до последних смежных уточнений; не выдаётся за окончательную валидацию всех
конечных байтов. Автор выполняет финальный профиль отдельно после review.

Проверенные конечные SHA-256:

| Артефакт | SHA-256 |
| --- | --- |
| scripts/validate-pr-metadata.py | `52c57bc0c95a9a06afbb9e518a8370f58115f65416d09b11df44c1a61f6296e7` |
| tests/governance/test_pr_metadata_event.py | `f2f4f29faa2188729762fd7237685f7567567d9480ba3fc776751b6306b66b80` |
| tests/governance/test_pr_checks.py | `48b142dfda67ea7550f9ee540f622d490422810092747cc6d0c9a771e2dfab45` |
| before-fix-shape log | `06e7efe9dbdc6b77b34a1a79d1092621d9d140d6d09a427f3d274138a01611db` |
| after-fix-regression log | `85bcfb9d9c40d47bc523d66667a5124937b05ef2216c489c6a32326faf02c78a` |
| первый focused282 log | `86682cf43659d8e7ea15ceb5147a2b9bc48d66fd9a5a930b0505080b135e548a` |

Все7 исходных хешей разрешения
`.dev/release/f211-scoped-reading-authorization-20261026.json` независимо
сверены и совпадают. SHA-256 разрешения:
`cac49184b15eba11953eda740b92d64621e14a3295abd367b699d900912fdb6e`.
Применимые текущие T101 требования/зависимости прочитаны полностью;
по разрешённому объёму это не новое полное чтение продуктовых PRD/status.

Checklist повторно прочитан:6 `[x]`,0 `[ ]`; отметки reviewer не менял.
HEAD не изменился. `git diff --check` PASS. Разрешённая запись reviewer
по-прежнему ограничена этим отчётом. T101 не закрывается этим code review;
завершённый актуальный профиль, convergence и hosted проверки ещё требуются.
