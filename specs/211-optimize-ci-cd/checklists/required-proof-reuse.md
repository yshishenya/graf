# A6 required-result reuse requirements

- [x] CHK001 Are fixed required names, unchanged code/native execution, and separate text concurrency explicit? [FR-040]
- [x] CHK002 Does component reuse require the latest actual source run/attempt with exact identity, no PASS fallback, and no text-chain/self-cycle? [FR-040]
- [x] CHK003 Do bounded waiting and double snapshots catch source changes and all gate/source attempts before common PASS? [FR-040/SC-019]
- [x] CHK004 Are executable negatives and actual GitHub merge-box acceptance required, with protection/history preserved? [SC-019]
- [x] CHK005 Does merged-PR text reuse derive the immutable checked base in scope and event/API snapshots, retain the real merge SHA, and reject invalid merge history or state? [FR-040/SC-019]
- [x] CHK006 Are governance artifacts named for the exact run/attempt, with an unambiguous legacy reader that cannot mask a bad exact artifact or mix attempts? [FR-040/SC-019]

Reviewer-owned requirements gate. Implementation must not mark checkboxes.

## Независимая проверка требований — 2026-09-13

Рецензент: `requirements_review`, отдельно от исполнителя A6. Проверены
уточнённые FR-040 / SC-019, раздел A6 T080–T081 в plan, обе задачи и приёмка
в quickstart. Предложение ранее сопоставлено с фактическими workflows,
`ci-pr-scope.py` и `validate-pr-checks.py`.

- **CHK001 PASS.** FR-040 и plan сохраняют постоянные обязательные имена,
  действующие code/native проверки и guards при ошибке scope. Текстовые события
  исключают тяжёлые команды и создание новых source receipts; отдельная
  concurrency не отменяет исполнение кода/native.
- **CHK002 PASS.** Уточнение FR-040.1–4/6 требует последнюю исходную попытку,
  включая поздний повтор старого run ID, и точную identity. Только проверенный
  scope разрешает исключить текстовый run. Текстовый итог не является источником
  нового доказательства, не ожидает себя/другой текстовый итог/другой компонент.
  Failed/cancelled/running не разрешают возврат к старому успеху.
- **CHK003 PASS.** Plan задаёт конечное ожидание и достаточный timeout native
  result на Ubuntu. Замечание P2 к полноте финальной проверки устранено:
  FR-040 clarification.6/8, plan A6.5, T080 и quickstart требуют актуальный
  gate run/attempt включая text, единственную задачу с обязательным именем
  и повторную сверку всех source/gate attempts перед общим PASS. Повтор на
  том же SHA во время проверки другого компонента блокирует прежний набор
  даже при неизменном PR snapshot; rollup/последний success не заменяют проверку.
- **CHK004 PASS.** T080 ставит исполняемые отрицательные API/terminal-shell
  сценарии до реализации T081. SC-019 и quickstart требуют отдельную live
  проверку блока слияния GitHub при body edit во время/после исходных тестов:
  required checks не остаются expected, source tests не отменяются/не повторяются.
  Protection, source receipts, сроки хранения и historical/post-merge binding
  сохраняются. Локальные проверки не объявляются hosted приёмкой.

Итог: **PASS 4/4, открытых замечаний проверки требований нет**.
Независимый requirements gate для T080 снят; clean analyze и issue evidence
остаются отдельными prerequisites. Изменён только этот checklist; код, другие
документы, тесты, сборки и GitHub не изменялись и не запускались.

## Уточнение требований после независимых замечаний к PR #6990 — 2026-09-13

Рецензент: `requirements_review`. Подтверждены причины замечаний
`4000081305` и `4000081311` к исходному SHA
`97f2348e8008be17f987fed1bd973895d8770b41`; текущая перебазированная ветка при
проверке — `2279b309f9fa48056560199c5ffa05b046b6027b`. Просмотрены оба комментария
GitHub, `reuse` / `code_snapshot` / reader артефактов, producer workflow,
`ci-pr-scope.resolve` и существующий `metadata.checked_base` с проверками истории.
Это уточнение существующих FR-040/SC-019; продуктовые возможности и полномочия
не расширяются.

**CHK005 PASS — требования к текстовому событию после слияния.**

- Только открытый PR либо закрытый и действительно слитый PR допускается к
  повторному использованию. Закрытый без слияния, противоречивое состояние,
  отсутствующая identity или недоступные Git objects дают отказ.
- Для слитого PR scope использует существующий `metadata.checked_base`:
  равенство деревьев исходного head и merge, точная история squash либо
  linear rebase, правильные predecessor и число commits. Простого ancestry
  недостаточно; новая реализация алгоритма определения базы не нужна.
- Снимки события и текущего API в `reuse` сравнивают одну и ту же проверенную
  базу слияния. Движущийся `api_base_sha` слитого PR не является identity кода;
  продвижение master до или во время обработки события не инвалидирует
  неизменное слияние. Для открытого PR актуальная API base остаётся обязательной.
- Настоящий `merge_commit_sha` слитого PR входит в `code_snapshot` и повторную
  проверку перед PASS. Асинхронный synthetic merge SHA открытого PR остаётся
  нормализованным в null. Смена настоящего merge SHA, head, checked base,
  repository, refs, commit count или состояния запрещает прежнее доказательство.
- Governance и native используют прежние исходные proofs на этом head/base;
  native сохраняет равенство `paths_digest` / `native_required`. Свежий metadata
  proof нужен для актуального title/body. Последний текстовый required gate
  проверяется полным consumer, как и для открытого PR.

Минимальные исполняемые границы приёмки:

1. Успех обоих компонентов после допустимых squash и linear rebase при уже
   продвинувшемся master; исходный проверенный diff остаётся прежним.
2. Дополнительное продвижение API base между event и текущим снимком, затем
   между снимками проверки слитого PR не создаёт ложный отказ. Смена настоящего
   merge SHA при том же head/tree/base, переход open → merged и прежние
   head/base/ref/state races создают отказ.
3. Неверные tree, parent/count, неподдерживаемое слияние и closed/unmerged
   не дают PASS. Существующие проверки `checked_base` переиспользуются;
   регрессии должны проверить и новую связь helper → scope/reuse.
4. Полный consumer принимает последнее успешное merged-text gate вместе с
   исходным proof и свежими metadata; failed/pending gate или stale source
   по-прежнему блокируют результат. Тяжёлые команды и новые source receipts
   в текстовой ветке отсутствуют.

**CHK006 PASS — требования к артефактам повторных попыток.**

- Producer governance включает `run_id` и `run_attempt` в имя артефакта.
  Формат внутреннего receipt и его обязательная run/attempt identity сохраняются;
  переименование внутреннего файла или расширение схемы не требуется.
- Reader сначала выбирает точное имя текущего run/attempt. Неуспешная предыдущая
  попытка и оставшиеся артефакты других попыток не делают новое точное имя
  неоднозначным.
- Чтение прежнего имени разрешено только если точное имя отсутствует и найден
  ровно один допустимый прежний артефакт. Его внутренние run/attempt/head/base,
  workflow/event и срок хранения проверяются прежним обязательным способом.
- Если точное имя найдено, его дубликат, истечение срока или неверные bytes /
  identity дают отказ. В этой ветке возврат к прежнему имени запрещён.
  Несколько прежних одноимённых артефактов не разрешают выбор последнего успеха
  либо артефакта по времени создания. Mixed-attempt proof всегда отклоняется.
- Имена scope/native/metadata, срок хранения и отсутствие governance receipts
  на текстовых событиях сохраняются.

Минимальные исполняемые границы приёмки:

1. Failed attempt 1 и successful attempt 2 с одним run ID: выбирается точный
   артефакт попытки 2, несмотря на оставшиеся артефакты попытки 1.
2. Точное имя имеет приоритет над присутствующими прежними именами; duplicate,
   expired, неверный run/attempt или содержимое exact не обходятся fallback.
3. Единственный исторический proof с совпадающей текущей identity читается;
   отсутствующий, expired, duplicate либо mixed-attempt legacy proof отклоняется.
4. Регрессии вызывают настоящий reader с подставными API/ZIP на границе
   провайдера, а не заменяют `artifact()` готовым словарём. Отдельно проверяется
   имя в фактическом producer workflow.

Итог уточнения требований: **PASS CHK005–CHK006; requirements gate PASS 6/6**.
Реализация двух исправлений, отрицательные/положительные регрессии и повторный
независимый review остаются обязательными до закрытия замечаний. Предыдущая
проверка реализации не подтверждает эти две границы; прежние live результаты
сохраняют только свою исходную область доказательства. Изменён исключительно
этот reviewer checklist; продуктовые тесты, Full, Swift и GitHub mutations
не выполнялись.
