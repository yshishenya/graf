# F290: повторное независимое ревью текущего CI-среза

Дата: 2026-10-19. Reviewer: `review_f290_infra`.
Рабочая копия: `post-release-hardening/crisp`, ветка
`290-post-release-hardening`. Исходная основа и HEAD:
`c6c5441c930b8c1ecffed6de9b80773aa0e757e5`.
Режим: **high-risk-product**, инфраструктура и доказательства проверок.

## Решение

**APPROVE текущих локальных изменений первого CI-среза; новых замечаний
к изменённому коду: 0.** Это повторное чтение реализации и проверка свежих
доказательств, а не перенос прежнего APPROVE без проверки.

Оба списка после изменения перечитаны: **requirements 6 checked / 0 unchecked;
infra 13 checked / 0 unchecked**. Сохранены прежние отметки качества требований;
новых заявлений о выполнении hosted/production или всей F290 не добавлено.

Закоммиченные изменения в этой проверке не создавались. Реальная сборка
Apple Swift, XCTest/ContractValidation и три текущих PR-проверки
`governance-fast`, `macos-pr`, `pr-metadata` по точному будущему SHA остаются
воротами T005. Слияния по текущему поручению удерживаются до отдельной живой
приёмки F280; этот отчёт не меняет это ограничение.

## Прочитанная область и происхождение доказательств

Проверены `.specify/feature.json`, текущая ветка/HEAD/состав diff; активная
F290, исходная основа и owned paths согласованы. В индексе Git изменений нет.
Прочитаны все **17** исходных Markdown-документов F290, включая spec, plan,
tasks, quickstart, оба checklist, исследования stash/US3 и все предыдущие
независимые отчёты. Важные ограничения прежних исследований сохранены.

Применён навык `code-reviewer`. Учтены прочитанные AGENTS, guidance index,
spec-kit-flow, development-process, product-gates, release-and-validation,
конституция 7.1.0, продуктовый baseline и current-product-status; их ранее
прочитанные неизменённые источники сверены в этой проверке. В этой старой
основе нет отдельного `document-reading.md`, и её guidance index его
не требует. Новых правил проекта reviewer не добавлял.

Полностью прочитан diff **11** runtime/test-файлов и `F290.yaml`;
278 добавлений, 95 удалений в отслеживаемых файлах. Дополнительно прочитаны
окружающие scope/native/receipt шаги workflow, оба изменённых validator,
`ci-pr-scope.py`, применимые проверки `validate-pr-checks.py`, политика PR,
модель readiness, действующие post-deploy маркеры CD и места вызова
failure/cleanup в normalization service. Новые ветки исполнения продукта
этот срез не добавляет.

Свежий внешний реестр:
`/Users/yshishenya/Documents/Codex/2026-10-19/f290-current-preflight/`.
В момент проверки **29/29** файлов совпали с `baseline-files.json`:
17 документов, 11 runtime/test-файлов и fragment. Все 12 файлов реализации
и fragment также совпали с ранее независимо рассмотренными байтами.
После этого reviewer менял только два принадлежащих ему checklist и этот
новый отчёт; исходная реализация, spec/plan/tasks и прежние отчёты сохранены.

## Текущие результаты проверок

Reviewer не запускал тесты, приложения, сборки, Docker, SSH или серверные
команды. Ниже — независимая проверка сохранённых свежих результатов
основного агента: разобраны XML, числа уникальных сценариев и терминальные
строки журналов; проверено совпадение проверяемых файлов с manifest.

| Набор | Свежий результат | Независимая сверка |
|---|---|---|
| governance + metadata | 172 PASS, pytest 59.60 s | XML: 172 уникальных testcases, 0 failures/errors/skipped; suite 59.593 s |
| CI/CD contracts | 103 PASS, pytest 18.75 s | XML: 103 уникальных testcases, 0 failures/errors/skipped; suite 18.682 s |
| Общий результат | **275 различных PASS** | Пересечений идентичностей testcases двух XML нет; прежние 34/6 сценариев входят в 172 и повторно не прибавлены |
| Workflow validators | оба self-test OK | Прочитаны свежие `governance-workflow-self-test.log`, `full-workflow-self-test.log` |
| Проектный процесс | PASS | `development-process.log`: agent-context, fragment, legacy-impact, development-process OK |
| Spec Kit | PASS | `spec-kit-governance.log`: bootstrap integrity + GRAF invariants OK |

Контрольные суммы свежих XML:

- `current-governance.xml`:
  `f85cef5ee1d7aea4bb448636ef3205e9dbd1cda2e2c01ad2cba6e499f061bac4`.
- `current-contracts.xml`:
  `0849acd373ce3d07e40cd09a1ac34561f520510f9a3d4cd759d1911c9ed93196`.

Старые результаты actionlint/ruff и изолированных US3 опытов не названы
новыми запусками. Статическое сравнение YAML и контрольные суммы reviewer
проверил заново. Текущий whitespace проверен `git diff --check`.

## Проверка реализации

Для всех шести Actions reviewer заново прочитал GitHub release ref и
`action.yml` по закреплённому commit: ref разрешается в ожидаемый commit,
`runs.using` — Node24, SHA256 `action.yml` совпадает со свежим
`current-action-pins.json`. Перечень commits совпадает с research.
Подмена blob SHA вместо commit и принудительный небезопасный Node flag
не используются.

Статическое сравнение разобранных YAML подтвердило: все **6/6** workflows
равны основе вне заявленных action pins, `archive:true`, отключения
автоматического package-manager cache, трёх native selector и изменения
key/restore-prefix Swift cache. События, права, trust refs, scope/concurrency,
required names, actual build/test commands, имена/пути/сроки артефактов и
SHA/base/run/attempt привязки сохранены.

`pr-metadata` по-прежнему использует доверенный `github.workflow_sha`,
`persist-credentials:false` и Python `-I`; код головы PR там не исполняется.
`ci-pr-scope.py` требует native для workflow/validator изменений, поэтому
T005 нельзя выполнить зелёным пропуском Swift job. Потребитель
`validate-pr-checks.py` по-прежнему проверяет exact head/base, текущий
run/attempt, имя/event/path workflow, required jobs и происхождение proof.
ZIP/name совместимость сохранена через `archive:true`; download не включает
пропуск распаковки или подавление digest mismatch. Node приложения 22.22.3
не изменён, автоматический npm cache явно выключен.

Три native selector имеют одинаковый SHA256 тела:
`c10d80f1c7b73a16ca65e0c777b50e9e4ed05f8a2845803878f18d7624ade365`.
Прочитанный shell проверяет обе исполнимые программы, завершение команд,
строгую semantic version 6.0.3 и неизменность developer/SDK до записи
`GITHUB_PATH`. Версия 6.0.31 не проходит. `DEVELOPER_DIR`, `SDKROOT`,
`TOOLCHAINS` и `xcode-select --switch` не назначаются. Ключ и restore-prefix
содержат `xcode16.2`, поэтому прежний Swift.org cache не используется.
Регрессии исполняют shell из YAML с подменой только платформенных путей;
это обоснованная проверка отказов, но не реальная компиляция Apple Swift.

Оба validator теперь отвергают один неверный pin среди остальных верных;
отрицательные сценарии проверяют v4, v99 и нулевой SHA. Прежние обязательные
проверки не убраны. Full workflow сохраняет резервирование кандидата,
обязательное успешное завершение всех частей и точное покрытие shard union.

## Основания по всем пунктам

Пункты R01–R06 ниже соответствуют порядку шести строк requirements.md;
CHK001–CHK013 — точным идентификаторам infra.md. Каждый итог относится
к качеству и полноте требований, а не к закрытию одноимённой работы.

| Пункт | Итог | Текущее основание и предел |
|---|---|---|
| R01 | Сохранить [x] | spec FR001/SC004, US1–US3 и T001–T013 сохраняют все три результата #6501; конфликт с уже принятой F238 отделён. |
| R02 | Сохранить [x] | У трёх историй собственные критерии; plan/tasks выделяют независимый первый CI-срез. US2/US3 не объявлены завершёнными. |
| R03 | Сохранить [x] | FR/SC измеримы; неверный toolchain останавливается, not-run не pass; US3 описывает пределы/cleanup и честные blocked результаты. |
| R04 | Сохранить [x] | FR010, plan и T004/T005/T011–T013 различают commit/merge/release/production. Текущее разрешение человека не отменяется старой формулировкой о запросе разрешения; reviewer нового запроса не создаёт. |
| R05 | Сохранить [x] | NEEDS CLARIFICATION нет; stash и живой synthetic executor явно исследовательские задачи, обнаруженные SE01/SE02 не скрыты. Это не допуск реализации неизвестного. |
| R06 | Сохранить [x] | SC001–004, tasks и validation сохраняют исходную приёмку; локальный PASS не закрывает hosted/US2/US3/closeout. |
| CHK001 | Сохранить [x] | spec/tasks и новые исследования сохраняют CI, stash и четыре результата; F238/F290 не смешаны. |
| CHK002 | Сохранить [x] | research и свежая независимая ref→commit→action.yml сверка шести Node24 pins; npm cache/ZIP/download контракт учтён. |
| CHK003 | Сохранить [x] | FR003; все 6 YAML сравнены с основой; прочитанные scope/receipt consumers сохраняют trust/SHA/base/run/attempt и обязательные jobs. |
| CHK004 | Сохранить [x] | FR004/research/plan отличают semantic 6.0.3 от compiler build и SDK; новый key и restore-prefix отделяют Apple compiler cache. Hosted compile остаётся T005. |
| CHK005 | Сохранить [x] | Actual selector и 33 параметризованных shell сценария плюс Actions contract входят в свежие 172 PASS; отсутствие/неверная версия/nonzero/SDK/developer drift прекращают запись GITHUB_PATH. |
| CHK006 | Сохранить [x] | T004/T005/T012, validation и этот отчёт разделяют локальные 275 PASS, hosted Swift, PR merge и frozen release. |
| CHK007 | Сохранить [x] | research/plan/T005/fragment сохраняют retirement macos-14 2026-11-02 и brownouts; миграция image отдельно, долгосрочная готовность не заявлена. |
| CHK008 | Сохранить [x] | FR005, stash-disposition и T006–T008 требуют base/index/untracked и сверку чужих пяти файлов; старое наблюдение не объявлено текущей сохранностью. |
| CHK009 | Сохранить [x] | FR006/quickstart/T007–T008 сохраняют failure/concurrency/protected copy/restore/отдельное решение удаления; last30 не подменяет 14days+weekly. Реальная приёмка ещё не выполнена. |
| CHK010 | Сохранить [x] | FR007/data-model/procedures; четыре отдельных результата, normalization_cleanup_result→cleanup_result. Прочитанная модель требует все девять pass, а не только четыре US3. |
| CHK011 | Сохранить [x] | FR008 и процедуры задают synthetic ownership/объёмы/TTL/deadlines; inventory прямо обозначен записью, production выделен в T011, отсутствующий безопасный исполнитель — PD01. |
| CHK012 | Сохранить [x] | FR009 и прочитанные 17 документов используют безопасные метаданные/digests; новые private diff/audio/credentials не добавлены. Сервер reviewer не читал. |
| CHK013 | Сохранить [x] | T001–T013 задают review/analyze/sync→validation→применимые разрешения→closeout; новые службы/API/зависимости/обходы не добавлены. Нужные дальнейшие задачи остаются открыты. |

## Остаток и условия переноса решения

Изолированные исследования US3 сохранили один PASS адресного отказа и два
нарушения безопасных инвариантов SE01/SE02. Прочитанные текущие service callers
по-прежнему пишут failure по job_id и запускают job-wide cleanup; эти причины
не исправлены CI YAML. Их проверенное исправление/приёмка F291 и безопасный
исполнитель нужны до полной US3 приёмки. SE03 не превращён в доказанный баг.
Результат 133 прежних тестов, Linux FFmpeg capability, read-only SELECT или
здоровый worker не заменяют четыре живых результата. CD по-прежнему печатает
`required_post_deploy`; модель readiness сохраняет девять обязательных pass.

Учёт stash — сохранённое наблюдение 16–17 октября и решение retain,
не новая инвентаризация/перенос/удаление или принятая ротация. T006–T008
не переотмечены reviewer; чужой backup workflow нельзя перезаписать при
будущем совмещении. T009–T011, #6501 и #7646 остаются открытыми.

После переноса ветки на текущий master этот APPROVE не переносится
автоматически на новый diff. Особенно важно сохранить уже принятые F263
календарные проверки в `apps/server/tests/contract/test_ci_cd_contract.py`,
повторно прочитать результат совмещения и выполнить относящийся к нему набор
проверок. Новые PR SHA/base требуют собственных текущих GitHub доказательств;
старые 103 contract PASS не доказывают ещё не полученный объединённый файл.
При переходе за срок macos-14 сначала уточнить и проверить миграцию image.

Reviewer изменил только два reviewer-owned checklist и этот отчёт. Код,
spec/plan/tasks, старые отчёты, Git index/commits, GitHub, приложения, stash,
сервер и production не менялись.
