# F290: независимое ревью требований инфраструктуры

Дата: 2026-10-17. Reviewer: `review_f290_infra`.
Ветка: `290-post-release-hardening`.
Исходный SHA: `c6c5441c930b8c1ecffed6de9b80773aa0e757e5`.
Область: качество требований и согласованность артефактов до реализации.
Режим работы F290: **high-risk-product** (нормализованное проектное значение).
Это не приёмка исполнения.

## Итог

Чеклист перечитан после изменения: **13 checked / 0 unchecked**.
Неподтверждённых требований чеклиста нет. Дополнительный анализ текущих
документов: **CRITICAL 0 / HIGH 0 / MEDIUM 0 / LOW 0**.
Все 11 FR и четыре SC покрыты задачами; 13 уникальных задач, без пропусков
номеров и без задач вне требований.

Качество требований достаточно для первого CI-среза T002–T005 после завершения
оставшихся ворот T001. Фактическую синхронизацию GitHub issues и каноническую
task ownership связь основной агент проверяет отдельно; этот reviewer её live
результат не подтверждает.
US2/US3 пока подготовлены как ограниченные исследовательские этапы:
неизвестные серверные факты не являются разрешением на код или выполнение.
T006/T007 и T009/T010 требуют уточнения плана и независимого review до своих
изменений. Готовность всей F290 и закрытие #6501/#7646 не подтверждены.

## Доказательства по пунктам

| Пункт | Текущий источник | Почему требования достаточны |
|---|---|---|
| CHK001 | spec Clarifications, US1–US3, FR001, SC004; tasks T001–T013 | Сохранены runtime CI, судьба stash и четыре процедуры. F238/PR6504 явно отделены, первый срез не закрывает исходную задачу. |
| CHK002 | research Actions; plan Design; T002/T003 | Для шести действий есть stable version, full commit pin и Node24. Отдельно учтены trusted checkout, automatic npm cache, ZIP/name и digest mismatch. |
| CHK003 | FR003; plan Technical Context/Design; T003/T005 | Сохраняются события, permissions, required names, scope/concurrency, source/base/run/attempt, сроки хранения и формат receipts; текст не заменяет исполнение. |
| CHK004 | spec Clarifications/FR004; research Swift; plan Design | Semantic version 6.0.3 отделена от Apple compiler build и SDK. Новый key и restore-prefix предотвращают старый compiler cache; SDKROOT/DEVELOPER_DIR/xcode-select не меняются. |
| CHK005 | US1 acceptance 3; plan Validation Plan; quickstart Первый CI-срез | Указаны отсутствие обоих binary, 6.0.31/6.0.2, nonzero при правильном stdout, xcrun failure и SDK drift. GITHUB_PATH изменяется только после всех проверок. |
| CHK006 | SC001/FR010; plan Validation Plan; quickstart; T004/T005/T012 | Изолированный harness не считается Apple build. До merge обязательны три exact-SHA checks и настоящий native build; выпуск требует собственного frozen Full и разрешений. |
| CHK007 | spec Edge Cases; research Swift; plan Design; T005 | Зафиксировано отключение macos-14 2026-11-02 и временные отключения до даты. Новый image требует отдельного плана, нельзя молча менять compiler/SDK. |
| CHK008 | FR005; plan US2; data-model Stash disposition; T006/T007 | Требуются immutable OID, base/index/untracked, сопоставление с чужими пятью файлами и владельцем без apply/pop/drop до решения. |
| CHK009 | FR006; quickstart US2; T007/T008 | До переноса требуются failure/concurrency/protected-last-copy/path-escape/restore проверки. Удаление сохранённой работы требует отдельного разрешения после доказанного решения. |
| CHK010 | FR007; data-model Post-deploy result; research таблица; quickstart US3; T009–T011 | У каждого сценария отдельные факты/условия/source/time/owner; not-run не pass. normalization_cleanup сопоставлен с cleanup_result модели, ready требует четырёх pass. |
| CHK011 | FR008; plan US3; quickstart US3; T009–T011 | Синтетика и изолированный PostgreSQL предшествуют точной согласованной production процедуре. Inventory service прямо обозначен как пишущий; healthy worker и пустая выборка недостаточны. |
| CHK012 | FR009; data-model; quickstart US2; T001/T004/T006 | Разрешены метаданные и безопасные digests; запрещены секреты, приватный stash diff, аудио, транскрипты и содержимое встреч. |
| CHK013 | FR010/011; plan Constitution Check/Validation Plan; tasks Dependencies | Review/analyze/sync идут до кода, regression до изменения, commit после проверки/разрешения, merge/release/closeout раздельны. Новые службы, зависимости и обходы исключены. |

## Дополнительный анализ согласованности

Метод: `$speckit-analyze`, только чтение исходных артефактов. Прочитана
`.specify/extensions.yml`, YAML разобран: enabled before/after-analyze hooks — 0.
Штатный `check-prerequisites.sh --json --require-tasks --include-tasks` прошёл;
наличие spec проверено отдельно. В установленном script нет `--require-spec`,
поэтому неподдерживаемый аргумент из SKILL не использовался.

| Требование | Задачи | Покрытие |
|---|---|---|
| FR001 | T001, T013 | Полный исходный объём и исправление task ownership до кода/закрытия. |
| FR002 | T002, T003 | Исполнимые regression и обновление Actions. |
| FR003 | T002, T003, T005 | Сохранение contracts и настоящие PR proofs. |
| FR004 | T002, T003, T005 | Отказ selector, SDK guard, кэш и настоящая Apple сборка. |
| FR005 | T006, T007 | Инвентаризация до переноса. |
| FR006 | T007, T008 | Review решения, failure/restore проверки и отдельное удаление. |
| FR007 | T009, T010, T011 | Процедуры, изолированные проверки, разрешённое исполнение. |
| FR008 | T009, T010, T011 | Синтетика и запрет несогласованной записи. |
| FR009 | T001, T004, T006, T011 | Метаданные в отчётах, защищённая инвентаризация. |
| FR010 | T001, T004, T005, T012 | Процесс до кода, validation/approval и convergence/release gates. |
| FR011 | T003, T009 | Без служб, зависимостей, обходов и нового retry/backfill API. |
| SC001 | T005 | Три точные PR-проверки с настоящим native исполнением. |
| SC002 | T006, T007, T008 | 100% stash учтено, решения и сохранность проверены. |
| SC003 | T009, T010, T011 | Четыре доказанных результата/цикла. |
| SC004 | T012, T013 | Все результаты, convergence, live closeout и комментарии. |

Метрики: requirements 15; tasks 13; coverage **100%**; неоднозначности 0;
дублирующиеся требования 0; unmapped tasks 0; нарушений конституции 0.
Критерии всех трёх US имеют независимую приёмку, порядок зависимостей явный.
Для US2/US3 детализация до соответствующего кода обязательна, это не скрытый
пропуск неизвестных safety требований ради реализации.

При первом чтении найдено несовпадение имени fragment с проектным правилом:
`changes/unreleased/290-post-release-hardening.md` вместо `F290.yaml`.
Основной агент исправил plan/tasks/pointer; reviewer только перечитал их.
Повторная проверка подтверждает `changes/unreleased/F290.yaml` во всех трёх
местах, замечание устранено до итогового PASS.

## Прочитанные текущие источники и пределы

- AGENTS, guidance index, spec-kit-flow, release-and-validation, product-gates,
  продуктовый baseline и current-product-status; конституция **7.1.0**.
- `.specify/feature.json` и штатный prerequisites вывод: активная F290,
  перечисленные собственные пути и исходный SHA согласованы.
- spec, plan, research, data-model, quickstart, tasks и оба checklist F290.
- Ссылки Actions во всех шести существующих workflow и целевые native шаги
  macos-pr/release-full; `scripts/ci-pr-scope.py` подтверждает, что workflow/
  validator изменения не являются доказанно независимыми от native.
- `deployment.py` подтверждает cleanup_result и четырёхчастный ready gate;
  cd-remote-runtime пока печатает required_post_deploy для четырёх результатов.
- backup/restore scripts и `changes/unreleased/README.md`: используются
  существующие пути, canonical fragment — `F<feature-id>.yaml`.

Выполнялись только чтение, prerequisites и небольшая проверка структуры
документов/YAML. Сетевые Actions, product tests, сборки, SSH, production,
stash и GitHub state в этом review не исполнялись и не менялись. Upstream
источники перечислены в research; это не повторная проверка установленных
hosted binaries. Изменены только infra.md и этот reviewer report.

Следующий шаг: основной агент подтверждает issue sync/локальную ownership
связь T001 и читает итог checklist; затем выполняет минимальный regression/CI
этап T002–T004.
Новая проверка до исполнения US2/US3 обязательна. Полномочия на commit,
merge, выпуск, deploy или удаление stash этим отчётом не выдаются.
