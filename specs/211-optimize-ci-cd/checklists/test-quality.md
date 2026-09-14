# A12 — качество и порядок проверок

Reviewer-owned requirements gate; implementation must not edit checkboxes.

- [x] CHK001 CSRF проверяется действием и заголовками, с отрицательным контролем; серверные запреты и альтернативные случаи сохраняются. [FR-057/SC-025]
- [x] CHK002 Удаление ограничено ровно пятью доказанными дублями (1+1+3): default-CSRF config, скалярный cookie-name в integration и три forbidden-readiness случая в contract; соответствующие unit проверки с независимыми буквальными ожиданиями, все остальные assertions/параметры/fixtures сохраняются, новые регрессии считаются отдельно. [FR-057/SC-025]
- [x] CHK003 Новый порядок Full сохраняет изоляцию, состав/markers/workers/digest, обязательность performance и cleanup; fast/focused не меняются. [FR-058]
- [x] CHK004 Исполняемые проверки доказывают ранний отказ, сохранение результатов и окончательный Full учитывается отдельно. [SC-025]
- [x] CHK005 Обязательный runtime-role bootstrap proof получает отдельный function-scoped PostgreSQL cluster с прежними production names, реальными миграциями, уникальным контейнером/loopback портом и ограниченным ожиданием; collection не создаёт ресурсы, ошибки setup/bootstrap дают FAIL, cleanup действует и при ошибке. Только этот тест меняет fixture; shared роли/остальные тесты/порядок фаз не меняются. Приёмка включает media→bootstrap и прежние 69 strict/performance случаев без SKIP. [FR-057/SC-025, T088]
- [x] CHK006 Требования делают три существующих media-tool предусловия обязательными: отсутствие FFmpeg/FFprobe даёт FAIL, а private TestRec сохраняет первым пропуск без явно заданного каталога. Подготовка инструментов ограничена существующими Full/server-change шагами; работающий комплект не переустанавливается, неисправный инструмент или ошибка установки останавливают проверку. Заданы исполняемые отрицательные проверки настоящих entrypoints/shell-блоков, прежние 49+1 синтетических случаев без SKIP, отдельный учёт новых регрессий и неизменность production/runtime-container проверки. [FR-057/SC-025, E02, T089]


## Независимая проверка требований — 2026-09-13

**PASS, CHK001–004: 4/4.** Проверены требования A12 и соответствующие пути
кода; это не приёмка реализации и не результат запуска тестов. Lane: проверка
требований существующей high-risk F211, разрешённая запись reviewer evidence.
Основание: `codex/211-release-image-reuse`, HEAD
`1b51bea23f07e468fda7186ca088c51dd9825897` и текущие незакоммиченные требования.

- CHK001: FR-057 → T084 требует исполнить чтение meta-токена и настоящий
  `htmx:configRequest` из `cabinet.js`, проверить unsafe/safe методы, отсутствие
  токена, сохранение других headers и FAIL на комментариях без поведения.
  Прослежены регистрация и вызов события в HTMX, шаблон `base.html`, выбор
  static-assets файла через `ci-behavior-tests.py`, серверные auth dependencies
  и `test_cabinet_csrf.py`. Сохраняются missing/invalid/valid token, native
  session и PUT/DELETE calendar-context случаи.
- CHK002: тела `test_web_production_runtime_still_rejects_default_csrf_secret`
  и `test_production_rejects_default_dev_web_csrf_secret` совпадают по AST:
  один helper, вход и ожидаемая ошибка. FR-057/SC-025 и A12 plan ограничивают
  удаление одним дублем; web/non-web/file cases и независимые значения остаются.
  Уменьшение на один относится к config-коллекции; новые регрессионные случаи
  учитываются отдельно. Общий E05.04 шире этого ограниченного исправления.
- CHK003: FR-058 → T085 задаёт только Full `strict → performance → parallel`.
  Прочитаны runner, `run_server_tests` и все его вызовы в `ci-local.sh`, прямой
  вызов в `release-full.yml`, resource/collection hooks и RLS isolation helpers.
  Сохраняются три непересекающиеся группы, приоритет strict при двух markers,
  serial performance, прежние workers, изолированная БД и cleanup.
  Неизменность digest относится к перестановке фаз на одной и той же коллекции.
  Обязательный performance сохраняет `required` и существующий p95 ≤ 50 ms.
- CHK004: SC-025 → T085/T086 требует настоящий shell/pytest contract для
  успешного порядка, отказов ранних фаз и cleanup, затем реальную strict/
  performance группу. Сохранение результатов задано CHK004; существующие
  `run_phase`, metadata-only JSONL и `always()` upload дают конкретную границу
  проверки. Итоговый frozen-source Full и hosted evidence вынесены в T077.

Незакрытых пробелов полноты, противоречий конституции или потери обязательных
случаев в требованиях A12 не выявлено. Тесты, Full, Docker, GitHub и приложение
не запускались; T084–T086 этой отметкой не закрываются.


## PASS delta — уточнение CHK002 / E05.04 — 2026-09-13

**PASS по полноте уточнённых требований FR-057/SC-025 → A12 plan → T084.**
Точный объём удаления — 1+1+3 = 5 случаев. Это новая независимая проверка
требований; выполнение T084, удаление дополнительных дублей и результаты тестов
не подтверждаются. Режим проверки: существующая high-risk F211, ограниченная
запись reviewer evidence без изменения реализации.

Предыдущая запись CHK002 выше и `/tmp/graf-a12-requirements-review.md`
описывают историческую редакцию A12 только про config. Они не ограничивают
запрос пользователя закрыть все конкретные находки исходного MD. Утверждение
старого отчёта об ограничении со стороны пользователя неверно; текущую границу
CHK002 задаёт эта delta. Историческое описание config-only в quickstart также
требует согласования в T086 и не переопределяет уточнённые spec/plan/T084.

- **1 config:** AST тел, аргументов и декораторов
  `test_production_rejects_default_dev_web_csrf_secret` из HEAD и сохраняемого
  `test_web_production_runtime_still_rejects_default_csrf_secret` совпадает.
  Вход `_production_settings`, буквальное значение и ожидаемый
  `ValidationError`/`web_csrf_secret` одинаковы. После исключения удалённой
  функции весь AST config-модуля равен HEAD: web/non-web/file и остальные
  проверки не изменены. Это статический факт о текущем diff, не приёмка T084.
- **1 cookie-name:** тела и аргументы
  `integration/test_web_owner_session_context.py::test_web_owner_session_scaffold_defines_cookie_name_contract`
  и сохраняемого
  `unit/test_auth_web_session_context.py::test_session_cookie_name_uses_host_prefix_contract`
  совпадают по AST, декораторов и входных fixtures нет. Оба импортируют
  `AUTH_SESSION_COOKIE_NAME` из `twobrain_rec_server.auth.dependencies` и
  сравнивают с буквальным `__Host-twobrain_rec_owner_session`. Удаляется только
  скалярная проверка; импорт нужен остальным integration-сценариям и остаётся.
- **3 forbidden-readiness:** тела и аргументы
  `contract/test_deployment_readiness_contract.py::test_deployment_readiness_contract_rejects_rollout_ready_language`
  и сохраняемого
  `unit/test_deployment_helpers.py::test_validate_readiness_verdict_rejects_forbidden_021_verdicts`
  совпадают по AST; оба импортируют `validate_readiness_verdict` из
  `twobrain_rec_server.deployment` и требуют `ValueError` с `match="forbidden"`.
  AST декораторов различается: contract берёт `FORBIDDEN_READINESS_VERDICTS`
  из config, unit — независимый буквальный список. Статически разрешённые
  значения, порядок и число равны: `production_ready`, `user_rollout_ready`,
  `internal_user_pilot_ready`. Буквальный unit список должен сохраниться;
  замена его производственной константой ослабила бы независимость проверки.

FR-057 и plan явно сохраняют все другие assertions, альтернативные состояния,
параметры и fixtures. Проверены остальные девять параметризаций integration;
они не входят в удаление. В readiness contract остаются allowed-verdicts,
zero-processing-side-effects и restore-rehearsal проверки, в unit — allowed
verdicts и безопасный Markdown. Лишние импорты после удаления readiness-дубля
оцениваются по реальным оставшимся использованиям; `pytest` там ещё нужен.

SC-025 задаёт уменьшение соответствующих коллекций ровно на 1, 1 и 3;
новые CSRF/runner регрессии учитываются отдельно. Это требуемая разница,
а не измеренная pytest collection: collection и тесты не запускались.
Оба дополнительных дубля пока присутствуют, четыре cookie/readiness файла
совпадают с HEAD по AST. Блокирующих пробелов в уточнении не найдено.
CHK001/003/004 этой delta не переоценивались; T084–T086 остаются отдельной работой.
Full, Docker, GitHub и приложение не запускались. Исходный общий MD не найден
среди доступных файлов репозитория и проверенных временных MD; перечень E05.04
сверен по явному уточнению пользователя, текущему plan и реальным тестам.


## PASS delta — T088 / изоляция обязательного bootstrap proof — 2026-09-13

**PASS требований, CHK005: 1/1; общий checklist 5/5.** Прочитаны дополнение
`A12 convergence: isolated bootstrap proof` в spec, соответствующий plan и T088.
Прослежены существующие `postgres_test_database.py::prepare_schema`, URL/name
validators, `postgres_rls.py::postgres_advisory_lock`, module media/migration
fixtures и `test_runtime_role_bootstrap_is_idempotent_and_verifies_privileges`
в `test_playback_normalization_postgres.py`, а также настоящий
`bootstrap_runtime_database_roles.py`.

- Граница изоляции выбрана по PostgreSQL cluster: `ensure_disposable_media_role`
  сохраняет `twobrain_rec_media` после прежнего media-сценария, а bootstrap proof
  проверяет наличие ролей в `pg_roles` до своего исполнения. Отдельная БД или
  последовательное исполнение не создают новый role namespace. Новая
  function-scoped fixture только для этого proof устраняет зависимость, не
  удаляя общую роль и не подменяя производственные имена.
- Требования сохраняют `postgres:17-alpine`, уникальный контейнер и loopback
  порт, настоящие миграции через `prepare_schema`, ограниченную проверку
  окончательной готовности PostgreSQL и безусловную очистку своего контейнера,
  включая failed setup. Недоступный Docker, timeout, migration/bootstrap failure
  и невозможные предусловия собственного кластера не превращаются в SKIP.
  Создание ресурсов происходит при запросе fixture, а не при collection.
- Существующий proof дважды вызывает настоящий bootstrap, проверяет identity
  трёх ролей, атрибуты, отсутствие опасного membership, function/table/column
  privileges и отказ при unsafe membership. Plan/T088 сохраняют все эти
  assertions; меняются только источник URL и прежние skip-preconditions.
  `prepare_schema` уже восстанавливает `TWOBRAIN_DATABASE_URL` и кэш Settings
  после миграций, в том числе при ошибке.
- FR-057/SC-025 → A12 plan → T088 покрывают создание изолированного ресурса,
  failed-setup cleanup, прежнюю последовательность media→bootstrap и сравнение
  той же strict/performance коллекции: ожидается 69 PASS/0 SKIP вместо 68/1.
  Эти числа являются критерием предстоящей приёмки, а не результатом этой
  рецензии. Общая база остальных тестов, A10 focused и A12 Full order остаются
  прежними; отдельный authoritative Full остаётся в T077.

Пробелов требований, противоречий существующей high-risk F211/конституции и
непокрытых условий T088 не найдено. Код фикстуры и bootstrap-теста на момент
проверки ещё совпадал с HEAD. Это приёмка требований до реализации; T088 не
закрывается. Изменён только этот reviewer-owned checklist. Тесты, Docker,
GitHub, сборки и production не запускались.


## PASS delta — T089 / обязательные синтетические медиапроверки — 2026-09-13

**PASS требований, CHK006: 1/1; общий checklist 6/6.** Прочитаны явные
дополнения T089 в spec/plan/tasks и три существующих места пропуска в
`test_playback_normalization_media_matrix.py::_media_tools`,
`test_playback_normalization_workflow.py::test_real_ffmpeg_pipeline_builds_validated_dual_source_playback`
и `test_playback_normalization_test_rec_e2e.py::test_authorized_test_rec_converts_automatically_and_leaves_no_residue`.
Режим: независимая проверка требований существующей high-risk F211 с записью
только reviewer evidence. Текущий HEAD при проверке:
`0153db313795cfeb2322d2cfd4a1bdbea2d3a92f`, `codex/211-delivery-cutover`.

- Граница изменения точна: заменяются только три media-tool SKIP; остальные
  assertions, параметры, синтетические данные и настоящий normalization pipeline
  сохраняются. Статический подсчёт функций и буквальных параметризаций даёт
  49 случаев media matrix и один dual-source workflow case. Это проверка
  состава исходного кода, не результат pytest collection или исполнения.
- В TestRec сначала проверяется opt-in переменная каталога; её отсутствие
  сохраняет SKIP до обращения к media tools. Заданный недоступный каталог уже
  вызывает ошибку. При разрешённом существующем каталоге отсутствие инструментов
  теперь должно вызвать FAIL до чтения/копирования записи. Новые отрицательные
  проверки могут использовать временный пустой каталог, без частных аудиоданных.
- Прочитаны существующие resource steps обоих workflows: Full готовит ресурсы
  перед Ubuntu component, governance-fast уже ограничивает подготовку веткой
  `classify_path == server`. Plan сохраняет эти границы и не добавляет установку
  для других PR-путей. Работающий комплект не требует package manager;
  отсутствующий инструмент допускает штатную установку FFmpeg из Ubuntu,
  а broken executable/failed install должны остановить validation.
- FR-057/SC-025 → T089 plan → T089 задают исполнение трёх реальных предусловий
  и обоих настоящих resource shell-блоков с подставными внешними командами.
  Указаны working/missing/broken tools, ошибка установки, non-server scope и
  сохранённый opt-in. Приёмка 50 PASS/0 SKIP относится только к прежним
  синтетическим случаям; новые регрессии считаются отдельно. В quickstart
  сохраняются только метаданные. Проверка возможностей runtime-контейнера
  остаётся отдельной; новые образы, службы, registry и production-изменения
  в эту задачу не входят.

Блокирующих пробелов полноты, ясности, безопасности или противоречий требованиям
F211 не найдено. Существующие три media-tool места ещё содержали SKIP при
проверке. Эта отметка принимает требования до реализации и не закрывает T089.
Root отдельно выполняет analyze и issue sync перед кодом. Изменён только этот
reviewer-owned checklist; тесты, Docker, GitHub, установки и production
не запускались.

## Требования T094: только необходимые проверки метаданных

- [x] CHK007 Канонические changelog-фрагменты и переносы не выбирают infra сами по себе; mixed infra и неизвестные пути сохраняют прежние проверки. Реальный process preflight обязателен без feature pointer, валидный/невалидный unreleased исполняется; ограничение архивного validator явно сохранено. Требования/проверки покрывают FR-003/FR-008 и не ослабляют Full, exact SHA или deployment gates.

## PASS требований — T094 / точная классификация changelog — 2026-09-14

**PASS требований, CHK007: 1/1.** Режим: независимая проверка требований
действующей high-risk F211 с записью только reviewer evidence. Основание:
`codex/211-release-prep-20260914`, HEAD
`605a2e00454ebe555917f078fdc8caa495284832` и текущая дельта FR-003/plan/T094.
Эта отметка не принимает реализацию, не подтверждает исполнение тестов и не
закрывает T094.

- FR-003 задаёт точное исключение: `changes/unreleased/F<digits>.yaml` и
  `changes/releases/v<YYYY.MM.DD.N>/F<digits>.yaml`. Вложенные/произвольные
  файлы, иной суффикс и некорректный путь версии сохраняют прежнюю
  классификацию. Нынешний native scope допускает более широкий `v[^/]+`;
  ссылка plan на его соглашение не расширяет явную границу FR-003.
  Например, `changes/releases/vfoo/F211.yaml` не получает исключения.
- Прослежен текущий `classify_path` и объединение компонентов в
  `infra/scripts/ci-local.sh`: фрагмент сам не должен добавлять infra, но
  продуктовый файл сохраняет собственный выбор, а смешанный infra или
  unknown — прежние проверки и ограничение покрытия. Настоящий Git-перенос
  через существующий `diff --no-renames` должен проверить обе стороны
  удаления/добавления; подставного списка путей для этого условия недостаточно.
- Существующий `check-development-process.py` уже выполняет repository checks
  без `.specify/feature.json`: `validate-changelog-fragments.py`, затем
  `scan_changed_legacy` для изменённых `spec.md`. Наличие pointer отдельно
  включает его валидацию; передача PR metadata без pointer по-прежнему
  отклоняется. T094 меняет вызов этого checker в CI, не создаёт обход этих
  условий и не требует нового валидатора.
- Plan/T094 требуют отказ process preflight без pointer до дорогих стадий
  и исполнение настоящего checker на валидном/невалидном unreleased.
  Существующий `run_stubbed_ci` подходит для порядка и выбора; отдельный
  настоящий checker необходим для подтверждения сохранённой проверки
  содержимого. Обязательство проверять изменённые спецификации явно есть
  в FR-003 и не заменяется наличием фрагмента.
- Архивное содержимое не приписывается unreleased validator. Прочитан
  `prepare-release.sh`: текущие фрагменты проверяются до подготовки,
  архивные входы/назначения и feature identity проверяются существующими
  этапами подготовки выпуска. T094 сохраняет этот путь и не обещает
  универсальную повторную проверку всех исторических архивов в PR CI.
- FR-008 и T094 сохраняют required checks на точном SHA, один авторитетный
  frozen-source Full и deployment gates. Указанные в plan 261+253=514 с
  относятся к двум стадиям прежнего широкого PR; это не измеренная экономия
  отдельного release-prep. Приёмка реализации, новый hosted результат и
  итоговый выпуск остаются отдельными доказательствами.

Блокирующих пробелов полноты или противоречий в T094 не найдено. Проверены
spec/plan/tasks, настоящий runner/checker, native scope, подготовка релиза и
действующие правила валидации. Изменён только этот reviewer-owned checklist;
тесты, GitHub, сборки и production не запускались.
