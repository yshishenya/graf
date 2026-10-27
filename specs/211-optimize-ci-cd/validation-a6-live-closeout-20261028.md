# A6 — итоговая проверка T063/T087 и #6986, 28.10.2026

Полоса: документальная сверка существующего этапа F211. Поведение продукта,
workflows, проверки, полномочия и правила выпуска не меняются. Исторические
результаты и прежние отказы сохраняются.

## Матрица и неизменность исходников

На `ce459d98b6a4f929eba5c4101e2b0afb4e4e4844` исполнены **673 разных PASS**,
0 FAIL/ERROR/SKIP за 191,80 секунды, в девяти существующих файлах:

| Файл в tests/governance | PASS |
| --- | ---: |
| test_pr_scope.py | 13 |
| test_pr_metadata_event.py | 135 |
| test_governance_workflow.py | 142 |
| test_ci_event_identity.py | 11 |
| test_merge_group_mapping.py | 18 |
| test_validator_safety.py | 171 |
| test_release_train.py | 11 |
| test_pr_checks.py | 152 |
| test_release_candidate.py | 20 |
| Всего | 673 |

XML независимо пересчитан: 673 уникальных идентификатора, SHA-256
`36c1d823f1fd6505dbcefb514a7e6b5401f43847e86e3cc0c5d41a929f846ebc`.
Workflow validator/self-test и actionlint трёх workflows прошли. Между
исходником прогона и `a6578c550496d32d8085df6fcdcf7e8bfb1e9109` девять
файлов матрицы, A6 helpers и workflows побайтно сохранены; изменённый
`test_dev_harness.py` находится вне этой матрицы. Это повторное использование
проверенных неизменных файлов, а не заявление о новом исполнении 673 тестов
на другом SHA.

Матрица включает ошибки identity/API/scope, fork/retarget, failed/running/
cancelled source, ограниченное ожидание, последнюю попытку старого run ID,
параллельные текстовые события, отсутствие/ошибку/дубликат обязательного итога,
same-SHA смену выбранной попытки, настоящие Git squash/rebase истории,
неправильные деревья/базу/merge identity, закрытый без слияния PR и настоящий
reader API/ZIP с exact-first/legacy/mixed-attempt отказами. Подставляются
границы API/команд; настоящий Git исполняется. Это не приёмка живой merge queue.

## Проверка GitHub на современном PR

Использован [PR #7779](https://github.com/yshishenya/graf/pull/7779):

- source `a6578c550496d32d8085df6fcdcf7e8bfb1e9109`;
- checked base `c2185bb252f7cb4f3fb069fd5fdf7b2133997938`;
- штатный squash `f6b611e106f1d605b6d58debd4740ec8b24bafc9`;
- все перечисленные runs — attempt 1 и SUCCESS.

| Событие | governance-fast | macos-pr | pr-metadata |
| --- | --- | --- | --- |
| Исходный код | [40598361588](https://github.com/yshishenya/graf/actions/runs/40598361588) | [40598361627](https://github.com/yshishenya/graf/actions/runs/40598361627) | [40598362174](https://github.com/yshishenya/graf/actions/runs/40598362174) |
| Описание изменено во время source | [40598898849](https://github.com/yshishenya/graf/actions/runs/40598898849) | [40598898633](https://github.com/yshishenya/graf/actions/runs/40598898633) | [40598899519](https://github.com/yshishenya/graf/actions/runs/40598899519) |
| Описание изменено после source, PR открыт | [40600303376](https://github.com/yshishenya/graf/actions/runs/40600303376) | [40600303427](https://github.com/yshishenya/graf/actions/runs/40600303427) | [40600303654](https://github.com/yshishenya/graf/actions/runs/40600303654) |
| Описание изменено после слияния | [40600716937](https://github.com/yshishenya/graf/actions/runs/40600716937) | [40600716833](https://github.com/yshishenya/graf/actions/runs/40600716833) | [40600716899](https://github.com/yshishenya/graf/actions/runs/40600716899) |

Исходная Swift job действительно исполнила build/tests/ContractValidation.
Изменение описания во время source не отменило и не повторило исходные runs:
сохранены IDs, attempt, время начала, event, path и head. Текстовые проверки
дождались настоящих исходных результатов. Scope artifacts всех текстовых
событий содержат `text_only=true` и прежнюю проверенную основу. Кодовая
текстовая job пропустила установки ресурсов, fast и создание/upload CI receipt;
native текстовая проверка выполнила verifier на Ubuntu, Swift job skipped.
Для code/native text опубликованы только scope artifacts, новых source
receipts нет. После merge исходные время завершения и результаты также
не изменились.

В авторизованном интерфейсе GitHub во время source наблюдались постоянные
required имена, ожидающие source proof. После второй правки описания и
завершения проверок основной агент прочитал настоящий блок слияния:
`Ready to merge`, `All checks have passed`, `No conflicts with base branch`
и доступную обычную `Squash and merge`. После раскрытия группы все три
обязательных имени успешны; `expected` отсутствует. Отдельный терминальный
снимок перед второй правкой не заявляется. API rollup не использован вместо
этого наблюдения. Обход защиты не выбирался.

Общий `scripts/validate-pr-checks.py --repository yshishenya/graf --pr 7779
--expected-sha a6578c550496d32d8085df6fcdcf7e8bfb1e9109` прошёл:

1. Перед обычным слиянием после after-source text.
2. После слияния, сохранив настоящий merge SHA и source checked base.
3. После postmerge text, с новой trusted metadata40600716899 и прежними
   source40598361588/40598361627, без цепочки текстовых proofs.

Полное дерево принятого squash совпало с проверенным source. Ранние вызовы
общего verifier до окончания source/scope отказывали; их журналы сохранены,
они не переименованы в PASS.

Защита master до и после сценариев: три required context `governance-fast`,
`macos-pr`, `pr-metadata`, app15368, strict=true, linear history=true,
approval count0; неразрешённых review threads нет. Каноническая граница
активации foundation #6987 / `a3f5f72e994e7872ee175ebafd9f7699a2d4ffca`
и 13.09.2026 13:18:40UTC сохранена.

## Требования, согласованность и границы

Независимый reviewer перечитал все пункты применимых списков и исходные
критерии/комментарии #6986: pr-check-cutover **6/0**, required-proof-reuse
**6/0**, project-template **3/0**, всего **15 checked / 0 unchecked**.
Проверки требований отделены от реализации и живой приёмки; checkbox state
исполнитель не менял. FR-038–041/SC-019 и FR-056/SC-024 сохраняют прежние
связи с задачами. Новых требований, CRITICAL/HIGH противоречий или новых
обязательных реализаций в этом документальном остатке не выявлено.

Исторический #6991 действительно исполнил старый YAML. Восстановленные
checks подтверждают его прежнюю политику, но не новый workflow. Старый PR
повторно не редактировался. Современный #7779 подтвердил недостающую
postmerge ветку; plan T090 согласован с уже действующей release guidance.
Прежние foundation/cutover, T082/T083 и результаты опубликованного T094
не выданы за новые исполнения и не переотмечаются.

Дополнительно общий live verifier повторно подтвердил cutover #6990:
head `2557bcebe428a7c469508ab1247dc312fbfb7b43`, checked base
`1592a7f750b96c36c5a120795fda6018031c4c7f`, merge
`829074ea8e931744f960aa21625d7165201c9072`, source
34780847563/34780847611 и metadata34888231789, attempt1. Старый PR
не редактировался; его исходные тесты не перезапускались.

T063/T087 завершены в указанной области A6. Для закрытия #6986 ещё нужны
принятие этой документальной сверки с её собственными точными SHA/base checks
и отдельная содержательная/live проверка закрытия. PR #7779 сам #6986
не закрывает. Общая F211, T077/A9, приёмка Apple, merge queue, новые Full,
выпуск, production и установленный GRAF Dev в эту сверку не входят.
