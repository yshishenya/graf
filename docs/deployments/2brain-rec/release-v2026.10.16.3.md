# Серверный выпуск v2026.10.16.3 — доступность отмены продления

Сервер развернут, стабильные tag и GitHub Release опубликованы. Выпущенный источник — `42f0b95105c6545235ba219a55cbcc62bf577f39`. Эта запись относится к документальному завершению T069/T070 существующей F280; ветка документального дополнения не является новым кодом сервера. Полоса изменения: docs-only/mechanical evidence; исходный продуктовый срез — high-risk-product, выпуск — release-deploy.

## Что вошло

В полной оболочке кабинета без JavaScript ограничена мобильная колонка и скрывается только боковая панель кабинета. Существующий признак `data-cabinet-shell` сохраняет административную навигацию. Вложенная карточка оплаты использует ограниченную колонку `minmax(0,1fr)`, а длинная подпись кнопки подписки переносится без растягивания формы. Предварительное действие хранения называется «Проверить изменение» при увеличении и уменьшении объема.

Цены, согласия и их предвыбор, обработчики списания/отмены, API/БД и денежные маршруты сохранены. Миграций и новых зависимостей в этом срезе нет. Между проверенным HEAD PR7616 и выпущенным источником `apps/server` побайтово не менялся; PR7619 подготовил метаданные выпуска и архив F280. Предыдущая .2 и ее неизменяемые записи не заменялись.

## Исходники и точные PR-проверки

Основа состава выпуска — опубликованный `v2026.10.16.2`, source `fb78b469aa7c22ad680424411025166870856b22`. Диапазон содержит PR [#7618](https://github.com/yshishenya/graf/pull/7618), [#7616](https://github.com/yshishenya/graf/pull/7616), [#7619](https://github.com/yshishenya/graf/pull/7619); обычные последовательные слияния без обхода обязательных проверок.

- PR7616: exact head `66c193bf5d47d462bd444d9a78623fbeb9d808e2`, checked base `69f493dba540f13b780e7ecb2cc34680d776fdb2`, merge `9d6243a22c0c7d9ee0a08b69ed4a969468ec92d1` от `2026-10-16T04:01:56Z`. Действующие proofs: governance [38847741590](https://github.com/yshishenya/graf/actions/runs/38847741590), macOS [38847741552](https://github.com/yshishenya/graf/actions/runs/38847741552), metadata [38847742504](https://github.com/yshishenya/graf/actions/runs/38847742504), попытка 1. Общий `validate-pr-checks.py` повторно подтвердил этот точный head/base и фактическое слияние.
- PR7619: exact head `e48a7c0405a4f07656fdcc099510441e9bd7269e`, checked base `9d6243a22c0c7d9ee0a08b69ed4a969468ec92d1`, merge/source `42f0b95105c6545235ba219a55cbcc62bf577f39` от `2026-10-16T04:05:18Z`. Governance [38848539446](https://github.com/yshishenya/graf/actions/runs/38848539446), macOS [38848539442](https://github.com/yshishenya/graf/actions/runs/38848539442), metadata [38848623095](https://github.com/yshishenya/graf/actions/runs/38848623095), попытка 1; общий `validate-pr-checks.py` повторно PASS на этом head/base и merge.
- PR7618 — документальное завершение предыдущей .2, merge/base PR7616 `69f493dba540f13b780e7ecb2cc34680d776fdb2`; governance receipt состава выпуска `38844714246`.

## Причинная история RED и GREEN

Реальный Ubuntu governance-fast [38846102759](https://github.com/yshishenya/graf/actions/runs/38846102759) на `c9f938851942c6f5c931ae57e5dfd9043d664769`, base `69f493dba540f13b780e7ecb2cc34680d776fdb2`, остановился: отмена при 320 px, светлой теме, 200%, без JavaScript, left 58/right 322.203125 при допустимом right≤321. Прежние macOS PASS этой среды не подтверждали. Минимальная ширина формы растягивала auto grid track; общий стиль кнопки запрещал перенос длинного слова.

После двух CSS деклараций настоящий Ubuntu GREEN [38847741590](https://github.com/yshishenya/graf/actions/runs/38847741590) прошел на exact `66c193bf5d47d462bd444d9a78623fbeb9d808e2`. Прежние размеры окна/увеличение/темы/режимы JS/геометрические пороги и клавиатурный native submit не ослаблены; добавлена проверка Range текста внутри кнопки и окна. Самостоятельная диагностика на Mac и прерванный label-прогон с return 130 Linux RED/GREEN не заменяют.

Полные локальные проверки macOS у исполнителя: 338 модульных и контрактных тестов PASS, Chromium — 20 PASS за 66,69 с, WebKit — 20 PASS за 85,19 с. Независимый итоговый проверяющий повторил: 338 PASS за 1,17 с, Chromium — 20 PASS за 64,69 с, WebKit — 20 PASS за 85,71 с. На каждый движок 16 административных и 24 сценария отмены встроены в один из 20 pytest; повторы и вложенные сочетания не суммируются как уникальные тесты. Проверены все четыре потребителя общей карточки, сохранность согласий и административной навигации. Проверка требований: 137 отмеченных пунктов, незавершенных 0, всего 11 контрольных списков. Независимый обзор исходников и браузеров на macOS — PASS, критических, высоких и исправимых средних замечаний 0. Полная история — [validation-five-agent-audit.md](../../../specs/280-payment-clarity/validation-five-agent-audit.md), [независимый итог](../../../specs/280-payment-clarity/review-linux-reflow-final.md).

## Замороженный кандидат и Full

- Train `train-20261016T040530Z-42f0b95105c6`, included PRs7619/7618/7616, Feature280; synthetic provenance `5572eba8c59559c3ed8d8eba001ba319fb616f3d`. Frozen source — точный SHA выше.
- Candidate `rc-20261016T040623Z-f2e7635cd992`, frozen `2026-10-16T04:06:23Z`; SHA256 candidate JSON `1f9cb46bb6ba4aedd13b0c5f87fb3c3285d62297bd813a9e90eff0cca0ba0f98`.
- Единственный авторитетный GitHub [release-full38848876764](https://github.com/yshishenya/graf/actions/runs/38848876764), попытка 1 — SUCCESS на frozen source. Evidence status passed/authoritative_full true, lane full; requested/start/end/server/macOS/repository SHA совпали; skipped_gates пуст. Full включает Ubuntu server/infrastructure и macOS Swift; это не новый установленный macOS выпуск.
- Full evidence digest `sha256:aeae37359b9da47ca54d2a3b9f701ec2796d63235d7c7be012c56c4cc1e6dc5e`; changelog digest `sha256:45624c34a43252271951007b65f2b6f54d1c709f40c21a3ea608e809ecab5bcf`.
- Attested train GO SHA256 `c3919f91b714010b6441810ae68d211b807f876907dee398fd1df3f0b8e00ab2`; decision GO SHA256 `0b9a82ae684fab23c1d2b74a6612e1d827612df777b84abd3f3badf266afeb92`. Decision связывает тот же candidate/train/source/Full/tag, неизменяемый первоначальный frozen JSON не перезаписан.

## Развертывание и публикация

Единый оператор root выполнил штатные CD dry-run и разрешенный execute: candidate_gates=passed, authoritative_full_reused, deploy_result=pass; driver exit0, release_result=pass. deployed_sha/runtime_sha равны `42f0b95105c6545235ba219a55cbcc62bf577f39`; второго Full для кандидата не было.

Штатный журнал подтвердил свежую резервную копию (backup_result=pass), migration_head_result/migration_verification PASS, ожидаемый head `0104_summary_share_scope_cascade`, готовность Temporal/processing и итоговые public download/update-feed проверки PASS. Очистка пробных данных завершилась PASS: 34 строки БД и 3 объекта удалены, остатка нет. Резервная копия сохраняется в закрытом серверном хранилище; пути и содержимое в эту запись не включены. Откат не выполнялся.

[Стабильный GitHub Release](https://github.com/yshishenya/graf/releases/tag/v2026.10.16.3) опубликован `2026-10-16T04:20:31Z`, draft=false/prerelease=false, target/source совпал. Annotated tag object `eb07931d44cf88af39b0a7e87872e4eb7ce25547` разрешается в выпущенный SHA. Publication attestation `pa-rc-20261016T040623Z-f2e7635cd992` от `2026-10-16T04:20:33Z` связывает tag/Release/source и тот же decision digest; SHA256 публикации `a5f6356bfd48a2875f4aeddfe26474751dd9c1838b61516318184ff7374b0d6b`.

Русские release notes содержат изменения, проверку, совместимость, ограничения и связь с issue/tasks. Release assets пуст: выпуск серверный, новый публичный macOS пакет/appcast не создавался. Прошедший Swift Full и публичные download/feed smoke не являются установленной приемкой GRAF Dev.

## Независимая сверка работающей версии

Независимая роль 5 проверила production только чтением: текущий серверный HEAD и source labels `rec-api`, `rec-media-worker`, `rec-processing-worker`, `rec-maintenance` совпали с выпущенным SHA. Штатный `release-images.py verify candidate` PASS. Активная deploy attempt `4b65feee03024ff4b8c92e809ec4ee4e`, result=deployed; source/candidate/decision/full digests совпали с неизменяемыми записями выпуска.

Внутри работающего API, по фактически установленному Python package, совпали 6/6 файлов с проверенными байтами PR7616:

| Файл относительно twobrain_rec_server | SHA-256 |
| --- | --- |
| `cabinet/static/cabinet/cabinet.css` | `f4ba435b5461e65a189c5fd85276031b22a9f64dabfad5cbe99101c375f477da` |
| `cabinet/templates/cabinet/pages/billing_storage_content.html` | `4b174d1c6e020731876866500d48bc93dd261b662c9aab2d81aca6449be07e39` |
| `cabinet/templates/cabinet/pages/billing_subscription_content.html` | `34523d26edfff86ccd9044c70013ccd392fbbd716b5221411e77f8ef15f38aa8` |
| `cabinet/templates/cabinet/pages/billing_checkout_content.html` | `9c68661848504e02b02f067f7e2a3f759fa0c04fd7f808354e4388c1d06d54b2` |
| `cabinet/static/cabinet/cabinet.js` | `ab3ab44f37d6ac4bf479503f5015f444edd8ef779f39c8fbb7e3251b89cb15cd` |
| `cabinet/web_routes/billing.py` | `95c4eea46fcdc581c02a155933f39da9c8459e3df504080a0bb588ab685b68dd` |

Серверная сверка всех прежних материалов распространения подтвердила 200 файлов до и после выпуска (87 pkg + 102 zip + 11 xml): измененных, добавленных и пропавших 0. SHA256 канонического словаря относительных путей и контрольных сумм — `c6a3123e7d867ab6f1281d1e09f3d8b10a867d316c13c6865e7a13da892689eb`. Публичный GET appcast HTTP 200, SHA256 `a41579d1b65a44ec2a6e33a4efb33aa1841f8ea4d1d5d44445f3ef8138d7711a` совпал с исходным снимком; основные pkg/zip HEAD 200. Все 200 файлов проверены полными контрольными суммами на сервере, отдельный HTTP для каждого файла и повторная загрузка архивов на Mac не выполнялись. Эта сверка доказывает сохранность распространения, не новую подпись/нотаризацию или установленную приемку приложения. Исходный независимый отчет и JSON с техническими метаданными сохранены локально; их живые серверные пути в Git не копируются.

## Работающий интерфейс

Root 16.10.2026 после развертывания и подтверждения публикации от `04:20:33Z` проверил интерфейс через CUA во встроенном браузере в обычном действующем авторизованном сеансе. Автор этого документа не заявляет самостоятельного повторного доступа к сеансу. Снимки визуально проверены root; частные данные, снимки, адреса и номера документов в Git не включены.

- После reload `/billing/subscription` показал активный оплаченный доступ и отключенное автопродление. «Способ оплаты, условия и история» раскрывается.
- «Продлить подписку» открыл годовое оформление: обязательная оферта не выбрана, необязательное автопродление выбрано; сумма, период, следующее списание и маскированный адрес чека видны. Финансовая форма не отправлялась.
- При viewport 320×800 карточка оформления имела left 10/right 310, document scrollWidth=innerWidth=320. На подписке ширина документа 320, кнопки внутри окна. Это проверка окна 320×800 в действующем браузере. Увеличение 200%, режим без JavaScript и обе темы проверяются отдельной автоматической матрицей и не приписываются живому сеансу.
- `/billing/storage` показывает «Проверить изменение», CTA left 10/right 310, document 320. Покупка не подтверждалась.
- Ранее оплаченный документ «Платеж и чек» показал состояния «Оплачен» и «Чек зарегистрирован», карточку в пределах 10–310 px и ширину документа 320 px; повторного действия оплаты нет (`duplicatePaymentCTA=false`); «Сведения о платеже» раскрывается. Это безопасный просмотр существующего оплаченного документа, не новая цепочка оплаты/чека у провайдера.

Размер окна восстановлен. Оплат, отмен, возвратов, писем и изменения автопродления в этом повторе не выполнялось. Проверка действующего сеанса не заменяет человеческую SC005/006, установленный GRAF Dev и полный финансовый цикл F278.

## Границы закрытия

Подтверждение относится к техническому срезу T069/#7613 и T070/#7614. T069/T070 отмечены выполненными только после собственного и независимого обзора, настоящего Linux GREEN, точных PR gates/обычных слияний, нового frozen Full/GO/CD/publication, независимой сверки runtime и проверки работающего интерфейса. Issues закрывает назначенный владелец после подробных комментариев и проверки действующих доказательств; этот документ сам по себе не утверждает уже выполненное закрытие GitHub issues. Пять независимых агентных ролей остаются технической проверкой. Это не пять самостоятельных участников SC005, не измерение SC006, не установленная проверка GRAF Dev и не финансовая приемка F278.

T011/#7378, T012/#7379, umbrella#7366 и F278 остаются открытыми. Новых оплат, возвратов или переключения действующего автопродления в этом завершении не выполнялось. CD оставил automatic_retry/backfill_inventory/range_playback/normalization_cleanup как required_post_deploy; готовность workers эти сценарии отдельно не закрывает. Legacy Impact: untouched.
