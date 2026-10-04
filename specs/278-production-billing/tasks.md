# Tasks: F278 — полноценная оплата GRAF

Источник: spec.md, plan.md, data-model.md, contracts/billing.md, quickstart.md. Ветка codex/278-production-billing. Режим high-risk-product + release-deploy. Независимое ревью требований: 32/32, review-report.md; это не отметки реализации. Все задачи ведёт основной агент; внешний трекер GitHub #7285. Коммит реализации только после проверки и явного одобрения.

## Phase 1: Подготовка

- [X] T001 Зафиксировать исходные проверки, безопасные исходные настройки и состояние окружения в `specs/278-production-billing/investigation.md`, сверить действующие требования и независимый review; секреты не сохранять. FR-032/033. (Issue #7307; [GitHub](https://github.com/yshishenya/graf/issues/7307))

## Phase 2: Денежная основа

- [X] T002 Написать падающие проверки каталога, расчёта сегментов, бюджета, уникальности и RLS в `apps/server/tests/unit/test_billing_purchases.py` и `apps/server/tests/integration/test_billing_purchase_storage.py`: 20→100→20, бонус, границы/округление, конкурирующие резервы. FR-007/019–025/032/034/040. (Issue #7308; [GitHub](https://github.com/yshishenya/graf/issues/7308))
- [X] T003 Добавить модели, экспорт и миграцию `apps/server/src/twobrain_rec_server/db/models/billing.py`, `db/models/__init__.py`, `db/migrations/versions/0100_billing_purchases.py`: каталог места, grants, quotes, бюджет/резервы, future selection и бонусный снимок; ограничения/индексы/RLS и безопасная совместимость. FR-019/022–025/032/034/040. (Issue #7309; [GitHub](https://github.com/yshishenya/graf/issues/7309))
- [X] T004 Реализовать расчёты денежных сегментов, проекцию места и бюджет в `apps/server/src/twobrain_rec_server/billing/purchases.py`, `billing/storage_addons.py`, `billing/catalog.py`; минимум карты ≥100 копеек в `config.py`; проверить фундамент T002 на PostgreSQL. FR-007/017/019–025/034/040. (Issue #7310; [GitHub](https://github.com/yshishenya/graf/issues/7310))

## Phase 3: US1 — понять цену до оплаты (P1)

Независимая проверка: выбор месяца/года и места без отправки денег показывает обычную цену, скидку, сроки, следующий состав и не устаревает молча.

- [X] T005 [US1] Добавить проверки server quote, stale price/state/promo/expiry, назначений согласия и одинаковой суммы в `apps/server/tests/integration/test_billing_purchase_quotes.py`, `apps/server/tests/contract/test_billing_purchase_ui.py`. FR-001–005/016/019/025. (Issue #7311; [GitHub](https://github.com/yshishenya/graf/issues/7311))
- [X] T006 [US1] Встроить серверный quote и единый расчёт состава/дат в `billing/purchases.py`, `cabinet/web_routes/billing.py`, `cabinet/templates/cabinet/pages/billing_checkout_content.html`, `billing_plans_content.html`, существующие публичные условия `public/`; сохранить базовые цены и независимые согласия. FR-001–005/015/016/019/025/031. (Issue #7312; [GitHub](https://github.com/yshishenya/graf/issues/7312))

## Phase 4: US2 — купить и получить услугу один раз (P1)

Независимая проверка: созданная операция переживает двойной POST, потерянный ответ, webhook/poll в обратном порядке, неверные атрибуты и отказ без второй оплаты.

- [X] T007 [US2] Добавить отрицательные и восстановительные проверки в `apps/server/tests/integration/test_billing_purchase_journey.py`, `apps/server/tests/unit/test_billing_purchase_observation.py` и `apps/server/tests/unit/test_billing_money_path_e2e.py`: amount/currency/id/metadata/shop/test, unknown, повтор, receipt, бюджет/код, межпространственные запросы. FR-005–010/016/017/027/032/034/041. (Issue #7313; [GitHub](https://github.com/yshishenya/graf/issues/7313))
- [X] T008 [US2] Расширить промокампании по назначению/пространству/бюджету, атомарное резервирование и CLI в `billing/promotions.py`, `billing/purchases.py`, `apps/server/scripts/manage_promo_campaign.py`, `cabinet/web_routes/billing.py`; начальная покупка тоже расходует бюджет. FR-006/007/016/017/032/034/036. (Issue #7314; [GitHub](https://github.com/yshishenya/graf/issues/7314))
- [X] T009 [US2] Реализовать общую проверку ответа/диспетчеризацию выдачи и восстановление в `billing/reconciliation.py`, `billing/webhook_reconciliation.py`, `billing/entitlements.py`, `billing/maintenance.py`, `cabinet/web_routes/billing.py`; все назначения, никаких новых POST для unknown. FR-007–010/022/025/027/031/041. (Issue #7315; [GitHub](https://github.com/yshishenya/graf/issues/7315))

## Phase 5: US3 — управлять подпиской и продлением (P1)

Независимая проверка: одно досрочное сохранённое списание добавляет полный следующий период; отмена и поздний успех сохраняют доступ без нового согласия, календарные окна не догоняются.

- [X] T010 [US3] Добавить проверки составной цены, досрочной оплаты, отмены/late success, resume в −12ч и окон/границ в `apps/server/tests/integration/test_billing_purchase_journey.py` и `apps/server/tests/unit/test_billing_renewal_workflow.py`, `apps/server/tests/unit/test_renewal_charge.py`. FR-011–015/024/025/039/041. (Issue #7316; [GitHub](https://github.com/yshishenya/graf/issues/7316))
- [X] T011 [US3] Реализовать составное/досрочное продление и единую следующую попытку в `billing/renewal_charge.py`, `billing/purchases.py`, `billing/entitlements.py`, `cabinet/web_routes/billing.py`, `cabinet/templates/cabinet/pages/billing_subscription_content.html`, `billing_overview_content.html`; не включать согласие после отмены, не применять future downgrade раньше. FR-011–015/024/025/039/041. (Issue #7317; [GitHub](https://github.com/yshishenya/graf/issues/7317))

## Phase 6: US4 — купить и управлять местом (P1)

Независимая проверка: каждый объём×месяц/год, пропорциональная доплата, предоплата/бонус, отложенное уменьшение и загрузка одновременно сохраняют деньги/права.

- [X] T012 [US4] Добавить проверки покупки/отложенного выбора/отмены, late storage, одновременной загрузки и истечения в `apps/server/tests/integration/test_billing_purchase_storage.py` и `apps/server/tests/contract/test_storage_addon.py`. FR-018–026/040/041. (Issue #7318; [GitHub](https://github.com/yshishenya/graf/issues/7318))
- [X] T013 [US4] Реализовать storage preview/purchase/schedule/cancel в `cabinet/web_routes/billing.py`, `cabinet/templates/cabinet/pages/billing_storage_content.html`, `billing/purchases.py`; показать общий объём, весь последовательный срок и следующую цену. FR-018–025/040. (Issue #7319; [GitHub](https://github.com/yshishenya/graf/issues/7319))
- [X] T014 [US4] Подключить временную проекцию grants/бонуса к выдаче, чтению лимита, нормализации и допуску загрузок в `billing/entitlements.py`, `billing/maintenance.py`, `billing/referral_rewards.py`, `billing/storage.py` и существующих API/сервисах чтения WorkspaceSubscription; проверить 80/95/100%, очистку/экспорт без удаления при снижении. FR-022–026/040/041. (Issue #7320; [GitHub](https://github.com/yshishenya/graf/issues/7320))

## Phase 7: US5 — результат, помощь и понятный интерфейс (P1)

Независимая проверка: историю/операцию и поддержку можно открыть после каждого исхода; чек/письмо не выдают за деньги, суммы и действия доступны в нужных размерах/темах.

- [X] T015 [US5] Добавить проверки названий операций, помощи, ошибок, фокуса, клавиатуры и отсутствия секретов в `apps/server/tests/contract/test_billing_purchase_ui.py`, `apps/server/tests/browser/billing-accessibility.test.cjs`. FR-027–032; SC-005/007/009. (Issue #7321; [GitHub](https://github.com/yshishenya/graf/issues/7321))
- [X] T016 [US5] Завершить историю/детали/статусы и однократные уведомления в `billing/history.py`, `billing/notifications.py`, `billing/events.py`, `cabinet/web_routes/billing.py`, `cabinet/templates/cabinet/pages/billing_*`; отдельная блокирующая сверка истёкшего storage с incident owner/review_by. FR-009/010/027–032/037/041. (Issue #7322; [GitHub](https://github.com/yshishenya/graf/issues/7322))
- [ ] T017 [US5] Устранить подтверждённое ограничение холодного запуска в `scripts/dev-harness.py` с проверками `tests/governance/test_graf_local_adapter.py`; проверить вручную браузер и единственный GRAF Dev, темы/360px/200%/VoiceOver/клавиатуру и три независимых прохождения; исправить недопонимания, записать факты в `specs/278-production-billing/acceptance-matrix.md` и `validation.md`. FR-029/030; SC-007–009. (Issue #7323; [GitHub](https://github.com/yshishenya/graf/issues/7323))

## Phase 8: US6 — реальные деньги и открытие продаж (P1)

Независимая проверка: тестовые деньги отделены от боевых; сумма всех реальных списаний ≤200 ₽, каждый платёж сопоставлен с услугой/чеком/зачислением.

- [X] T018 [US6] Расширить проверяемую процедуру запуска и ограниченной акции в `docs/runbooks/billing-launch.md`, `apps/server/scripts/manage_promo_campaign.py`; согласованный состав Q3, сохранённая карта, бюджет, прекращение акции/автопродления, отдельное последовательное test-shop окно. FR-031–039. (Issue #7324; [GitHub](https://github.com/yshishenya/graf/issues/7324))
- [ ] T019 [US6] Провести настоящий тестовый магазин, webhook/GET/receipt, отказ сохранённой карты, три окна и граничные суммы по `specs/278-production-billing/quickstart.md`; записать безопасные доказательства в `validation.md`, не выдавать MockTransport за провайдера. FR-006–017/033/038/039. (Issue #7325; [GitHub](https://github.com/yshishenya/graf/issues/7325))
- [ ] T020 [US6] Подготовить проверенный точный кандидат и выполнить допущенный выпуск по `docs/agent-guidance/release-and-validation.md`: обязательные GitHub checks/release-full, резервная копия/восстановление, dry-run, человеческие условия runbook; результаты в `validation.md`. FR-031/033/037; SC-010. (Issue #7326; [GitHub](https://github.com/yshishenya/graf/issues/7326))
- [ ] T021 [US6] Провести ограниченные реальные подписку/место/досрочное продление, подтвердить чеки и банковское зачисление, внешние возвраты по runbook, закрыть акции/автопродление и только затем открыть продажи; раздельные результаты A03/A21/A27/A42–46 в `specs/278-production-billing/acceptance-matrix.md`. FR-033–039; SC-003/010/011. (Issue #7327; [GitHub](https://github.com/yshishenya/graf/issues/7327))

## Phase 9: Общая проверка и завершение

- [X] T022 Выполнить локальную денежную/БД/контрактную/браузерную матрицу без пропуска новых файлов; анализ и convergence реализации по high-risk-product, без незакрытых critical/high, результаты и обязательную оставшуюся живую/ручную приёмку в `specs/278-production-billing/validation.md`. FR-001–041; SC-001/004–007/009/010. (Issue #7328; [GitHub](https://github.com/yshishenya/graf/issues/7328))
- [X] T023 Подготовить русский фрагмент `changes/unreleased/F278.yaml`, связи задач/issues/PR и локальные доказательства, запросить одобрение конкретного проверенного коммита, явно оставить внешнюю приёмку открытой до её завершения. FR-033/035/037; SC-010/011. (Issue #7329; [GitHub](https://github.com/yshishenya/graf/issues/7329))

- [ ] T024 После T017/T021 сверить каждую обязательную строку A01–A46, SC-001–011 и доказательства точного выпуска, завершить `specs/278-production-billing/validation.md`, синхронизировать и закрывать связанные issues только по правилам closeout. FR-001–041; SC-001–011. (Issue #7330; [GitHub](https://github.com/yshishenya/graf/issues/7330))

## Порядок и зависимости

T001 → T002 → T003 → T004. Далее US1 T005→T006 → US2 T007→T008→T009. Для US3 T010→T011 и US4 T012→T013→T014 — после US2, последовательно из-за общих файлов. US5 T015→T016→T017 после денежных путей. US6 процедура T018 следует после US2–4; T019 после реализации и локального T022; T023 и готовый проверенный коммит до T020. T020 включает предусмотренное runbook последовательное тестовое окно на установке; только затем T021. T022 запускается до T019/коммита; финальная матрица T024 закрывается после T017/T021. Ни один цикл не требует живых платежей для допуска локального кода.

Тестовые задачи сначала фиксируют ожидаемый провал новых требований, затем реализация и повтор. Отметка задачи тестов означает соответствующее проверяемое покрытие, а не обязательный успех до реализации. Зависимость модели при сборе нового теста разрешается после зафиксированного отсутствия реализации.

## Параллельность и стратегия

[P] не ставится: платёжные истории разделяют routes/entitlements/purchases, одновременная запись дала бы конфликт. Пример допустимой параллельной проверки после кода: unit расчётов и браузерный контракт; PostgreSQL concurrency запускается внутри отдельного теста с двумя транзакциями. US1–US6 реализуются последовательно, каждая проверяется отдельно; ранний частичный результат не открывает production. Полный выпуск ждёт денег/ручной приёмки/внешних доказательств по установленному порядку, без фиктивного закрытия задач.

## Phase 10: Convergence

Сверка 2026-09-26: просмотрены FR-001–041, SC-001–011, 32 сценария US1–US6, семь решений реализации plan.md и семь принципов конституции. Новых доказанных противоречий кода не найдено; четыре неполные обязательные группы не позволяют объявить полное соответствие. Это условия приёмки, не доказательство четырёх дефектов. Последующие задачи сохраняют связь с исходными T017/T019–021/T024, не заменяют и не закрывают их.

- [ ] T025 [HIGH] Завершить ручную проверку браузера и единственного GRAF Dev, VoiceOver и три самостоятельных прохождения после подготовки проверенного коммита; записать факты и исправления в `specs/278-production-billing/validation.md` и `acceptance-matrix.md`, совместно с T017/T024, per FR-006/030, SC-008/009, US5/AC4 (partial). (Issue #7332; [GitHub](https://github.com/yshishenya/graf/issues/7332))
- [ ] T026 [HIGH] Подтвердить настоящий тестовый магазин, сохранённую карту, чеки, уведомления и календарные окна по `specs/278-production-billing/quickstart.md`; результаты в `validation.md` и A10–24/A26–31/A37/A43, совместно с T019, per FR-006–014/033/039, plan: настоящий test shop (partial). (Issue #7333; [GitHub](https://github.com/yshishenya/graf/issues/7333))
- [ ] T027 [HIGH] После явного одобрения проверенного коммита получить проверки точного SHA, допуск операторов, резервное восстановление, dry-run и выпуск; сохранить доказательства в `specs/278-production-billing/validation.md`, совместно с T020/T023, per FR-033/037, SC-010, Constitution V/VI (partial). (Issue #7334; [GitHub](https://github.com/yshishenya/graf/issues/7334))
- [ ] T028 [HIGH] Провести четыре боевых платежа по quickstart.md: исходный поднабор Q3 (месяц, пакет, досрочное продление) плюс год с одним пакетом, ожидаемо до 150 ₽ в общем пределе 200 ₽, сверить услугу/чек/банковское зачисление, обязательные внешние возвраты, закрыть акции и автопродление, затем принять все A01–46; результаты в `specs/278-production-billing/validation.md` и `acceptance-matrix.md`, совместно с T021/T024, per FR-034–039, SC-002/003/011, US6/AC1–5 (partial). (Issue #7335; [GitHub](https://github.com/yshishenya/graf/issues/7335))

## Локальная отметка выполнения 2026-09-26

T001–T016/T018/T022 отмечены по исходникам и локальной проверке, см. validation.md, E1–E11 и code-snapshot.json. Это не закрытие GitHub issues или выпуск. T017/T019–021/T023–028 остаются открытыми; T023 подготовлен до обязательного явного одобрения коммита. Для T007/T010 реальные тестовые пути уточнены: сценарии собраны в общем HTTP/БД наборе, без пустых дублирующих файлов. После convergence работа implement продолжена для отчёта и конкретного кандидата; внешние доказательства не выдумываются.

## Phase 11: Утверждённые пакеты хранения

- [X] T029 [US4] Внедрить FR-019 от 2026-09-27: 5 ГБ в базе, 0–99 пакетов +5 ГБ по 250/2500 ₽, каталог/миграцию 0101 в `apps/server/src/twobrain_rec_server/db/migrations/versions/`, серверный расчёт и защиту старых цен в `billing/catalog.py`, `billing/purchases.py`, `billing/renewal_charge.py`; формы количества и состав покупки в `cabinet/`, условия в `public/`. До кода — независимое ревью изменённых требований; затем проверки количества/каталога/миграции/сохранения прав/старых цен/продлений и полного пути в `apps/server/tests/`, обновление `validation.md` и фрагмента F278. Старые локальные доказательства не подтверждают новую сетку. Не включает выпуск или реальные списания. (Issue #7347; [GitHub](https://github.com/yshishenya/graf/issues/7347))

Локальная отметка T029: 608 проверок общей матрицы и 83 проверки продления/пакетов (наборы пересекаются), браузерные 72 сочетания и статические проверки пройдены. Новая схема локально реализована; выпуск, внешняя приёмка и поступление денег остаются в T017/T019–021/T023–028. Подробности — validation.md.

- [ ] T030 [US6] Закрыть выявленный при подготовке выпуска пробел ограниченного окна FR-033/034/037: серверный список разрешённых пространств в config.py, billing/operations.py, cabinet/web_routes/billing.py и billing/renewal_charge.py; единая настройка трёх служб и минимум карты 100 копеек в infra/docker-compose.yml и infra/env/rec.production.env.example и корректная публичная доступность. Проверить прямой HTTP, пустой/чужой список, отключение, неверную конфигурацию и подготовленное продление до POST; сохранить сверку/историю/отмену. Обновить процедуру выпуска и доказательства перед новым коммитом. (Issue #7350; [GitHub](https://github.com/yshishenya/graf/issues/7350))

Отметка T023 от 2026-09-28: пользователь явно поручил довести выпуск и боевую приёмку до конца; проверенные коммиты и PR #7349 подготовлены с разрешением на дальнейший выпуск. Фрагмент, связи и локальные доказательства готовы. Внешние T017/T019–021/T024–028 остаются открытыми. Заключительные исправления ревью и точные результаты — validation.md.

Уточнение T030 от 2026-09-28: код и автоматические проверки завершены и выпущены в v2026.09.28.1. Задача остается открытой до фактической проверки одинаковой настройки служб и ограниченного окна после выпуска, как требуют исходные критерии issue #7350. Согласованная настройка трех служб уже подтверждена; само платное окно еще не открывалось. Это исправление преждевременной отметки, без расширения исходного объема. Архивный фрагмент выпуска сохраняет историю поставленного кода.


## Phase 12: Convergence

Срез 2026-10-04 ограничен FR-027/028/031/032 и US5/AC2. Доказанный пробел HIGH/partial: успешный платёж с pending-чеком исключается из всех последующих фоновых кандидатов. Остальные открытые задачи живой/человеческой приёмки сохраняются и не закрываются этим исправлением.

- [ ] T031 [HIGH] [US5] Восстанавливать отложенный чек успешной покупки через проверенный GET в `apps/server/src/twobrain_rec_server/billing/webhook_reconciliation.py`: только pending-чек, первые 24 часа фонового наблюдения, затем явное обновление владельцем через `cabinet/web_routes/billing.py`; сохранение оплаченного доступа/бюджета/отмены, проверки всех видов покупок, неверной суммы/магазина, повторов и выключенного checkout в `apps/server/tests/unit/test_billing_purchase_observation.py` и `apps/server/tests/integration/test_billing_purchase_journey.py`. Перед реализацией независимое ревью чеклистов и analyze; затем локальная проверка, русский фрагмент, точные PR/release gates и наблюдение годового чека в production. per FR-027/028/031/032, US5/AC2 (partial). (Issue #7512; [GitHub](https://github.com/yshishenya/graf/issues/7512))

Дополнительные критерии T031 после независимых замечаний PR: восстановление чека существующей `succeeded_projected` доплаты без новой выдачи; незавершённая оплата имеет приоритет при ограниченной очереди; проверка чека возвращает на сведения этого же счёта и показывает фактическую регистрацию/ожидание/ошибку. Требуются отрицательные/повторные проверки с сохранением финансовых данных и отдельное подтверждение нового проверенного коммита перед фиксацией.

Дополнительный критерий T031: pending-чек уже оплаченного terminal `succeeded_refused` обновляется только чтением. Обязательны фон/позднее ручное действие/отсутствие владельца с сохранением service gap, нулевой выдачи прав, отключённого согласия и финансовых полей. Список существующих paid terminal states сверяется с producers в purchases/entitlements/maintenance; нетерминальные финансовые операции не переводятся в receipt-only только по invoice.status.


Дополнительные проверки T031: справедливое чередование двух pending-чеков при limit=1 через время подтверждённого чтения; поздняя receipt-only проверка действующим owner после реальной смены billing_owner_id, без финансовых полномочий и без раскрытия чека/контакта/карты прежнего плательщика.

Уточнение T031: тест поздней смены владельца вызывает настоящий grant_confirmed_renewal и использует produced succeeded_refused/workspace_scope_invalid; ошибочные сочетания исключаются. Чередование receipt-попыток работает также после HTTP/validation отказов и rollback, не регистрируя чек и не меняя финансовые данные.
