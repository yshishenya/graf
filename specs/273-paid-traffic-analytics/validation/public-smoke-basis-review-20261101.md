# F273/T106 — независимое before-code ревью предпосылки public smoke

Дата: 01.11.2026. Проверяющий `/root/public_counter_readiness_review`.
Ветка/source из текущего `.specify/feature.json`:
`codex/f273-smoke-basis-20261101`,
`e4762f64ba7bab08e2a06f51a15bf370d30d3295`.
Полоса: узкая тестовая совместимость действующего Spec Kit среза T106.

**Requirements PASS; checklist5 отмечены/0 открыты; P1/P2/HIGH — 0/0/0.**
Отметки существующего checklist не переопределяют общую приёмку T106;
текущий report принимает только план подготовки учебного valid register.

## Матрица всех пяти пунктов

1. CHK001: старые public scope/flags/env/revision/surfaces не меняются.
   test_093 сохраняет настоящие assertions landing/download external scope
   и login relay-only. Добавляется только аргумент существующей opt-in
   public_basis_register; product provider scope/flags не подставляются.
2. CHK002: current public_analytics_blocker и настоящий reader перечитаны.
   available=false или file_errors дают отказ; header version1 без отзывов
   — валидная начальная предпосылка, не разрешение missing файла. Existing
   conftest fixture создаёт такой файл в tmp_path и monkeypatch восстанавливает
   env. Smoke перемещает уже имеющийся legal_basis_state_file до public
   builder; тот же файл остаётся в live_environment. Нового реестра/кэша
   или положительного production разрешения нет.
3. CHK003: patch.dict(os.environ,{BASIS_WITHDRAWAL_STATE_FILE_ENV:...})
   ограничен единственным public builder. Нельзя подменять blocker/reader
   или расширять область patch на transport. Настоящий context читает файл;
   route/delivery/final PostHog gate не меняются. Положительный учебный файл
   не отменяет restore/readiness/consent/catalog проверки. Existing
   public_analytics_config CLI уже применяет TemporaryDirectory/patch.dict;
   его API не требуется менять ради единственного caller.
4. CHK004: реальные RED3 подтверждены в журнале. План сохраняет assertions
   и требует GREEN тех же трёх, весь page-scope module, public unit/контракты,
   independent implementation review/converge. Smoke output контракт
   фактически исполняет shell и extracted Python; второй запускает
   sys.addaudithook на socket.connect/getaddrinfo. Сетевой запрет и
   check_restore_blocked до/после synthetic transport должны сохраниться.
   Следовательно GREEN не должен достигаться снятием запретов или
   удалением restore/assertions. Дополнительная общая helper API не нужна.
5. CHK005: дополнение plan/tasks оставляет T106/#7696 открытыми. Рабочие
   flags, server gate и внешнее включение не затронуты. Local GREEN не
   принимается за actual delivery/SDK/runtime/T0 или успех продвижения.
   До выпуска остаются independent code review/converge/exact-SHA gates;
   текущий старый HOLD внешнего включения не снимается тестовой подготовкой.

## Прочитанные факты и причинное доказательство

Полностью прочитаны новые plan/tasks sections и existing checklist, spec
T106 server/current-browser/SDK sections, test page-scope module, conftest
fixture и public_analytics_config CLI, public blocker/builder, reader
legal_basis_lifecycle и smoke body с фактическими restore/transport guards,
контрактный smoke-output модуль с network audit. Прежний server review
прочитан как зависимость. Большие усечённые выводы не объявляются полным
чтением: актуальные зависимости reread адресно без усечения.

Прочитан RED summary:3failed/2.22s (test_093 и два smoke-output теста),
ошибки ожидают enabled public context без читаемого withdrawal register.
Дополнительный диагностический журнал cause прочитан: те же3passed/0skips/
1.08s с одним внешним temporary version1 basis env на неизменном source.
Это усиливает причинную связь с отсутствующей synthetic prerequisite;
не принимает ещё не написанный scoped patch и не доказывает runtime.
TemporaryDirectory cleanup сообщён исполнителем, проверяющий его не
воспроизводил. Gate/assertions по этому эксперименту не менялись.

Исключение повторного чтения F273 применено только к неизменным ранее
прочитанным constitution/PRD/status/product-gates/guidance: их хеши совпали.
Production public analytics, provider_delivery_gate и legal_basis_lifecycle
также совпадают с прежним собственным review. Новых privacy/storage/network
свойств здесь не вводится. Настоящее состояние SDK/старых вкладок и общий
T106 оцениваются по своим отдельным срезам, не переоткрываются этим планом.

Изменены только назначенный checklist и этот report. Тесты/сеть/Git/GitHub/
CI/runtime/серверы/выпуск не запускались. Код/spec/plan/tasks не менялись;
чужие изменения сохранены. Перед реализацией действуют прежние analyze/
sync и обязательное independent after-code review. Final checklist фактически перечитан после записи: **5 отмечены/0 открыты**.

## Хеши принятого состояния до кода

- `specs/273-paid-traffic-analytics/plan.md`: `d0d55807782192bbb23e1740f34464b0ab1bf54d52fffb6b33ea740985736f89`.
- `specs/273-paid-traffic-analytics/tasks.md`: `a2f641d6e6b21830260232daed6c414002dcf175eb96414a2c837c1cf77e1ae4`.
- `apps/server/tests/integration/test_product_analytics_yandex_page_scope.py`: `ae345ded30aea14460895b63fe5e21919e3dd492838a547332432db268fdd4a7`.
- `infra/scripts/run-product-analytics-provider-smoke.sh`: `440e8a37942828a2f705215d2555f4884f2a790bb0de0d3ce983093870bcd245`.
- `apps/server/tests/conftest.py`: `0a8a2cb767b2f74e777fcb0c79616e68c65b0bf5a9ad5418838a4a0693389793`.
- `apps/server/tests/fixtures/public_analytics_config.py`: `07253a6f7dba5d917f837ee05c4e4467eacf0676b3df0191f8205465cdf4eb19`.
- `apps/server/tests/contract/test_product_analytics_provider_smoke_output.py`: `cc7e3b4c2fc90c3409aa138d72d8535916933b6ab633294bcb09d4862388f43b`.
- `apps/server/src/twobrain_rec_server/public/analytics.py`: `c789fa7ab77ee5090c0542fd422fadab175e50a618c8d7229e10c34416d3694d`.
- `apps/server/src/twobrain_rec_server/product_analytics/provider_delivery_gate.py`: `fbb2616e62802ee0050b0dd2bf220583bd6f4c9772c2a1d88a261c0bcdc04f9e`.
- `apps/server/src/twobrain_rec_server/product_analytics/legal_basis_lifecycle.py`: `ac4eb465afb0c647b0d3501bdbeaca2a8a4b1d9c6cad59d4c9a9953cae5f81f9`.
- `.specify/memory/constitution.md`: `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8`.
- `docs/prd-voice-layer-final.md`: `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2`.
- `docs/current-product-status.md`: `25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16`.
- `docs/agent-guidance/product-gates.md`: `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5`.


## Независимое implementation review / scoped converge

Фактический diff двух owned code/test файлов прочитан полностью.
**Scoped implementation PASS; P1/P2/HIGH — 0/0/0.**

В test_093 изменена только сигнатура — явно запрошена существующая opt-in
fixture public_basis_register. Все прежние assertions landing/download,
external scope и login relay-only/replay denial сохранены. Fixture пишет
версионный пустой withdrawal register в tmp_path; monkeypatch восстанавливает
исходный env при teardown. Не меняются global/autouse state либо production
файлы; API CLI public_analytics_config также не затронут.

Smoke добавляет os import, переносит прежнюю единственную запись
legal_basis_state_file выше public builder и ограничивает patch.dict
os.environ единственным вызовом builder (включая его Settings). После with
исходное окружение автоматически восстанавливается, в том числе при ошибке.
В дальнейшем live_environment получает путь к этому же файлу; дублирования
или перезаписи register нет. Весь файл остаётся внутри прежнего
TemporaryDirectory и очищается при выходе. Прочие readiness/transport
настройки не меняются.

Production public.analytics/web, reader legal_basis_lifecycle и final
provider_delivery_gate совпали по hashes с before-code. Условие
available/file_errors/withdrawal и свежие context/relay/worker решения
не менялись. Smoke не патчит эти функции, не кэширует positive decision и
не создаёт runtime basis. Сохранён отдельный старый synthetic
restore_consistent patch только вокруг двух transport wiring вызовов.
check_restore_blocked выполняется до и после него, проверяет прежние
blockers/status и транспортные счётчики0→1. Нельзя выдавать этот процесс
за настоящее восстановление либо действующую external отправку.

Contract smoke output module неизменён. Второй контракт устанавливает
sys.addaudithook для socket.connect/getaddrinfo, затем исполняет реальный
Python body. Assertions network, restore marker и отсутствие запрещённых
полей/секретов в output сохранены. Новый env patch не охватывает audit hook
и не отменяет его. Это изоляция учебной проверки, не изменение production
сетевых разрешений.

### Прочитанные результаты

Тесты reviewer не запускал; фактически прочитаны журналы исполнителя:

- green.log: **53passed/0skipped/2.04s** — весь page-scope, два smoke-output,
  public unit, lifecycle и delivery gate по отчёту запуска.
- public-contracts-final.log: **36passed/0skipped/16.85s**, collection_count36;
  actual rendered consent modal выполнен (2.69s), PostgreSQL runner status
  pass/duration21s, isolated_container_removed.
- Первые public-contracts.log и public-contracts-corrected.log:
  no tests collected/container_not_started, EXIT4 по отчёту исполнителя.
  Это ошибочные пути запуска, не PASS и не fallback выполнения сценариев.
- process/fragments/governance журналы непосредственно прочитаны — OK.
  Ruff/Bash syntax/diff PASS сообщены исполнителем и записаны в его report;
  отдельных журналов этих трёх проверок в просмотренном наборе не было.

Warnings pytest rewrite/Starlette сохранены в журналах и не являются skips.
Профили53 и36 не представлены как один общий прогон89. Прочитанный прежний
RED3 и causal3 с одним внешним synthetic register объясняют исправление;
после code diff GREEN подтверждает его действие без ослабления gate.

### Converge и пределы

Все четыре группы принятого plan (old public scope, valid temporary basis,
независимые restore/network guards, честные границы приёмки) реализованы
минимальным diff и покрыты указанными профильными результатами. Все5
checklist групп сохраняются, новых unmapped задач/P1/P2/HIGH внутри этого
среза не найдено. T106/#7696 и T118 не закрываются; эти тестовые изменения
не добавляют новую продуктовую функцию или инфраструктуру.

Изменены только reviewer report и checklist; остальные изменения сохранены.
Код/spec/plan/tasks/Git/GitHub/CI/сеть/runtime/сервер/данные не менялись;
самостоятельные тесты не запускались. Checklist фактически перечитан после
записи: **5 отмечены/0 открыты**. Exact-SHA PR gates/merge/Full/CD и рабочее
включение, индивидуальный server revoke, весьT106, T0 и коммерческий рост
не принимаются. Самостоятельные более поздние SDK срезы не переоцениваются
данным review тестовой предпосылки.

### Хеши итогового проверенного состояния

- `apps/server/tests/integration/test_product_analytics_yandex_page_scope.py`: `a15256f367812694c2d917eaf148ab4b2e4627c95fb35d98e124e354740b1ca6`.
- `infra/scripts/run-product-analytics-provider-smoke.sh`: `a4f9277704a367b3134b732d429f04c6f1179833969d455e57e3f40b32f3c6cb`.
- `apps/server/tests/conftest.py`: `0a8a2cb767b2f74e777fcb0c79616e68c65b0bf5a9ad5418838a4a0693389793`.
- `apps/server/tests/fixtures/public_analytics_config.py`: `07253a6f7dba5d917f837ee05c4e4467eacf0676b3df0191f8205465cdf4eb19`.
- `apps/server/tests/contract/test_product_analytics_provider_smoke_output.py`: `cc7e3b4c2fc90c3409aa138d72d8535916933b6ab633294bcb09d4862388f43b`.
- `apps/server/src/twobrain_rec_server/public/analytics.py`: `c789fa7ab77ee5090c0542fd422fadab175e50a618c8d7229e10c34416d3694d`.
- `apps/server/src/twobrain_rec_server/public/web.py`: `d61c93bb74ae6b0f1bd193844a093985b9d85f25b11e9b4e78e01d3cf9ec19a3`.
- `apps/server/src/twobrain_rec_server/product_analytics/legal_basis_lifecycle.py`: `ac4eb465afb0c647b0d3501bdbeaca2a8a4b1d9c6cad59d4c9a9953cae5f81f9`.
- `apps/server/src/twobrain_rec_server/product_analytics/provider_delivery_gate.py`: `fbb2616e62802ee0050b0dd2bf220583bd6f4c9772c2a1d88a261c0bcdc04f9e`.
- `.dev/public-smoke-basis/green.log`: `b3c948112a62a7d5285071869b028f3e8b6e842d995e97d4d2f56748c2e22452`.
- `.dev/public-smoke-basis/public-contracts-final.log`: `822c49659e28e23be043685db9693711badc6d7b54eee6ac9e26dbd4153a9039`.
