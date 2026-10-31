# F211/A14: поддерживаемый исполнитель macOS

Дата: 2026-10-31. Ветка: `codex/211-macos-runner-migration`.
Исходная основа: `686e4bb59aae093c03839c80438e93076f9f824d`.
Область: #7834, T105/T106, FR038/059/060, SC026.
Полоса: существующий срез Spec Kit, инфраструктура CI.

## Проверка требований и анализ до реализации

Независимый reviewer: `checklists/runner-image.md`, 5/0 PASS.
Уточнение FR060 отделило primary key с хешами от restore prefix без них.
Ограниченный analyze A14: CRITICAL 0, HIGH 0; нет блокирующей неоднозначности.
FR038/059/060 покрываются T105, SC026 — T105/T106. Все четыре требования
имеют задачи; T106 зависит от T105. Конституция V/VI: публичная подпись,
доверие и обязательные проверки сохраняются. Другие задачи F211 не принимаются.
Существующая issue #7834 сверена по содержимому, task links и feature:211;
добавлены type:hardening и gate:pr-blocker, дубликат не создан.

## Причинная проверка

Исполнен настоящий shell selector каждого из трёх YAML; подменены только
платформенные пути/ответы, приложение и системный Xcode не менялись.
До исправления: **27 FAILED / 42 PASSED** из 69 сценариев
(`/tmp/f211-runner-red-20261031.log`). Новые отказы обнаружили пропущенные
проверки архитектуры, job env, developer path, принадлежности/версии SDK и её
смены. Старые отрицательные сценарии сохранены.
Дополнительно до исправления: три проверки образа/среды и два контракта
cache/diagnostic завершились ожидаемым FAIL на macos14/старом namespace.

## Реализация

Три задания используют macos15 и job-level DEVELOPER_DIR Xcode16.2.
Selector сохраняет оба executable/version/error checks Swift6.0.3, проверяет
arm64, developer, SDK15.2 внутри выбранного Xcode и неизменность среды.
GITHUB_PATH дописывается только после полного успеха. Оба Swift cache keys
и restore prefix согласованы и содержат macos15. Новый helper/зависимость,
sudo или системное переключение Xcode не вводились.

## Локальные результаты

- `/Users/yshishenya/Documents/crisp/apps/server/.venv/bin/python -m pytest -q tests/governance/test_governance_workflow.py apps/server/tests/contract/test_ci_cd_contract.py`:
  **365 PASS**, 129.76s; один PytestAssertRewriteWarning о заранее загруженном
  модуле fixture, отказов/пропусков нет. Включены 69 actual-shell сценариев
  и 3 проверки job image/env.
- `python3 scripts/validate-full-ci-workflow.py --self-test`: PASS, включая
  отклонение прежнего macos14; валидатор текущего workflow: PASS.
- `actionlint` трёх изменённых workflows: PASS.
- Ruff трёх изменённых Python-файлов: PASS.
- `check-development-process.py`, `check_spec_kit_governance.py`,
  `validate-changelog-fragments.py`, `git diff --check`: PASS.

## Независимое ревью, сходимость и внешняя приёмка

Независимое ревью реализации: SCOPED PASS, P1/P2 и CRITICAL/HIGH0;
`review-runner-implementation-20261031.md`. Scoped convergence A14: текущие
source соответствуют FR038/059/060; новые обязательные задачи не обнаружены.
T105 принята локально, T106 остаётся открытой до настоящего native
GitHub job, всех трёх exact head/base checks, защищённого merge и live closeout.
Локальные подмены среды не доказывают настоящий compiler GitHub.

## Границы

Продукт, GRAF Dev, установленная совместимость macOS14, Windows/F200,
публичная подпись/нотаризация, production и выпуск не проверялись/не менялись.
Новый release-full не запускался: будущий замороженный кандидат требует его
обычным единственным authoritative прогоном. F269/T031 и остальные открытые
задачи F211 не закрываются этим переходом. Legacy Impact: remove — активный
macos14 runner и совместимый с ним cache namespace заменены; fallback нет.


## T107: фактический отказ и уточнение объёма

Первый настоящий native run [41215353665](https://github.com/yshishenya/graf/actions/runs/41215353665)
на source `45f783a5a6789db03e3530194be92453c0a86974` подтвердил macos15 arm64,
Xcode16.2, Swift6.0.3 и SDK15.2, но завершился FAILURE при сборке.
Три protocol conformances WebKit не принимали callback types без
`@MainActor @Sendable`. Следовательно, прежние локальные 365 PASS сами
по себе не доказывали native готовность; этот failed run сохранён.

До исправления добавлены FR061/T107 и точная граница двух файлов; issue
#7834 обновлена без создания дубля. Независимая повторная проверка требований:
6/0 SCOPED PASS, `review-webkit-types-20261031.md`. Scoped analyze A14 после
этого дополнения: FR038/059/060 → T105, FR061 → T107, SC026 → T105/T107/T106;
5/5 требований покрыты, несвязанных задач 0, CRITICAL/HIGH/clarification gaps0.
T106 зависит от T105 и T107; публичная совместимость/доверие не меняются.
Анализ выполнен до source edit, режим analyze не менял файлы.

Исправление удаляет 17 строк двух старых условных ветвей, без добавления кода.
Существующие шесть MainActor/Sendable aliases и все тела/consumers сохранены.
Compilation проверяет conformance; дополнительная обвязка не требуется.
Deployment target macOS14 сохранён; сборка старым SDK14 не поддерживается.
Ручная/установленная приёмка macOS14 этим изменением не заявляется.

Локальная `swift build --package-path apps/macos --scratch-path /tmp/graf-f211-t107-swift`:
PASS,31.05s, Swift6.3.3/Xcode26.6/SDK26.5, arm64. Это другая среда;
точный Swift6.0.3/SDK15.2 должен пройти новый настоящий native run.
Существующие XCTest/ContractValidation и независимое implementation review
ещё выполняются; T107/T106 пока открыты. GRAF Dev не запускался.


### T107: завершённые местные проверки

Существующие команды `swift test ... list` и `swift test ... --skip-build`
с тем же временным scratch успешно завершены, `_SWIFTPM_SKIP_TESTS_LIST` снят.
XCTest: **1296 total = 1287 PASS + 9 SKIP,0 failures**,130.105s.
Семь skip сохраняют честный отказ среды подтвердить AppKit focus; два —
не запрошенные экспорты synthetic previews. Они не относятся к типам WebKit
и не объявлены установленной приёмкой. Все тесты/ожидания сохранены.
`swift run ... --skip-build ContractValidation`: **PASS**,exit0.
Native приложение не запускалось; сборка executable не является запуском.

Журналы и SHA256:
- build: `af892cf6faf379fcc8d8deccb9fcfc0a4b3d0caeeef455fd0414ca1f0f98458b`;
- discovery: `20ec30e4c6e40db1ff74ca2412574cb250bc2245ce03648beb999ff3e8d1cfa4`;
- XCTest: `820e2540674757a4f43c0d2ceba0c869faa1d2578030bc23c4d59701742c7175`;
- ContractValidation: `17189bd7192c0e37e850670a49ed6602566a183b4d772c368024c2674e389c87`.

Process/governance/changelog/diff PASS. Scoped convergence после T107:
5 требований A14,6 типов/14 declaration consumers и3 решения плана сверены;
missing/partial/contradicts/unrequested0. Новых задач не добавлено:
настоящее pinned native и exact-SHA/base/merge уже принадлежат T106.
Общая программа F211 вне этой приёмки. Before/after hosted proof не смешивается.


Независимый reviewer перечитал завершённые XCTest/ContractValidation logs,
подтвердил итог, причины9 SKIP и неизменные source hashes; окончательный
`review-webkit-implementation-20261031.md`: SCOPED PASS, P1/P2/HIGH/CRITICAL0.
T107 отмечена после этой проверки; T106 до нового hosted proof/merge открыта.


## Второе настоящее исполнение — отказ XCTest, 2026-10-31

[macos-pr41216963828](https://github.com/yshishenya/graf/actions/runs/41216963828),
source `7af2fb8fb14b217d6baa100ef5bf78484d579d4f`: WebKit успешно собран.
Полный XCTest исполнил1296 случаев,9 прежних skip,12 assertions failures
в4 случаях: три `DesktopNotificationProtectedConsumerTests` и
`testRealJavaScriptCancelAndKeyboardNeverRunProtectedAction`.
Governance41216963853 также завершился FAILURE, metadata41216990821 SUCCESS.
Body-only повтор native не исполнял и не заменяет отказ source run.
**T106 и #7834 остаются открытыми; слияние #7835 запрещено до PASS.**

Полный журнал сохранён вне исходников. Повтор обеих неизменных групп локально:
9 PASS/0 SKIP,8.967s; это иная среда, pinned отказ не опровергнут.
Обнаруженные предпосылки малого экрана, устаревшего AX после resize и document/
sheet readiness вынесены в FR062/063/T108 до изменения тестов. Product source
после T107 не меняется. Прежние assertions нельзя удалять ради зелёного CI.


### Анализ T108 до изменения тестов

Независимое requirements review: checklist7/0 PASS, отчёт
`review-ui-fixtures-20261031.md`. Scoped analyze после новых tasks:
FR038/059/060 → T105; FR061 → T107; FR062/063 → T108;
SC026 → T105/T107/T108/T106. 7/7 требований покрыты, несвязанных задач0;
CRITICAL/HIGH, неоднозначность и конфликт с конституцией0. Критерии не
сокращены; ограничения родительского A14 и исходных F277 controls сохраняются.
Issue7834 синхронизирована с T108 до реализации, дубликата нет.


### T108: причинные предпосылки и профильная проверка

До исправления исходная подготовка с viewport внутри настоящего экрана
не более1024×743 и явной проверкой свободного верхнего якоря дала:
**3 теста FAIL,9 assertions,0 unexpected**,7.474s. Все три новые проверки
исходного якоря отказали; также воспроизведены прежние отказы возврата рамки
и зазора. RED — `/tmp/f211-t108-anchor-red.log`; продуктовые source не менялись.

Исправление резервирует место для исходного окна слева, предъявляет длинную
карточку и двигает настоящее окно только по X. Рамки/нажатие Stop и marker
берутся из настоящих consumers, не подставляются. Deadline теперь задан
явно20s; проверка его сохранения больше не сравнивает nil с nil. Все исходные
assertions безопасности, accessibility, коллизии/8pt и lifecycle сохранены.

Новое наблюдение AX не предполагает фиксированный сдвиг центра: диагностика
подтвердила одновременное изменение ширины реальной кнопки180→140.5pt.
После обновлённых bounds нужно новое AX-дерево и отличная от старой рамка,
затем прежние полное покрытие и контроль нахождения Stop внутри окна.
Первое слишком жёсткое новое ожидание центра отказало; журнал сохранён,
продуктовый критерий ради него не менялся.

Confirmation ожидает URL, оба loading состояния и свободный sheet до каждого
запроса; затем видимый настоящий alert. Сохранены реальные Return/Escape,
false и защищённое действие. Кооперативное ограниченное ожидание30ms
освобождает MainActor; синхронный вложенный NSApp.run здесь блокировал WebKit
navigation и был исключён из подготовки. Продуктовые guards неизменны.

Окончательные обе группы после замечания R1: **9 PASS,0 SKIP/FAIL**,8.660s.
R1 закрыто: новое ожидание AX отвергает временно пустую рамку.
Полный повтор после R1: **1296 total,1287 PASS,9 SKIP,0 FAIL**,169.500s.
Все1296 unique discovery IDs совпали с terminal execution IDs; дублей0.
Семь прежних пропусков относятся к AppKit focus, два к optional preview export;
новых skip нет. ContractValidation: **PASS**.
Native/required checks точного нового SHA не получены; T106 открыта.

### Дополнительный отказ governance

Исходный governance41216963853:1800 PASS/2 SKIP/1 FAIL за644.77s.
Отказ `test_stopped_same_active_sigkill_and_exact_retry[after-permit]` связан
с retry worker и тестовым docker executable; полный traceback в кратком CI
выводе обрезан. Причина не установлена, исправление не заявляется.
Изолированный повтор того же случая на native Linux arm64/Python3.12.15 с
pytest8.4.2, Git и procps:1 PASS/10.77s. Источники и Git objects подключены
только для чтения, сеть использовалась лишь для временных test dependencies;
контейнер удалён автоматически, настоящий Dev/Docker services не менялись.
Первая проба на другом образе без ps остановилась при доказательстве PID и
не является воспроизведением CI-отказа. Новый полный governance обязателен;
существующие проверки восстановления не ослаблены и не менялись.


### Ограниченная итоговая сверка A14/T108

Полоса — active Spec Kit slice, без выпуска. Проверены FR038/059/060/061/062/063
и SC026 (7 требований), решения plan A14 о закреплённой среде/кэшах, сохранении
типов callback и подготовке двух UI-групп. FR062/063 покрыты фактическими
предпосылками/ожиданиями и всеми9 исходными тестами. Обязательные проверки
Stop/indicator,8pt, panel/deadline, lifecycle, Return/Escape и fail-closed
сохранены; продуктовый код T108 не меняется. Новых незапрошенных механизмов,
удалённых сценариев, ослаблений конституции и обязательных задач реализации0.
T106 уже содержит оставшуюся внешнюю проверку, поэтому новая задача не нужна.
Общая F211 и исторические условия других срезов этой сверкой не принимаются.

Окончательные SHA256 тестов:
- Consumers: `371220275bec0fae0cb5cd5f24bd2703672e82a4c7d703f0fee81caa40db5b62`.
- Confirm: `76796d2f25bd94ff8452cd60a0ab4007bf77049a80f1429a7e25717981901de0`.

Журналы финального профиля, полного XCTest и ContractValidation сохраняются
в закрытом локальном каталоге доказательств, вместе с хешами и discovery.
Первый полный прогон до R1 сохранён отдельно и не заменяет окончательный.

Независимое implementation review после окончательного полного прогона:
**SCOPED PASS**, R1 closed, открытых P1/P2/CRITICAL/HIGH0. Отчёт
`review-ui-fixtures-implementation-20261031.md`, SHA256
`7c3cd5bdec1729ad452df2046db850c7e4fd6f8cc2d6e1a1657024f22d13ca67`.
Reviewer повторно прочитал checklist:7 отмечено/0 не отмечено. T108 пока
остаётся открытой до полного закреплённого native вместе с T106; местная
приёмка не подставляется за CI.


### Третий закреплённый native — остаётся confirm

Run41220589209 на `dc4e97d1b6aeae5857796979d7028b54ca194e75`:
среда и WebKit compilation приняты, все три настоящих consumer tests PASS.
Всего1296 XCTest,9 skip,3 failures/1 unexpected в одном случае:
`testRealJavaScriptCancelAndKeyboardNeverRunProtectedAction` — после готовой
навигации диалог не появился для Return, completion остался не получен.
Это не PASS T108/T106. Точная причина ещё не доказана.

Следующая ограниченная проверка T108: до confirm проверить настоящий
`document.readyState` через выполненный JavaScript callback и ObjC selector
реального coordinator. Пустой loading флаг не доказывает готовность JS realm.
При отказе записать видимость/Space/key/loading состояния; критерий настоящего
диалога, Return/Escape/false не менять, прокси делегата в принятом тесте нет.
Это проверка предпосылки, не заявление об устранении корня отказа.

Дополнение JavaScript readiness: независимый scoped review PASS,
`review-js-readiness-20261031.md` (SHA256
`6ccccff8229e08bd4e576adfd285d526e7eff17153d1fafbbccc861f64374a95`).
Окончательный локальный source SHA256 confirm test:
`2e6e3043b5228f7590bb8ac45a44568dcaa40d3f16313c3737072735b50b338e`.
Профиль6PASS/0SKIP/0FAIL,7.090s. Полный новый повтор после этих строк:
1296 total/1287PASS/9прежнихSKIP/0FAIL,172.441s; все1296 discovery IDs
совпали с execution без дублей. ContractValidation PASS. Новый pinned CI
ещё обязателен; причина прежнего отказа не объявлена доказанной.


### Четвёртый закреплённый native: причина optional confirm

Run41222159260 на `9b3edf7351b1421bac821db04b061a71891057c8` завершился
FAIL:1296 XCTest,9 прежних skip,4 failures/1 unexpected в том же confirm case.
Новая проверка selector на строке71 дала false; document.readyState прошёл,
window visible=true/space=true/key=false, оба loading=false.
Все три protected consumer cases вновь PASS.

Compiler warning содержит точный expected optional WKUIDelegate callback:
`@escaping @Sendable (Bool) -> Void`, текущий тип
`@MainActor @Sendable (Bool) -> Void` не соответствует ему. Метод только
почти совпадает с необязательным requirement, поэтому не получает ObjC selector.
Отсутствие настоящего confirm здесь не исправляется дальнейшим ожиданием.
Предыдущая гипотеза JS readiness оказалась недостаточной; её локальный PASS
не выдан за устранение причины.

T108 не меняет продуктовый код: новое владение FR064/T109 определено до
исправления. Требования используют стандартный async requirement вместо
callback-overload и удаляют неиспользуемый confirm alias; implementation
остановлена до независимого CHK008/analyze. T106/#7834/PR7835 открыты.
Журнал и краткий compiler/error excerpt сохранены отдельно; новые проверки
точного SHA/основы остаются обязательными.


### T109: анализ до изменения кода

Требования CHK008: независимый SCOPED PASS, весь checklist8/0; отчёт
`review-confirm-requirements-20261031.md`, SHA256
`cbe490ebe325ba2a29686e4d5f47fa36ce9a6ab07d1920e2abead7c7b21c6704`.
Read-only analyze A14 после FR064: FR038/059/060 → T105, FR061 → T107,
FR062/063 → T108, FR064 → T109, SC026 → T105/T107/T108/T109/T106.
Покрытие8/8 требований,5 связанных задач, неоднозначность/дубли/непривязанные
задачи/CRITICAL/HIGH0. FR064 явно определяет новое владение после product
failure, не ослабляет старые guards или тесты. T109 предшествует T106;
процесс согласован с конституцией. Состояние issue7834 обновлено до кода.


### T109: минимальное исправление и локальная проверка

Удалён только confirm alias и заменено одно объявление WKUIDelegate
стандартным async requirement. Он вызывает прежний request через
withCheckedContinuation; request/finish/cancel, guards, UUID и alert не меняются.
Diff продукта:9 удалённых/8 добавленных строк, новых helpers/ветвей0.

Профиль шести существующих confirm tests: **6 PASS/0 SKIP/0 FAIL,7.165s**.
Настоящие selector, JavaScript, alert и Return/Escape сохранены без правки
тестового файла. Исходный pinned selector=false остаётся причинным RED;
локальный PASS другой среды не заменяет новый Swift6.0.3/SDK15.2.
SHA256 продукта: `5c6b2f3cee584fa13765b00cfe27a17cbff2465eab615e85b373dbbd12fe96d2`.
Полный локальный XCTest/ContractValidation ещё выполняются; T109/T106 открыты.


Окончательный полный локальный T109: **1296 total/1287 PASS/9 прежних SKIP/
0 FAIL,165.567s**, exit0. Все1296 discovery IDs совпали с завершёнными
execution IDs; дублей, потерянных и лишних0. ContractValidation: PASS/exit0.
Профиль6 случаев и полный прогон не суммируются. Product source и confirm
test hash неизменны после профиля; новых skip нет. Process/governance/fragment/
diff PASS. GRAF Dev, выпуск и production не запускались.


### Итоговая сверка T109 перед новым PR CI

Независимое implementation review: SCOPED PASS, P1/P2/CRITICAL/HIGH0,
отчёт `review-confirm-implementation-20261031.md`, SHA256
`09dfa0981c8ad1bb3bffca9e388e1729ea8b4ec9d6f4f702ff0dc9e418124695`.
Reviewer подтвердил8/0 checklist, неизменные байты request/finish/cancel до
конца файла, обе ветви разрешения continuation и неизменные6 tests/9 skips.

Scoped converge A14 после T109:8 требований и4 решения текущего плана
(закреплённая среда/кэши, обязательные типы SDK, подготовка двух UI-групп,
стандартный async confirm) покрыты существующими T105/T107/T108/T109/T106.
missing/partial/contradicts/unrequested в реализации текущего дополнения0;
CRITICAL/HIGH0. Новых задач реализации0, tasks.md при converge не менялся.
Внешнее исполнение и защищённый merge уже принадлежат открытой T106;
T108/T109 также ждут закреплённого CI. Общая F211 не принимается.

Следующая основа837594c9c2b61d440a64efd89970695050b768b3 содержит только
принятый F140 test-only PR7837 относительно c9a85917307a4388d534c61bc98e036a18d1245e.
Перед отправкой требуется сверка после синхронизации и новые exact-SHA/base
проверки; старый governance41222159075 SUCCESS на9b3… не переносится на новый SHA.
