# F227/#7645: текущая независимая проверка T032–T033

Дата: 19.10.2026. Reviewer: `f228_checklists_review`; навык `code-reviewer`.
Ветка: `codex/227-ci-merge-queue-release-train`.
HEAD/база: `c6c5441c930b8c1ecffed6de9b80773aa0e757e5`.
Полоса проверки: **Active Spec Kit slice**, инфраструктура и происхождение
выпуска. Текущий объём не включает всю F227.

## Решение и границы

**APPROVE проверенного локального изменения; P0/P1/P2 замечаний нет.
Качество требований PASS: requirements16/0, infra13/0, всего29/0.**
Это результат текущего чтения исходников и требований. Отметки контрольных
списков сохранены, добавлены только датированные примечания reviewer.

Исходные T001–T031 остаются открытыми. Историческое расхождение31 открытой
задачи с закрытыми child issues сохраняется в T030/#6237; текущий срез его
не скрывает. Настоящие GitHub T029/T031, authoritative API mapping, включение
native queue, exact-SHA проверки будущего PR, слияние и выпуск этим решением
не подтверждаются. Удержание слияний на согласованное окно F280 сохраняется.

## Область чтения

Проверены AGENTS/index и активный pointer/пререквизиты F227, конституция7.1.0,
применимые правила spec-kit-flow/product-gates/release-and-validation.
Их контрольные суммы совпадают с уже прочитанной версией guidance в текущей
работе; разделы конституции V/VI и независимого reviewer gate перечитаны.
Прочитаны active spec/plan/tasks/quickstart, clarifications/research/data-model,
оба contracts, оба checklist, analysis/review/validation от17.10 и fragment.
Просмотрены все16 изменённых файлов, существующий train schema/validator,
текущая функция и её единственный caller, реальный release operator и тестовый
набор release_train.

Существующее APPROVE17.10 сопоставлено с фактическими service/test hashes;
его9 независимых и121 общего исторического теста не объявляются новыми.
Закреплённый harness v0.1.13/SHA и описанная Python3.9/3.12 matrix сохранены;
исторический внешний GitHub run повторно через сеть reviewer не проверял.

## Проверка реализации

В `require_git_commit_relationship` удалено только старое условие OR, которое
допускало base→synthetic вместо base→source. Все три значения по-прежнему
проверяются `git cat-file ...^{commit}`; любой ненулевой результат
`git merge-base --is-ancestor base source` теперь останавливает операцию.
Ошибки/неполная история Git не превращаются в успешное ancestry доказательство.
Source/synthetic остаются различными полными SHA.

Единственный caller — train-freeze. Порядок сохранён: валидация параметров,
HEAD/origin master, существование commits и ancestry, чистота дерева,
changelog digest, authoritative exact PR set, schema, затем создание train
и immutable identity. Следовательно, отказ ancestry происходит раньше обеих
записей. Изменение не обходит PR proofs, Full CI, attest/decision и write-once
идентичность. Другие операции используют неизменяемые manifests; пересоздание
исторических результатов не требуется.

Настоящий serial operator `scripts/release.sh` создаёт отдельный commit-tree
с деревом actual source и родителями base/source. Он не передаёт merge-group
коллекции, поэтому они остаются пустыми. Такой коммит подтверждает происхождение
данных выпуска, но не событие GitHub очереди. Новый guard совместим с ним.
Условие source→synthetic не добавлено: future queue synthetic может
предшествовать фактическому post-merge source, поэтому это было бы другим
требованием.

Новая регрессия вызывает настоящий release-candidate в отдельном Git repo:
успешный serial freeze/validate содержит три PR, раздельные source/synthetic
и пустые queue arrays. Затем base из самостоятельной истории является
предком собственного synthetic, но не actual source: ожидается точный отказ
и отсутствие manifest/identity. Последний шаг сохраняет отказ для отсутствующего
synthetic commit. PR/Full proofs подставлены fixture, что прямо указано в
quickstart и отчётах. Тест проверяет причину исходного дефекта; существующие
восемь сценариев не заменяют эту отрицательную проверку.

Схема, CLI, реальный release caller и validate-pr-checks не изменены.
Новых режимов, зависимостей, nullable synthetic и исключений совместимости нет.
Legacy Impact `untouched` соответствует текущему объёму. Код приложения,
данные, signing/notarization и защита GitHub не затронуты.

## Каждый пункт requirements

Нумерация ниже соответствует порядку16 существующих пунктов.

| Пункт | Основание PASS требований |
|---|---|
| 1. Детали реализации | Наблюдаемые SHA/отказ/поля являются контрактом; конкретная общая функция описана в plan/tasks. |
| 2. Ценность | Цель и Why US связывают изменение с достоверным CI и безопасным выпуском. |
| 3. Язык | Цели, уточнения и границы понятны; имена Git/GitHub и полей сохранены для точности. |
| 4. Секции | Есть сценарии, приёмка, edge cases, FR/SC, assumptions, exclusions и Legacy Impact. |
| 5. Уточнения | Нет NEEDS CLARIFICATION; C1–C6 различают действующий serial и будущий native этап. |
| 6. Проверяемость | FR001–011 задают identity/отказы/чистоту/ancestry; T033 имеет точный результат. |
| 7. Измеримость | SC001–007 определяют mismatch0,100% отрицательных случаев, три PR, один Full CI и отсутствие output. |
| 8. Технологическая граница | Результат — достоверная идентичность выпуска; Git/GitHub необходимы для существующего контракта. |
| 9. Сценарии | US1–US3 охватывают CI/stale/train; SC007 уточняет serial/orphan-base. |
| 10. Пограничные случаи | Неизвестные SHA, недоступная история, cancellation, drift, API mapping и synthetic/source различены. |
| 11. Объём | Продукт, включение очереди и выпуск исключены; T029/T031 сохранены. |
| 12. Допущения | Действующие PR checks, serial режим, один Full CI и закреплённый harness названы. |
| 13. Критерии FR | FR001–010 связаны с US/SC/tasks; FR011 со SC007/T033. |
| 14. Основные потоки | Exact identity, stale rejection и train представлены; serial поправка не заменяет native gates. |
| 15. Измеримые исходы | Spec задаёт измеримые SC; отметка не является фактическим выполнением всей F227. |
| 16. Приватные данные | Текущие требования и fragment содержат только служебные сведения/публичные SHA/ссылки. |

## Каждый пункт infra

| Пункт | Основание PASS требований |
|---|---|
| 1. Event target/base | FR001/002 и receipt contract различают PR/merge-group/manual exact identity. |
| 2. Checkout/mapping | FR003 и R6 требуют authoritative полный mapping и безопасный отказ; T029/T031 открыты. |
| 3. Concurrency | FR004/US2 исключают отмену другой логической цели. |
| 4. Cancellation/stale | FR004/006/008 и SC002 запрещают non-success evidence. |
| 5. Final cleanliness | FR005/SC003 требуют tracked/untracked gate после артефактов с ограниченными исключениями. |
| 6. Schema/metadata | FR006/contracts и plan ограничивают структуру и запрещают private data. |
| 7. Synthetic/source | FR007/011/уточнения различают provenance и actual source; новый guard требует base→source. |
| 8. Один Full CI | FR008/SC004/release contract требуют immutable candidate и единственное authoritative proof. |
| 9. Владелец protection | FR009 и exclusions сохраняют отдельный этап оператора после проверки workflow. |
| CHK010 | Spec/plan/quickstart/tasks сохраняют serial/native границы и открытые T029/T031. |
| CHK011 | FR011/SC007 требуют actual source ancestry, три local commits и отказ до train/identity; код соответствует. |
| CHK012 | Plan/quickstart явно различают fixture proofs, реальные PR checks и release-full. |
| CHK013 | R8/quickstart и harness lock сохраняют exact pin, Python3.9/3.12 и ограничения исторического run. |

После дополнения примечаний оба checklist перечитаны: requirements
**16 checked / 0 unchecked**, infra **13 checked / 0 unchecked**,
всего **29 checked / 0 unchecked**. Требования к будущему native этапу
отмечены как качественно описанные, а не как выполненные в GitHub.

## Текущие проверки

После первичного оформления завершился свежий focused запуск основного агента.
Reviewer прочитал законченный журнал и XML: **121 различная проверка PASS /
0 FAIL / 0 ERROR / 0 SKIP**, 79.65с. Разбивка: release_train9,
release_candidate20, merge_group_mapping18, ci_event_identity11,
governance_workflow43, ci_evidence_producer6, ci_guard14. Новый ancestry
случай входит в девять release_train и в121; отдельно не прибавляется.
Runtime/test hashes повторно совпали после сверки результатов.

Исторические9/121 и старый harness run не переаттестованы и не прибавляются
к текущему числу. Это проверка нового результата основного агента, а не
собственный второй запуск reviewer. Reviewer тесты, приложение, Docker,
GitHub или выпуск не запускал. Доказательства находятся во внешнем каталоге
`2026-10-19/f227-current-preflight`; fixture proofs остаются синтетическими.

## SHA256 проверенного изменения

| Файл | SHA256 |
|---|---|
| infra/scripts/release-candidate.sh | dcfa09b9e643cbf64481926ffa8586b61e130ec9844893bd6121feeee625beeb |
| tests/governance/test_release_train.py | 186669f39ecc5e824e788250a2d49e7aa4b8e29468ea0079f801deb47a7cf84d |
| changes/unreleased/F227.yaml | 60a8aad75b4a4f604c1e11eee947e2d0506d7450b9bfcd367b5e530dbe98225c |
| spec.md | 196f4b6f02f0feca8446ba766c9e6c77c4ed200ba2e3b4930ba315afb82df071 |
| plan.md | af3f86d6ff24e1828aca10d30f4df0a953b89d6c7e855b9426190deaa1179d60 |
| tasks.md | 3ffaf2a67c64a78962e3c3f260b97757211e7a10f97e7c0f884617a38a79eb90 |
| quickstart.md | d7f112e935b70dd9aba2c88aa31510c2794c2b37ec05b5f1d21ff0580ed9fbc8 |
| requirements.md после примечания reviewer | 49bf6d723c387ca2b12d0193d6e07a0bdaef20dece8efdd0dc123abf8c31a6c8 |
| infra.md после примечания reviewer | f1a6c65b8af5090f0f0aaffebcf087e758efa7f954215c0dabf5bea2e7f72b15 |
| current-governance.xml | 20d290463f90d765c5eb16f38798caea0cf4ef0d2f0b98f1de9abdebad3cb085 |
| current-governance.log | 6b3b9f03ea33ed2a7da75ca998190e6ca766c5393700d8e23ee2d29cf7e663d4 |

Изменения reviewer ограничены двумя принадлежащими ему checklist и этим
отчётом. Код/spec/plan/tasks/исторические отчёты и чужие правки сохранены.
Проверка оформления `git diff --check` выполнена; она не заменяет runtime,
exact-SHA GitHub проверки, разрешение слияния или производственный выпуск.
