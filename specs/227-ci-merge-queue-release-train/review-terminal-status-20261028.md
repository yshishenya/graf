# Независимое предреализационное ревью F227 T014 — 28.10.2026

Результат: **PASS требований / APPROVE начала реализации T014**.
Проверяющий — отдельный агент; область `Active Spec Kit slice`, shared CI.
Основа: `908670770cffe1c3e26fd1212c2837bd1bfeb229`, ветка
`codex/227-terminal-receipt-status`. Неподтверждённых пунктов требований и
блокирующих замечаний: **0**. Реализация исправления ещё не принята.

Прочитаны все пункты двух существующих списков, spec/plan/tasks/quickstart,
clarifications, research, data-model, оба контракта и текущий датированный
анализ T014. Конституция и применимые инструкции прочитаны лично. Фактический
указатель и prerequisite-команда подтвердили F227/T014; исходная строка задачи
и её владелец сохранены. Полномочия ограничены двумя списками и этим отчётом.

## Обоснование требований

Независимо прочитан настоящий terminal step `governance-fast.yml`: он выбирает
явный или найденный локальный файл раньше проверки `job_status`; отказ задания
влияет только на создание fallback при отсутствии файла. Прочитан сохранённый
синтетический опыт `f227-terminal-existing-evidence-probe-20261028.json` из
операторского каталога проверки за 27.10.2026. Его SHA-256 workflow совпадает с
текущим файлом. Опыт показывает ложный receipt PASS при готовом локальном PASS
и известном `failure`/`cancelled`. Здесь опыт не повторялся и не выдаётся за
настоящий запуск или отмену GitHub.

Прочитан `emit-ci-receipt.py`: поля conclusion/cancellation/supersession уже
производятся из статуса выбранного evidence. Нет основания дублировать их в
локальном producer ради буквального исторического пути T014. Схема v1 допускает
эти поля, validator проверяет их согласованность. Новая схема не требуется.

Прочитаны применимые функции `validate-pr-checks.py`: фактические run и jobs
должны завершиться успешно; совпадение head/base/run/attempt проверяется
отдельно. Поэтому обнаруженная ошибка квитанции не доказывает обход merge или
release. Прочитан применимый участок `release-full.yml`: его receipt создаётся
после component/evidence gates и не использует ошибочную ветку выбора по
JOB_STATUS. Изменение этого workflow текущими требованиями не обосновано.

Из spec/plan/quickstart следует достаточная проверяемая матрица:

| Известное состояние задания | Локальные данные | Требуемый результат |
|---|---|---|
| success | passed | passed при сохранении существующих validator gates |
| failure | passed, явный или найденный файл | failed; исходный файл не перезаписывается |
| cancelled | passed, явный или найденный файл | cancelled; cancellation_state=cancelled; исходный файл не перезаписывается |
| success | любой допустимый non-success | исходный non-success сохраняется; повышения до PASS нет |
| любой | evidence отсутствует | успешная квитанция не допускается |
| неизвестное состояние | в том числе готовый passed | успешная квитанция не допускается |
| последующий отказ/отмена GitHub | квитанция уже сформирована | общий consumer отвергает фактический неуспех; ранний файл не доказывает окончательный успех |

Матрица должна исполнять настоящий YAML step и receipt CLI во временных
каталогах, проверять status/conclusion/cancellation/supersession, schema и
неизменность исходного файла. До изменения кода требуется исходный отказ.
Проверка только наличия строк YAML или успешный старый набор тестов этот
дефект не закрывает. Это требования к следующему шагу, а не заявленные здесь
результаты исполнения.

## Каждый пункт requirements.md

Номера ниже соответствуют порядку исходных 16 пунктов; новые пункты не созданы.

| № | Пункт | Основание сохранения `[x]` |
|---|---|---|
| 1 | Нет лишних деталей реализации | Spec задаёт наблюдаемые статусы/приоритет, неизменность входного evidence и существующую границу producer; пути уточняют соответствие T014, новая архитектура не навязывается. |
| 2 | Пользовательская ценность и безопасность выпуска | US2 и уточнение T014 запрещают выдавать известный неуспех за PASS; окончательные GitHub gates сохраняются. |
| 3 | Понятный язык | Причина, результат и ограничения описаны прямо; имена полей и GitHub статусов сохранены для точной проверки. |
| 4 | Обязательные разделы заполнены | Есть цель, три истории, сценарии, edge cases, FR/SC, допущения, границы и Legacy Impact. |
| 5 | Нет NEEDS CLARIFICATION | Таких маркеров нет; приоритет известных статусов и поздняя отмена определены в датированном уточнении. |
| 6 | Требования проверяемы и однозначны | US2.4 и приведённая матрица различают success/failure/cancelled/unknown, отсутствие evidence и локальный non-success. |
| 7 | Критерии измеримы | SC-001/002/003 задают совпадение SHA и отказ во всех отрицательных случаях; quickstart задаёт исполняемую матрицу. |
| 8 | Пользовательский результат не зависит от деталей технологии | Достоверный успех/отказ и отсутствие stale acceptance являются результатами; конкретный workflow указан как существующая граница интеграции. |
| 9 | Основные сценарии приёмки определены | US1–US3 содержат Given/When/Then; US2.4 отдельно описывает новый дефект и сохранение исходника. |
| 10 | Краевые случаи определены | Отсутствие evidence, unknown job status, superseded/stale, обнаруженный путь и более поздняя отмена описаны в spec/plan/quickstart. |
| 11 | Область ограничена | Только T014; шесть других открытых задач, native queue, protection, Full, выпуск/CD и frozen source вне изменения. |
| 12 | Зависимости и допущения выявлены | Существующие producer/consumer, GitHub SHA/base/attempt gates, последовательные слияния и отдельная native приёмка указаны явно. |
| 13 | FR имеют приёмку | Таблица анализа связывает 11 FR и 7 SC с 33 задачами; FR-004/006/SC-002 уточнены для T014. Покрытие не названо выполнением. |
| 14 | Истории покрывают главные потоки | US1 — identity, US2 — неуспех/устаревание, US3 — train; T014 остаётся внутри US2. |
| 15 | Измеримые результаты определены | Сохранена историческая трактовка этого пункта как качества измеримых требований SC, без утверждения о готовой системе. |
| 16 | Нет секретов или частных данных | Прочитанные требования содержат только метаданные и публичные ссылки; metadata-only запреты сохранены. |

Итого: **16 отмечено / 0 не отмечено**. Маркеры не менялись.

## Каждый пункт infra.md

Первые девять пунктов — исходные; последние четыре сохраняют номера CHK010–013.
Это качество требований, а не утверждение, что вся инфраструктура уже принята.

| № | Пункт | Основание сохранения `[x]` |
|---|---|---|
| 1 | Event-specific target/base | FR-001/002, US1, CIReceipt contract и EventIdentity различают PR/manual/merge-group и неизвестный target. |
| 2 | Fail-closed synthetic и связь PR | FR-003, C5 и T029/T031 требуют authoritative mapping; настоящий native rehearsal остаётся открытым. |
| 3 | Concurrency только своего target | FR-004, US2.3, R2 задают deterministic logical target и supersession. |
| 4 | Отмена/stale не удовлетворяют required check | FR-004/006, SC-002 и T014 задают приоритет известного неуспеха; поздний неуспех отдельно проверяется общим consumer. |
| 5 | Итоговая чистота после артефактов | FR-005, US2.2 и R3 сохраняют tracked/untracked gate и документированные metadata exceptions. |
| 6 | Только метаданные и schema validation | FR-006, CIReceipt contract, plan constraints и quickstart сохраняют schema/validator и запреты частного содержимого. |
| 7 | Synthetic и source различены | FR-007/011, C1/C6 и train contract запрещают подменять фактический source служебным SHA. |
| 8 | Один authoritative Full | FR-008, SC-004, C3 и train contract требуют один Full на неизменный candidate; текущий срез его не запускает. |
| 9 | Protection и активация — оператору | FR-009 и out-of-scope сохраняют отдельное включение после настоящей проверки; T014 GitHub protection не меняет. |
| CHK010 | Serial и будущая native приёмка различены | Уточнение применимости, FR-009, plan/quickstart явно оставляют T029/T031 открытыми. |
| CHK011 | Обязательная base→source и отказ до записи | FR-011, SC-007, train contract и data-model сохраняют существование всех commits и независимое base→actual source. |
| CHK012 | Fixture, PR и выпуск разделены | Plan/quickstart и новое уточнение T014 прямо отделяют синтетическое исполнение от реального GitHub run и выпуска. |
| CHK013 | Pinned Python matrix и её предел | Research R8 и quickstart называют v0.1.13, точный pin, Python3.9/3.12 и исторический run; новый CI GRAF не заявлен. |

Итого: **13 отмечено / 0 не отмечено**. Маркеры не менялись.

## Решение и ограничения

Требования T014 достаточно полны для минимального исправления существующего
terminal step. Указатель уже называет настоящий
`tests/governance/test_governance_workflow.py`; несовпадения пути нет.
Изменения принципов, зависимостей, схем, приложения и release-full не нужны.
Текущий анализ сохраняет CRITICAL 0 / HIGH 0 и прежний MEDIUM I1 трекера;
состояние трекера других задач это ревью не исправляет и не принимает.

Следующий этап: исходный отказ, минимальное исправление, профильные проверки
producer/consumer и независимое итоговое ревью. Затем обязательны три GitHub
проверки точного PR SHA/base и обычное защищённое слияние. Только последующая
индивидуальная live-проверка может разрешить закрытие #6221. T014 сейчас `[ ]`;
T015/T016/T028/T029/T030/T031 и umbrella #6207 сохраняются открытыми.

Продукт, Full CI, выпуск/CD, приложение и внешние состояния этим агентом не
запускались и не менялись. Проверка ограничена требованиями CI metadata;
продуктовые PRD/current-status не использованы как доказательство этой задачи.

## Прочитанные версии

Пути ниже относительны к корню рабочей копии. SHA-256 подтверждает содержимое,
а не реализацию. Полное чтение: инструкции, конституция и документы F227;
`release-and-validation.md` — применимый раздел строк1–170. Файлы исходников
использованы в названных выше применимых участках; `emit-ci-receipt.py` и схема
прочитаны полностью.

Контрольные суммы приведены ниже; оба checklist после добавления ссылки на
этот отчёт перечитаны, их конечные хеши переданы основному агенту отдельно.


```text
24c0767f2223bb21e969079ec1ec09e0dec7c3fd3d85d02e78832f17e0775958  AGENTS.md
2f3e0339a89d3ccdf0878026920955a189584d6a985116b069584cd78b3c75bb  docs/agent-guidance/README.md
5263860b1974df022826ac81c2482e6ee92100bc0bb718ab5a29b32e2422e411  docs/agent-guidance/document-reading.md
afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e  docs/agent-guidance/spec-kit-flow.md
9793de5e158283c2d37bdd2b47f0daf4d312a44fd6ffa37cc22ac47f7a0c3472  docs/agent-guidance/tracker-policy.md
d7d8c9cce8315c17efaa1da05ece80c2542ca01b966f81fb848580104b785e1d  docs/agent-guidance/codex-worktrees.md
ff0d996c95101d5f782259661131db1b7528b3bf58991603f5652092e1e5256f  docs/agent-guidance/release-and-validation.md
7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8  .specify/memory/constitution.md
f7b6201c83e96a506430559d2e4ddcf747badaece22e486f94dad55b250aadc2  .specify/feature.json
3f35c2dda86d65219f0c8a6d1606b90b8f0488cf531a24c411e14876bac2ba4a  specs/227-ci-merge-queue-release-train/spec.md
859aa5a270e772075b539360da172459c5ca31901658dee2d6ba5bc468903fa3  specs/227-ci-merge-queue-release-train/plan.md
850cc63e80538324fa736a90179557b5fc70aca6a8ef60d84839c14424f3898b  specs/227-ci-merge-queue-release-train/tasks.md
d5c44a5dd02dcd02a4b2a897a243d693fb448a77a607495947694e1fb5223624  specs/227-ci-merge-queue-release-train/quickstart.md
22b225b129de44649a0cdbf60706db0281800ce6323fe91032995b7b30b96a52  specs/227-ci-merge-queue-release-train/clarifications.md
b266d467d02a2017fd7b36e1b77af86d1d38a145ceab8d7382ae9a4b092112f8  specs/227-ci-merge-queue-release-train/research.md
cfca5ed769ef9cde11170a6f851e166710096cd0db14f928e989bc877c9860d3  specs/227-ci-merge-queue-release-train/data-model.md
2ed7fe32aab818f503ce35b8496e265769e462617758c5db21d09972ee4322d8  specs/227-ci-merge-queue-release-train/analysis-provenance-20261017.md
9e6146a8aa70bdfb55fc59f39ac167862afcfe3fa61f3909e6abcb2bb8c02092  specs/227-ci-merge-queue-release-train/contracts/ci-receipt.v1.md
b04a07030c32510dc25edb9a7fc2a1209c3979036ab8595c09a10fe29c9c9309  specs/227-ci-merge-queue-release-train/contracts/release-train.v1.md
4fef181fbe047060f46576789b491d6423e552241e8a7f599b3e86c6890f3e34  .github/workflows/governance-fast.yml
b009aa5c49f53dd5ee9b200cb88eec68f243b0a974b3e2e7aff50e71b568aac0  .github/workflows/release-full.yml
859b4b1b73ab9207636e4973c18f02c59ba27a52bc17e3cb9aeeff8bcdd1d647  scripts/emit-ci-receipt.py
3dadb1b84cfe45bbf4f06939981042ad2d1a0ff6aeb45928cf9e4a9ce0e3380e  scripts/validate-pr-checks.py
9043733082664d3d8f493c0820b2daf21e5ad1729923f7e11bf2739a9f8c6bce  infra/release/ci-receipt.schema.json
0013df390d6caac11393a4e9cc9053f819b28b6df28dfe379d2695674bd0fced  scripts/validate-ci-receipt.py
```

Сохранённый синтетический опыт: SHA-256 `23528b69886a203e1ab2c735853a8c4f2bb5766850c2f901076068699fddecab`.

## Итоговое независимое ревью реализации — 28.10.2026

Результат: **APPROVE локального исправления T014**, замечаний, требующих
исправления: **0**. Это отдельное итоговое назначение после предреализационного
PASS выше. Использован навык `code-reviewer`; проверена текущая рабочая версия
на той же основе `908670770cffe1c3e26fd1212c2837bd1bfeb229`.

Лично перечитаны изменённые tasks и весь `validation-terminal-20261028.md`,
fragment F227 и полный diff. Хеши spec/plan/quickstart/анализа, конституции и
применимых инструкций совпали с ранее полностью прочитанными версиями.
Оба списка перечитаны по пунктам, основания 16+13 пунктов выше сохраняются.

### Корректность и достаточность изменения

Производственное изменение — две строки существующего workflow: условие
создания terminal evidence включает `job_status != "success"`; reason правдиво
называет момент формирования. Известные failure/cancelled и unknown больше не
сохраняют готовый PASS. При success выбирается исходный локальный файл;
stale/cancelled/superseded/failed/ambiguous не повышаются до PASS. Если файла
нет, существующий fallback остаётся non-success.

Настоящий terminal step, CLI producer и оба validator исполнены новым тестом
на всех 56 сочетаниях. Проверяются также conclusion, cancellation/supersession,
cleanliness, identity SHA/base/PR/run/attempt, digest выбранного файла и
побайтовое сохранение исходного локального evidence. У теста собственные
временные каталоги и ограниченные subprocess timeouts. Новых зависимостей и
механизмов нет: hashlib — стандартная библиотека, PyYAML уже применяется в
существующем файле. Старые тесты не удалены; прежняя строковая проверка reason
приведена к новому точному тексту.

Самостоятельно выполнены только назначенные новые случаи и самопроверка:

```text
python3 -m pytest -q tests/governance/test_governance_workflow.py::test_actual_terminal_receipt_preserves_known_job_failure
56 passed in 7.61s
python3 scripts/validate-governance-workflow.py --self-test
governance-workflow self-test: OK
```

Лично прочитаны журналы и разобраны JUnit XML исполнителя. RED содержит ровно
56 уникальных случаев: 36 failed / 20 passed / 0 skipped. Ошибки включают
configured/discovered PASS при failure/cancelled/unknown. GREEN содержит
367 уникальных случаев: 367 passed / 0 failed / 0 skipped, 68.72 с по журналу.
Четыре SHA-256 совпали с авторским отчётом. Этот агент не повторял остальные
311 проверок; числа общего профиля подтверждены сохранёнными файлами.

Программно сопоставлены все task-строки с исходной основой: **33/33 ID,
описания и порядок сохранены**. Единственная смена маркера — T014 `[ ]` →
`[X]`. Итог: 27 выполненных / 6 открытых; открыты именно
T015/T016/T028/T029/T030/T031. Локальная отметка T014 сопровождается
каноническим владельцем #6221 и отдельным указанием ещё не пройденных PR/live
условий. Исторические записи оставлены историческими. Fragment отражает
исправление и границу поздней отмены без заявления о выпуске.

Побайтовое сравнение с основой подтвердило отсутствие изменений в
`emit-ci-evidence.py`, `emit-ci-receipt.py`, `validate-pr-checks.py`,
`validate-ci-receipt.py`, receipt schema и `release-full.yml`. Общий consumer
по-прежнему требует фактические успешные GitHub run/job и точные SHA/base/
attempt; поздняя ошибка не становится успехом по раннему receipt.
Metadata-only, exact-SHA, final-cleanliness и обязательные outcome gates не
ослаблены. Производственного обхода merge/release не заявляется.

### Предел решения и повторное чтение списков

Допустима локальная отметка T014 и подготовка PR. Слияние требует трёх
обязательных проверок точного нового SHA/base и окончания согласованного
соседнего окна без слияний. #6221 закрывается только после принятия и отдельной
live-проверки. Все остальные задачи F227, native queue, Full CI, выпуск и CD
этим ревью не принимаются. Git/GitHub-состояние, код и авторские документы
этим агентом не изменялись; изменены только два списка и этот отчёт.

После дополнения оба списка снова прочитаны целиком: requirements —
**16 отмечено / 0 не отмечено**, infra — **13 отмечено / 0 не отмечено**;
маркеры не менялись. `git diff --check` — PASS.

### Контрольные суммы итоговой реализации и доказательств

```text
191f01fc6837a7486f3ed6220b5cd6cc7e2d5966932678f5208686a87d54f0b5  .github/workflows/governance-fast.yml
d81cb9e6874bafa2214a8d47059fc1386df4b1a819c168c12527473f111ce6a4  tests/governance/test_governance_workflow.py
02758d7d6166eaf3b0d6840fa1e39534504d7fb27c44c661c6e2d977fe0b89d0  specs/227-ci-merge-queue-release-train/tasks.md
996e083c85802b807953e34adc1e0e8ee2be138355e77c666bf451c372fa009f  specs/227-ci-merge-queue-release-train/validation-terminal-20261028.md
f54368c303c4ff2a6703ffc6e8e5b7b66cd4d7b4f249fe633ce481ab19c3ad6b  changes/unreleased/F227.yaml
da1f72ade8ea2a9ba57efcfbc87a01912eef6c0af0e2040d39d6766177f8e98f  f227-terminal-red-20261028.log
a0fc576a6cd29e1faf3f11e8c41942c2315f80bd5353255b829b3ec2819a8615  f227-terminal-red-20261028.xml
c76d2412e886002a39f7dd4f619704d2a2295af43bedb445147bd5a6174c4b45  f227-terminal-green-20261028.log
fce54229bbea84f3dd03a22cb06a6ad10e90c029ad10f50f7378fffc5fb00223  f227-terminal-green-20261028.xml
```

Журналы/XML находятся во внешнем операторском каталоге проверки за 27.10.2026;
они подтверждают локальные синтетические проверки и не называются доказательством
реальной отмены GitHub, установленного приложения или выпуска.
