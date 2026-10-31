# F290/T016 — независимая проверка требований, 31.10.2026

Результат: **SCOPED REQUIREMENTS PASS**. Открытые замечания: CRITICAL 0,
HIGH 0, P1 0, P2 0. Режим работы — независимая проверка требований активного
среза Spec Kit; область реализации относится к инфраструктуре повышенного риска.
Разрешённая запись ограничена двумя контрольными списками и этим отчётом.

Ветка `codex/290-restore-access-preflight`, исходный HEAD
`837594c9c2b61d440a64efd89970695050b768b3`. Активная F290/T016 подтверждена
локальным `.specify/feature.json`, веткой и tasks.md. Содержимое локальных
документов проверено независимо от Git SHA, с учётом незакоммиченных уточнений.

## Предмет и доказательства

Полностью прочитаны AGENTS.md, карта инструкций, document-reading.md,
spec-kit-flow.md, release-and-validation.md, product-gates.md, конституция
7.1.0, spec/plan/tasks/quickstart/research/data-model F290 и оба контрольных
списка. Прочитан весь backup-restore-rehearsal.yml, изменения документов и
существующий образец исполнения настоящего YAML Bash в governance-тестах.
Продукт, БД, сервер, установленное приложение и внешнее состояние не проверялись.

В workflow четыре обязательных параметра: `PROD_SSH_HOST`, `PROD_SSH_USER`,
`PROD_SSH_KEY`, `PROD_SSH_KNOWN_HOSTS`. Существующий шаг `Require production
host access` при отсутствии любого из них сохраняет список имён и ручную
подсказку, но ошибочно печатает `restore_rehearsal_schedule_result=skipped`
и возвращает 0. Шаги настройки SSH и запуска проверки восстановления не
содержат `if: always()` или `continue-on-error`; обычное условие успеха
GitHub Actions уже позволяет остановить их одним ранним ненулевым отказом.
Нового выходного параметра, шага, флага или сервиса для этого не требуется.

Проверены безопасные фрагменты исходного журнала run40296980179,
job121485302736: при четырёх пустых параметрах ранний шаг напечатал skipped,
следующий создал неполную SSH-конфигурацию, команда запуска проверки затем
отказала при разборе конфигурации с причиной `backup_reference_discovery_failed`.
Это отказ до получения резервной копии и её восстановления. Сам шаг запуска
команды выполнялся; успешная SSH-сессия или настоящее восстановление этим
журналом не подтверждаются.

Журнал `graf-restore-direct.log`, SHA-256
`4079a1465484ced2f05a7815499d6f55addc74666ac0bfee356e670ebff67392`.
Переданный `restore-access-causal-red.json`, SHA-256
`1e4477810484256d9672a63f4d7166d4735977b685ad3105f44f7dcdc88f47ee`,
содержит четыре одиночных пропуска с фактическим exit0 вместо ожидаемого exit1
и один полный синтетический набор с exit0/configured. Вывод согласуется с
прочитанным Bash. Reviewer не повторял эти пробы и не принимает этот JSON
за окончательную проверку будущего исправления. Полностью пустой набор
подтверждён исходным журналом; новая проверка должна исполнить все шесть
случаев на окончательном коде.

## Инфраструктурный список — основания по каждому пункту

| Пункт | Основание сохранённой отметки требований |
| --- | --- |
| CHK001 | FR001, три пользовательские истории и SC004 сохраняют полный объём #6501, различие F238/F290 и отдельное закрытие. FR012 ничего из него не удаляет. |
| CHK002 | FR002 и research задают точные commit pins, Node24 и ограничения совместимости major; T016 не меняет действия. Это требования, не новая проверка upstream-версий. |
| CHK003 | FR003/010, план и T016 сохраняют trust, permissions, required names, source/base/run/attempt и три обязательные PR-проверки. |
| CHK004 | FR004, research и план различают semantic version Swift6.0.3, compiler build, SDK и новый namespace кэша; T016 их не затрагивает. |
| CHK005 | US1.3, FR004, план и quickstart требуют отказа до изменения GITHUB_PATH при неверном выборе/ошибке команды; SSH-уточнение не меняет этот путь. |
| CHK006 | FR010, SC001 и quickstart различают локальные пробы, настоящие GitHub проверки, merge и release. Новый ранний отказ не объявляется restore PASS. |
| CHK007 | Edge case, research и план сохраняют macos14 retirement 02.11.2026 и отдельную миграцию image. Исторический план не принимается как новая проверка текущего runner. |
| CHK008 | FR005, план и T006/T007 требуют immutable stash, index/untracked и сопоставления чужих пяти файлов до переноса. |
| CHK009 | FR006, quickstart US2 и T008 содержат ошибки записи/удаления/диска, конкуренцию, защищённую последнюю копию, restore и отдельную границу удаления. |
| CHK010 | FR007, SC003, research, data-model и T009–T011 сохраняют четыре независимых результата и mapping normalization_cleanup_result → cleanup_result. |
| CHK011 | FR008, план и quickstart запрещают считать пишущий inventory чтением, требуют синтетику и отдельную готовую процедуру production. T016 запрещает SSH/production/restore. |
| CHK012 | FR009/012, plan/quickstart требуют только метаданные и имена отсутствующих параметров; реальные и синтетические значения не должны попасть в stdout/stderr/summary. |
| CHK013 | FR010/011 и T016 задают порядок checklist → analyze → issue sync → causal RED/GREEN → review/converge → три exact-SHA/base gates, без новых служб/обходов. |
| CHK014 | FR012, приложение плана, T016 и quickstart согласованно требуют blocked/exit1 при любом пропуске, прежний успех/summary/подсказку, нормальные условия следующих шагов и шесть случаев настоящего Bash на безопасном окружении. |

Исходные тринадцать пунктов и их исторические примечания сохранены. Их отметки
подтверждают ясность соответствующих требований, без нового заявления об
исполнении US2/US3. Новый CHK014 отмечен только после проверки всех связанных
документов и существующего Bash.

## Общий список требований — основания по каждому пункту

| Пункт | Основание |
| --- | --- |
| 1. Полный объём и F238 | FR001/SC004, все три истории, T006–T013 и прямое исключение FR012 сохраняют исходные результаты и конфликт номера. |
| 2. Независимые истории и CI-срез | Для каждой истории есть свой Independent Test; T016 ограничена ранним отказом CI и не зависит от реализации US2/US3. |
| 3. Измеримость и честные ошибки | FR012 задаёт наблюдаемые status/reason/exit и имена; план/quickstart задают пять отказов, один успех и отсутствие значений в трёх каналах вывода. |
| 4. Полномочия | FR010, plan/tasks и действующее общее разрешение на Git сохраняют проверки перед commit/merge; production, выпуск и удаление сохранённой работы имеют отдельные границы. Reviewer эти действия не выполняет. |
| 5. Уточнения и неизвестные факты | Уточнение 31.10 однозначно; неизвестные stash/server факты остаются T006/T009–T011. Для маленького CI-среза они не подменены предположениями. |
| 6. Границы готовности | SC001–004, T012/T013 и FR012 прямо запрещают общее закрытие после одного CI-исправления; F291/#7734 также исключена. |

## Итог и оставшиеся ворота

Оба списка после записи перечитаны целиком: infra **14 checked / 0 unchecked**,
requirements **6 checked / 0 unchecked**, вместе **20 checked / 0 unchecked**.
Необоснованных новых отметок и блокирующих требований не найдено.

Этот результат допускает дальнейшие подготовительные ворота T016. До кода
основной агент ещё обязан завершить scoped analyze и issue sync; затем нужны
причинные RED/GREEN настоящего Bash, весь профиль workflow-тестов, actionlint,
проверки процесса/фрагмента/whitespace, независимое итоговое ревью и converge.
Перед слиянием обязательны новые governance-fast, macos-pr и pr-metadata одного
точного PR SHA/основы через общий validate-pr-checks.py.

Исправления кода на момент этого ревью ещё нет. Reviewer не запускал тесты,
Bash-пробы, CI, сеть, SSH, backup/restore, приложение, БД или production и не
менял Git/GitHub. T006–T013, #6501/#7646 и F291/#7734 остаются открытыми.

## Контрольные суммы прочитанных источников и списков

| Файл | SHA-256 |
| --- | --- |
| `AGENTS.md` | `24c0767f2223bb21e969079ec1ec09e0dec7c3fd3d85d02e78832f17e0775958` |
| `.specify/memory/constitution.md` | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| `docs/agent-guidance/README.md` | `2f3e0339a89d3ccdf0878026920955a189584d6a985116b069584cd78b3c75bb` |
| `docs/agent-guidance/document-reading.md` | `5263860b1974df022826ac81c2482e6ee92100bc0bb718ab5a29b32e2422e411` |
| `docs/agent-guidance/spec-kit-flow.md` | `afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e` |
| `docs/agent-guidance/release-and-validation.md` | `ff0d996c95101d5f782259661131db1b7528b3bf58991603f5652092e1e5256f` |
| `docs/agent-guidance/product-gates.md` | `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5` |
| `specs/290-post-release-hardening/spec.md` | `7ad5555a100954b0d8c3c6ab8f2faa00334a1873a2241d6ac7812cbe7bc5ba31` |
| `specs/290-post-release-hardening/plan.md` | `b9938439ba8b8cd02f198ac95190a53d6399466f8070fa0604eaf488d0a591f3` |
| `specs/290-post-release-hardening/tasks.md` | `7145af9a966e09f5647427863e5e0c29d9698aed71223b529816e900dd92dce6` |
| `specs/290-post-release-hardening/quickstart.md` | `f16eddebb44e5a50b4dd2d896ad005bfb623c1cb63425c0db221796adf956906` |
| `specs/290-post-release-hardening/research.md` | `a6bec8f55ff23b876fe93e74a9b6ce8ee5f33b2d4bcf9669e70add8fab7179ed` |
| `specs/290-post-release-hardening/data-model.md` | `ea2ad0764fef4e57c9324459a5e2bf1726d3ddd3e678dddcac08580f797e8468` |
| `.github/workflows/backup-restore-rehearsal.yml` | `d7700b914ab4c6b62b892f77f3469058aff41134a0773d8c31e1cc0af22db44b` |
| `tests/governance/test_governance_workflow.py` | `d81cb9e6874bafa2214a8d47059fc1386df4b1a819c168c12527473f111ce6a4` |
| `specs/290-post-release-hardening/checklists/infra.md` | `a6ac06043477f231768f71615a77f68703ddeee78c8f7c973dbb2336be2835b2` |
| `specs/290-post-release-hardening/checklists/requirements.md` | `2e33bf8075658a265ae1f0d246c759d0051a7b5f06353b2cec0a6040c3b101fe` |
