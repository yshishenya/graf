# Независимая проверка требований T101/T102

Дата:26.10.2026. Проверяющий: `growth_infra_gate`.
Рабочая копия: `/Users/yshishenya/.codex/worktrees/growth-guide-links/crisp`.
Ветка: `codex/211-release-rebase-proof`.
HEAD: `2df314e5ca8549e636d386cdb68fecc861ddf015`.
Lane: active Spec Kit slice / high-risk CI/governance, только проверка требований.

**PASS:6 checked,0 unchecked.** Это качество текущих требований T101/T102,
не реализация, успешное выполнение матрицы, проверка PR или выпуск.

## Проверенные пункты

| Пункт | Точное основание | Вывод |
| --- | --- | --- |
| CHK001 | spec T101 clarify/пункт1, plan шаг2 | Source checked base и target start различены; N, линейность, смежность, направление ancestry и исходная возвращаемая база определены. |
| CHK002 | spec пункты1–2, plan шаг2 | Проверяется полное дерево каждой пары, также при равном final; конфликт/ошибка/unknown/missing object/count/ancestry не дают replay PASS. Явный source parent обязателен. |
| CHK003 | spec пункт3, plan шаг3, research T101 | Aggregate разрешён только при полном линейном независимом prefix и точном three-way tree. Учитываются пути каждого промежуточного commit обеих цепочек, возвраты, rename/delete и путь-предок; NUL/`--no-renames`. Overlapping squash может быть unsupported. |
| CHK004 | spec A6 identity:290 и T101 пункт4, plan:225 и шаг4; историческая T098 | Прежняя несовместимая формула A6 заменена ссылкой на текущий контракт. Sync/two-parent остаются отдельными доказательствами; identity, snapshots, freshness, run/attempt и required checks сохраняются. Старый T098 не переписан. |
| CHK005 | spec пункт5 и запрет мутации в пункте4, plan шаг5, quickstart T101/T102 | Есть настоящий Git advanced/same-base positive, regression-before-fix, промежуточная скрытая порча, count/drop/extra/order/nonlinear/unrelated/error/missing/conflict negatives и overlap матрица. Scope/full consumers сохраняют base/diff и отказы неправильных receipts; checkout/refs/index/source неизменны. |
| CHK006 | spec пункт6, plan шаг5, quickstart T101/T102 | T101 локальная реализация/review/PR и T102 live range/frozen Full/dry-run/backup/CD/public acceptance разделены. Продажи, рост и запуск полной F273 из исправления не следуют. |

Существенных/блокирующих пробелов в этом delta не выявлено. Прежний BLOCK
от22.10 по различию checked base и началу target устранён текущим уточнением.
Это не означает, что прежнее техническое предположение об универсальном
различении squash/replay подтвердилось: shape-review от26.10 его опровергает,
и текущая консервативная граница является существенной частью принятия.

## Почему консервативная граница достаточна

Рассмотренный shape-review показывает одинаковые parents/trees/count для
действительного squash и replay со скрытой промежуточной подменой. Поэтому
ни конечное дерево, ни топология, ни aggregate после любого replay отказа
не определяют исторический метод merge. Текущие требования этого не обещают.

Два положительных доказательства разделены: точное воспроизведение всех
N деревьев или независимый полный prefix плюс точный squash. Если целевая
история коснулась исходных путей, в том числе временно и затем вернула байты,
её нельзя принять вторым путём. Простого итогового diff недостаточно.
Проверка ancestor-путей предотвращает обход через замену файла каталогом.
`--no-renames` вместе с объединением per-commit путей сохраняет обе стороны
rename как delete/add; ошибка перечисления не превращается в пустой набор.

Спецификация допускает блокировку правильного overlapping squash как
неоднозначного. Это явное ограничение поддержки, без нового доверенного факта,
whitelist или ослабления proof. Независимость путей не проверяет качество
остальной target history; каждый другой PR по-прежнему требует своих receipts.

## Обязательные следующие ворота

1. Сгенерировать T101/T102 tasks после этого checklist PASS; затем scoped
   analyze текущих spec/plan/tasks и issue sync. На момент проверки tasks
   заканчивался T100. Это правильный порядок до генерации, а не выполненная
   реализация или уже принятая трассировка новых tasks.
2. Сначала доказать FAIL старого кода реальным временным Git, затем минимальный
   fix и всю матрицу; существующий target-only N2 squash должен остаться PASS,
   а не получить ослабленные ожидания. Сохранить все sync negatives/positives.
3. Отдельно проверить shared consumers, непорчу checkout/refs/index/source,
   независимое implementation review/converge и exact-SHA/base PR checks.
4. Только T102 подтверждает актуальный диапазон, frozen candidate/один
   authoritative Full и штатный выпуск. Этот отчёт не даёт разрешения на
   production, включение аналитики или внешние сообщения.

## Прочитанные источники и пределы

Проверены активные `.specify/feature.json` и prerequisite paths, AGENTS.md,
guidance index, `spec-kit-flow.md`, `development-process.md`,
`document-reading.md`, применимые release/identity/trust правила, конституция
7.1.0, текущие T101/T102 разделы spec/plan/research/quickstart полностью,
связанные FR-008/FR-039–041/SC-019 и A6 identity/review delta, прежняя T098
и её checklist, существующий tasks.md. Исторические отметки не изменены.

Выполнена собственная read-only сверка текущего `checked_base`, shared callers
`ci-pr-scope` и `validate-pr-checks`, существующих положительных squash и
historical-scope test историй. Прочитан целиком corrected shape-review
`.dev/release/rebase-shape-review-20261026.md`; это исследовательское
обоснование контракта, не исполняемое доказательство его будущей реализации.

Действует прямое scoped разрешение
`.dev/release/f211-scoped-reading-authorization-20261026.json`. Все7 базовых
SHA-256 совпали: AGENTS, constitution, PRD, current status, document-reading,
product-gates, release-and-validation. Совпадение хеша не выдаётся за новую
полную продуктовую проверку. Продуктовые PRD/status целиком заново не загружены
по разрешённому объёму; продуктовые изменения текущим подэтапом не допускаются.

| Артефакт | SHA-256 проверенного содержимого |
| --- | --- |
| spec.md | `2c835cbf01688db805cd756972d9221b5e5b299e958fb61d16aa52f07e3f0425` |
| plan.md | `7c573b6fbd385e6a0a7333edf801c78db31cc37b8fcfdaa6cce2a24656a1fb34` |
| research.md | `612fceb783e6787598a0885e8acb6a70c258a67fba744fa059aebdfc41ce5e9b` |
| quickstart.md | `28219e033ec8f61fca4b1b745508480fc6162fc73b5bf8b552a60145dcbd8bba` |
| tasks.md до генерации T101/T102 | `6a35e833b6fc901037619f06a53375a57832ec71115767cb6047c546fba9e9cf` |
| corrected shape-review | `bdae966e8951c3431c0d408d12cb57038bdebbf93c2d288a8a45396c70108ae4` |
| validate-pr-metadata.py | `d91ff39356901b384b2f235ecea0087e27dfcdb53f28f78d7286d8c10d91e5ab` |
| spec-kit-flow.md | `afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e` |
| development-process.md | `1037b91f153f0757fff372e26cd05dd31433158c9c35d149125197a8a523f20d` |

Записаны только `checklists/rebase-proof.md` и этот отчёт. Тесты, Git object
writers, Git/GitHub mutations, сеть, release и deploy не выполнялись.
Итоговый checklist перечитан после изменения: **6 checked/0 unchecked**.
