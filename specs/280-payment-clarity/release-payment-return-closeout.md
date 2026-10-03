# F280 — выпуск и применение подтверждённой оплаты

Дата: 2026-10-03. Lane: release-deploy внутри high-risk-product. Фича 280-payment-clarity, задачи T029–T045; T032 закрывается только доказательствами ниже.

## Причина и исправление

ЮKassa подтверждала платёж, но служба GRAF, обрабатывавшая сверку, не имела нужной ограниченной роли базы для общей очереди. Подтверждение оставалось в provider_pending и не предоставляло доступ. Существующая очередь перенесена в maintenance; processing сохраняет роль приложения. Правила доступа к данным не расширены. Страница проверяет существующую оплату и показывает успех только после её применения. Новых финансовых операций для исправления не создаётся.

Старый Full CI37107429605 на e1012f98 завершился FAILURE и не выпускался. ПричинныйRED8/49→GREEN57:7устаревших текстовых ожиданий и1регрессия прежнего initial_checkout recovery. T045 восстановила узкий совместимый путь с прежним ключом и защитой invoice/operation/actor/amount/RUB. Два независимых SOURCE/TEST reviewers нашли2P2 состояния ожидания, оба исправлены; локальный основной переход подтверждёнRED5/20→окончательный full410PASS264.96с. Окончательные source/test remarks0, requirements checklist17/0.

## Проверки реализации и подготовки

- PR7479: reviewed head97c2db66105ec8a446ce4f8efd639d3aa47a23ae, merge29ae608d8674e97ce2a89d416b4d219d43ae6ffa. Common validator PASS: governance37105751427, macos37105751407, metadata37105968393.
- T045 PR7496: reviewed headccd3bbf71a7602740f1d22b28708ec241f50f692, merge0221d6ccbc094d030f180a8382efc9f43c54ea39, base e1012f98. Common validator PASS: governance37110799199, macos37110799195, metadata37110799183.
- Release-prep PR7497: reviewed headc58459a3c50ce2d813fa2d2b5726b6669bc5c0f8, mergebbe1fc772896e1d88fb9f601daefba4b6e5609b2. Common validator PASS: governance37111606480, macos37111606484, metadata37111605896.
- route→PostgreSQL storage32PASS; Chromium56/WebKit56PASS для настоящего сервера и общего контроллера; окончательная серверная матрица410PASS. Ruff/governance/fragments/issue-canon/diff PASS. Исторические отказы сохранены в отдельных validation/review reports.

## Неизменяемый выпуск

- CalVer v2026.10.03.3; features280,285; PRs7497,7496,7494,7479,7469,7461, skips0.
- base published v2026.10.02.7/78f9a1207a4aba6ef1ecaf85431888d1e055dd95.
- train train-20261003T090627Z-bbe1fc772896; candidate rc-20261003T090820Z-ec2855e03f27.
- Deployed candidate source SHA: bbe1fc772896e1d88fb9f601daefba4b6e5609b2.
- Changelog digest sha256:1ba18af6ab702feb3ebae5966c1fc360a4f9528d159bd03d3247b93dfdb64d73.
- Единственный release-full37112054115, reserved2026-10-03T09:09:06Z, requested/source совпадают. **PASS:** все8PostgreSQL групп, strict/performance, static/governance, macOS и aggregate. Authoritative receipt digest sha256:8957745bda42ff65315f2b1b573c4107229e8a5555b3b3a7af270acaac96823d.
- train-attest/decide **GO**, отдельные create-once records; исходный frozen manifest не изменён.
- CD dry-run **PASS**, execute **PASS**,226с, deployed/runtime SHA совпадает; readiness_verdict=infra_smoke_ready. Публичное здоровье и существующий подписанный update feed/archive проверены; проверки записи/воспроизведения вне области этого billing closeout.
- Tag и non-draft stable GitHub Release v2026.10.03.3 опубликованы на том же source; отдельная immutable publication attestation проверила настоящий tag/release.

## Проверка уже оплаченного платежа

Повторное чтение 2026-10-03T09:22Z сопоставило один и тот же непустой внутренний отпечаток с предвыкладочным наблюдением. Идентификаторы/отпечаток в отчёт не переносились.

- До: ЮKassa succeeded/paid, receipt_registration succeeded; GRAF invoice pending/operation provider_pending, grant0, personal доступ отсутствовал.
- После запуска новой maintenance: invoice/operation **succeeded**; **ровно1** связанное активное право source=provider_confirmed, связанная запись аудита с reason provider_get_confirmed. Связи invoice/operation/workspace совпадают;1invoice/operation, новых операций пространства0.
- Personal подписка и оплаченный период совпадают с единственным связанным правом. Отказ recurring_consent присутствует и явныйfalse; recurring_allowed=false; saved method=false. Чек зарегистрирован по наблюдению провайдера и локальным metadata.
- Все3службы rec-api/processing/maintenance запущены на candidate SHA, image/source environment совпадают; restart_count0.
- Processing: twobrain_rec_app, RLSon, NOSUPERUSER/NOBYPASSRLS, maintenance недопустим. Maintenance: twobrain_rec_maintenance с теми же ограничениями и разрешённой сверкой.
- В существующей billing reconciliation queue ровно1 свежий maintenance workflow и activity poller; свежих processing/other pollers0. Старая запись processing существует как устаревшее наблюдение, а не активный обработчик.
- Публичная оплата/наблюдение включены, consent checkbox по умолчанию отмечен; данный оплаченный отказ от продления сохранён.

Проверка была только чтением; provider mutations0. Право и связанный аудит созданы после запуска новой maintenance на подтверждённом исходном коде. Источник права и причина аудита согласуются со сверкой GET существующего платежа; наблюдения не атрибутируют отдельную запись конкретному процессу. В наблюдаемом пространстве новых платёжных операций нет.

Наблюдения выполнены только чтением: READ ONLY/rollback SQL, GET существующего платежа ЮKassa, Temporal describe и Docker inspect. Личные/платёжные идентификаторы и отпечаток в репозиторий не включены. Оператор не выполнял новую оплату, списание, возврат или ручную выдачу доступа; это граница выполненных команд, а не вывод об отсутствии любых внешних действий.

## Границы

Частная сессия пользователя после выпуска не наблюдалась; не утверждаем, что пользователь уже видел новый экран. Банковское зачисление, возврат, живое автоматическое продление и человеческая финансовая приёмка остаются отдельными T011/T012/F278/#7366. Подписанный публичный macOS установщик сохраняется, новый пакет не публикуется. F285 включена как уже слитый состав; её отдельная приёмка и чужой PR7470 не менялись.

## Первичные доказательства и область независимой сверки

- Проверки PR: [#7479](https://github.com/yshishenya/graf/pull/7479), [#7496](https://github.com/yshishenya/graf/pull/7496), [#7497](https://github.com/yshishenya/graf/pull/7497); записи common validator сверены оператором по точному SHA.
- Authoritative [release-full 37112054115](https://github.com/yshishenya/graf/actions/runs/37112054115): общий результат SUCCESS; локальный receipt и GO относятся к одному кандидату.
- [Опубликованный выпуск v2026.10.03.3](https://github.com/yshishenya/graf/releases/tag/v2026.10.03.3) и publication attestation относятся к source SHA выше.
- CD dry-run/execute: первичные локальные журналы оператора, не включаемые в репозиторий; execute содержит deploy_result=pass, runtime/deployed SHA, public_download_smoke_result=pass, public_update_feed_smoke_result=pass, final_temporal_readiness_result=pass.
- История RED/GREEN и независимых исходных обзоров: [validation-payment-return-release-regressions.md](validation-payment-return-release-regressions.md), [converge-payment-return-release-regressions.md](converge-payment-return-release-regressions.md), [review-payment-return-release-source.md](review-payment-return-release-source.md), [review-payment-return-release-tests.md](review-payment-return-release-tests.md).
- Первый независимый аудит подтвердил производственные наблюдения, но удержал публичный черновик из-за слишком сильной атрибуции и отсутствия источников для части утверждений. Его HOLD сохраняется в [review-payment-return-live-first.md](review-payment-return-live-first.md); уточнённый повторный обзор — [review-payment-return-live-final.md](review-payment-return-live-final.md). Эти отчёты проверяют предоставленные первичные доказательства, не повторяют частную пользовательскую сессию.

## Повторная сверка перед документальным завершением

Оператор повторил те же проверки только чтением 2026-10-03T20:25:40Z. Непустой внутренний отпечаток снова совпал с исходным платежом; invoice/operation succeeded, одно связанное активное право, paid_through=2026-11-03T09:19:12.495136Z. Явный отказ от продления сохранён; новых платёжных операций пространства и изменений у провайдера при проверке — 0. Все три службы по-прежнему работают на опубликованном source SHA. Свежие чтения GitHub подтверждают non-draft/non-prerelease выпуск и release-full SUCCESS на том же исходном коде; annotated tag разрешается в этот commit. Эта дополнительная сверка проведена оператором и не заявляется новым независимым аудитом.

Независимый повторный обзор исправленного черновика — PASS в указанной области. T032 завершена по доказательствам выпуска и применения оплаты; T011/T012/F278 и общая человеческая/финансовая приёмка остаются отдельными. Этот документальный коммит не изменяет опубликованный candidate SHA или работающие службы.
