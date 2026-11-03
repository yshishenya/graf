# Независимая проверка требований provider-smoke F273/T118

Дата: 23.10.2026. Проверяющий: `/root/f273_smoke_requirements_reviewer`.
Рабочая копия: текущая `crisp`, ветка `codex/273-provider-smoke-recheck`.
Исходный HEAD: `1c5148dbe5c1c3d19ae69d713b99cc8227458cb6`.

## Решение до реализации

**PASS качества требований узкого исправления проверки.** Существующие
FR-035/051/053, operations §T118 и последняя запись tasks о недоказанном
восстановлении достаточны; менять требования или добавлять обход runtime
не требуется. Это проверка перед исправлением smoke, а не приёмка исправления.

Задача относится к существующему высокорисковому срезу F273/T118, а не к новой
фиче. Обязательные analyze, синхронизация issue, независимая проверка кода,
точные SHA/base проверки GitHub сохраняются. T118 остаётся `[ ]` до полного
согласованного восстановления и требуемой рабочей приёмки.

Перечитаны целиком четыре чек-листа, spec, plan, tasks, quickstart, research,
data-model, legal-basis, все четыре contracts, конституция, карта руководств,
spec-kit-flow, document-reading, development-process, product-gates.
В release-and-validation заново прочитаны применимые разделы Validation Lanes,
Local development, PR and merge, Production Deployment And Smoke, Restore
rehearsal cadence, Git Safety, Evidence Safety. История PRD и статуса повторно
не прочитана: основная задача передала проверенное прямое разрешение владельца
на узкое повторное чтение F273 от 21.10.2026. Самостоятельно сверены все семь
якорей исходного scoped-reading manifest; 7/7 совпали. Их совпадение не
объявляется новым полным чтением или доказательством выполнения продукта.

## Причина отказа и граница допустимого изменения

В исходном smoke создаётся самодекларированный restore-state v2 и ожидается
успешная доставка. Реальный `collect_analytics_operations_evidence` намеренно
возвращает `restore_consistent=False`: доверенного проверяющего T118 пока нет.
`analytics_operations_blockers` поэтому добавляет `restore_verification_failed`.
PostHog `capture_event` и Yandex `export` проверяют общий delivery gate до
считывания секрета для отправки и вызова транспорта. Одного корректного вида
хешей/списков и слова pass недостаточно, что соответствует operations §T118.

В существующем `tests.fixtures.analytics_operations.stub_verified_restore`
уже есть минимальная типизированная подстановка одного поля через
`dataclasses.replace`. Положительные transport/page-policy tests применяют
её только внутри тестового процесса; остальные состояния собираются реальным
collector. Поэтому новый рабочий флаг, fallback или второй механизм не нужны.

Критерии приёмки исправления:

1. До любой подстановки настоящий collector отвергает учебный receipt;
   readiness сообщает блокировку восстановления, оба провайдера отказывают
   отправке и счётчики вызовов обоих подставных транспортов равны нулю.
2. Только внутри явно ограниченного тестового контекста используется имеющийся
   helper либо эквивалентный stdlib patch с типизированным evidence. Остальные
   поля/проверки не подменяются: backup, retention, capacity, approvals,
   access, legal basis, consent и advertising transfer сохраняют свои ворота.
3. В этом контексте вызываются только предоставленные синтетические
   транспорты; проверяются форма запросов и ожидаемые конечные статусы.
   Настоящие сетевые отправки, рабочие секреты и рабочие receipts не нужны.
4. После выхода из контекста настоящий collector снова запрещает отправку;
   результат нельзя сохранить как рабочее подтверждение T118 или разрешение
   запуска. Такая повторная отрицательная проверка доказывает снятие подстановки.
5. Вывод smoke должен честно отделять штатную блокировку от синтетической
   проверки транспорта. Он не подтверждает работу провайдера, реальное
   восстановление, установленную конфигурацию, доставку тревоги или кампанию.

Новые тесты должны проверять выполнение встроенного Python, а не только наличие
строк patch в Bash. Изолированное выполнение без Docker/SSH/сети достаточно для
этой регрессии; полный production-сценарий T118 этим не заменяется.

## Самостоятельная оценка каждого чек-листа

Все существующие вопросы прочитаны и оценены заново; группы ниже объединяют
соседние вопросы с общим основанием. Отметки проверяют качество формулировки
для текущего среза, а не достигнутый SC. Вопросы без номеров requirements.md
обозначены RQ01–RQ16 по порядку. Маркеры не менялись.

| Чек-лист / вопросы | Конкретное основание достаточности требования |
| --- | --- |
| requirements RQ01–04 | spec §Контекст и цель, роли, пять US и обязательные разделы; предметные названия действующих платформ задают границу продукта, выбор реализации вынесен в plan. Smoke её не расширяет. |
| requirements RQ05–08 | В spec нет NEEDS CLARIFICATION; FR-001–062 задают наблюдаемые условия, SC-001–013 измеримы. Для T118 отдельно запрещён tar/hash-only успех, заданы конечные нативные сверки и время. |
| requirements RQ09–12 | Все пять US имеют сценарии; Edge Cases включает отказ восстановления/копии/канала и потерю основания. Out of Scope, Assumptions и Legacy Impact отделяют внедрение и платный запуск. |
| requirements RQ13–16 | FR и SC связаны через contracts/data-model/quickstart; пять independent tests определены. Feature meets outcomes означает возможность проверить результат, а не текущий результат. |
| privacy-measurement CHK001–007 | spec §Правовая конструкция, FR-007/008/047/061, legal-basis: три основания разделены, псевдонимизация не объявляется обезличиванием; запись одобрения и новая IP-категория отдельны. |
| privacy-measurement CHK008–015 | FR-001–006/048/049/059, модель выбора, anonymous-aggregate: отказ до следующей передачи, отдельные цели, повреждённый выбор запрещает необязательное измерение. |
| privacy-measurement CHK016–021 | FR-010/011/013/057, data-model §Уровень 1 и anonymous-aggregate: закрытые поля/регион, нормализация, порог 3 до суммирования, запрет связи и использования consent как аналитики. |
| privacy-measurement CHK022–030 | FR-014–025, attribution-handoff и activation-milestones: last-non-direct только среди допустимых источников, unknown/weak, точные триггеры, долговечная дедупликация, полный GET/200 отдельно от установки. |
| privacy-measurement CHK031–034 | FR-030–035/051–056, operations/research: независимый маршрут/срок, общий физический диск и приоритет защиты, точный локальный каталог, 7/минимум2, честная потеря узла. |
| privacy-measurement CHK035–038 | FR-036/039/048/050, operations §Хранение/Нагрузка, SC-011/012: явные режимы по категориям, неизвестное блокирует, baseline и 5×R измеримы. |
| privacy-measurement CHK039–045 | FR-040–047, SC-001–013, пять US, plan §Risks: набор отчётов/владелец/оговорки, исходные 093/094/096 сохранены, отдельное решение выпуска и владельцы открытого остатка. |
| infra CHK001–005 | FR-033/051/052, research §6, operations §Резервное копирование: назначение, отсутствие offsite, автоматический порядок, failed, 7 полных/минимум2 и защищённая ротация. |
| infra CHK006–010 | FR-034/035/051/053, operations §T118, quickstart7: 0≤age<26h; restore 0≤age<30d; нативное чтение и ORM/event-query, полное соответствие manifest/runtime, отказ и loss-of-all-copies. |
| infra CHK011–015 | FR-032/039/058, SC-012, operations §Нагрузка: точный p95/период/фазы, приоритет сохранения продукта; неизвестный baseline и внешний счётчик не дают ложного результата. |
| infra CHK016–021 | FR-030/031/032/054/055/056, operations §Один физический диск/Полнота входа/Независимый наблюдатель: разделены сигнал/действие, shared FS имеет отдельную защиту; owners и channel failures определены. |
| infra CHK022–025 | FR-038/039, operations §Начальные численные пределы/Полнота входа: 128GiB, рост≤0,5GiB/сутки, прогноз90суток, deadlines, неизвестное не ноль, история не удаляется. Версии/runtime привязаны; обновление не обнуляет историю. |
| security CHK001–004 | FR-007/008/048/061, legal-basis и три уровня: закрытые данные/цели, IP отдельна, отпадение основания требует остановки и отдельного удаления. |
| security CHK005–009 | FR-028/029/049/054, plan/research: PostHog/Метрика/рекламный получатель и metadata-only Telegram имеют отдельные границы; согласие, disclosure и revocation проверяемы. |
| security CHK010–015 | FR-036/048/050/061, data-model §Правило хранения, operations: явный until_decision, точные хранилища/реестр категории, deadline удаления, после restore прежняя проверка режима недействительна, truth of deletion. |
| security CHK016–020 | FR-001–006/059, anonymous-aggregate и модель выбора: explicit consent, раздельные цели, отсутствие/ошибка не разрешает, отзыв действует при новом визите. |
| security CHK021–025 | FR-037/038/047/055/060, operations §Доступ/Одобрения, plan §Risks: минимум2/MFA, version check, owners, отзыв/смена состава и отдельная правовая запись определены; выполнение остаётся операторским гейтом. |

| Повторный подсчёт после чтения | Подтверждены | Не подтверждены | Узкий гейт |
| --- | ---: | ---: | --- |
| requirements.md | 16 | 0 | PASS |
| privacy-measurement.md | 45 | 0 | PASS |
| infra.md | 25 | 0 | PASS |
| security.md | 25 | 0 | PASS |
| Всего | 111 | 0 | PASS требований |

Ранее оставшиеся рабочие проверки, T097/T106/T109–119 и реальное подтверждение
основания IP не объявляются завершёнными. Устаревшие строки tasks о разовом
разрешении на commit не применяются против более позднего общего разрешения
владельца; в этом ревью tasks не редактируется. Исторические итоги FAIL/PASS
в чек-листах сохранены как история; текущие числа получены по реальным markers.

## Контрольные суммы входа

В таблице SHA-256 исходных прочитанных файлов. Реализация ещё не проверена;
хеш smoke здесь обозначает исходный дефектный файл, а не будущий кандидат.

| Файл | SHA-256 |
| --- | --- |
| `AGENTS.md` | `24c0767f2223bb21e969079ec1ec09e0dec7c3fd3d85d02e78832f17e0775958` |
| `.specify/memory/constitution.md` | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| `docs/agent-guidance/README.md` | `2f3e0339a89d3ccdf0878026920955a189584d6a985116b069584cd78b3c75bb` |
| `docs/agent-guidance/spec-kit-flow.md` | `afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e` |
| `docs/agent-guidance/document-reading.md` | `5263860b1974df022826ac81c2482e6ee92100bc0bb718ab5a29b32e2422e411` |
| `docs/agent-guidance/development-process.md` | `1037b91f153f0757fff372e26cd05dd31433158c9c35d149125197a8a523f20d` |
| `docs/agent-guidance/product-gates.md` | `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5` |
| `docs/agent-guidance/release-and-validation.md` | `ff0d996c95101d5f782259661131db1b7528b3bf58991603f5652092e1e5256f` |
| `specs/273-paid-traffic-analytics/spec.md` | `c6b318125e90cd19018f43cecc8fced90bb22ee3e5340849d81189e520e081da` |
| `specs/273-paid-traffic-analytics/plan.md` | `01180ee8fc810d6e55547d21a06388c2dbbca98c42ac106efe868526a12c62bf` |
| `specs/273-paid-traffic-analytics/tasks.md` | `56956ae556c2cab4fc58e8c0f69e454b134ee9b59762216333363be97136a2b9` |
| `specs/273-paid-traffic-analytics/quickstart.md` | `80effe2a47bf179ab0a5e2923f84d86f1bd1527305af33534ddda549780daefc` |
| `specs/273-paid-traffic-analytics/research.md` | `f23981a8af82ecef54c793134df136e75c9ceb646d487ba5b79f84700c158b0a` |
| `specs/273-paid-traffic-analytics/data-model.md` | `4a8f615425e5448c391551bebe8128b729e4b60692ca40bfa3b62647a678151f` |
| `specs/273-paid-traffic-analytics/legal-basis.md` | `f5c8b5ea1bb2a145f438069dc64b0e3816fb46496de86aecd17d02d47db3d423` |
| `specs/273-paid-traffic-analytics/contracts/activation-milestones.md` | `ba2e86a4034a348f09f1809deac7b6e47f2e92d0152069324bc3fb0400eabbaa` |
| `specs/273-paid-traffic-analytics/contracts/anonymous-aggregate.md` | `7e10a25d64c9d94951bec8440c1c84d205e5bfc0e87f31364f0739c5357ca47f` |
| `specs/273-paid-traffic-analytics/contracts/attribution-handoff.md` | `8d5808a1bd4a1bbc6fbdbbc8cf1d301e246dd8822c25e841bef7ceaca723fd82` |
| `specs/273-paid-traffic-analytics/contracts/operations.md` | `f3a3a732e0075e3afafb0806c613fc66e71ba87c9860ab84ecd455af8ea55e5a` |
| `specs/273-paid-traffic-analytics/checklists/infra.md` | `c3ef10636f4fd977cca6231b7ba2e1396f026ce8d58fc08d7eef5f071e67207b` |
| `specs/273-paid-traffic-analytics/checklists/privacy-measurement.md` | `00a31550d0ab58f06f2712434bf915119095f3c77ca7dc099cb3c79f83513f4f` |
| `specs/273-paid-traffic-analytics/checklists/requirements.md` | `2c4a91701de2dcdb377f758064216125098bdc752e616115deb2bdb6a2607f9d` |
| `specs/273-paid-traffic-analytics/checklists/security.md` | `0db087da3daeaa31a2cb8ca3e5d24b4363111881ed391098e062c03118249921` |
| `infra/scripts/run-product-analytics-provider-smoke.sh` | `940c1fb1a3c2080d2aa3a557428c0f55a680f511742a8d4eb9081404d3d0e7cd` |
| `apps/server/tests/fixtures/analytics_operations.py` | `d92a21fd9503c7477bb0d1b3a87264a7b37d3f06674cbd079bbceed240b1f1eb` |
| `apps/server/src/twobrain_rec_server/product_analytics/provider_readiness.py` | `265cbd6a53ea08d83990bbacdd9416c74b266d2716837d3ebc193d2d64672a44` |
| `docs/prd-voice-layer-final.md` — только сверка исходного scoped-reading якоря | `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2` |
| `docs/current-product-status.md` — только сверка исходного scoped-reading якоря | `25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16` |

Все входы таблицы, кроме двух явно обозначенных hash-only якорей, прочитаны в указанном выше объёме; перед записью отчёта их содержимое повторно сверено с исходным HEAD и совпало. Проверяющий изменил только этот отчёт. Код, Git, GitHub, runtime, приложения, данные и выпуск не менялись.
