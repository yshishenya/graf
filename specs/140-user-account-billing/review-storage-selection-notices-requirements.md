# Независимое ревью требований SSN1–SSN7

Дата: 12.11.2026. Проверяющий: `/root/f140_storage_selection_requirements`.
Полоса: **high-risk-product**. Рабочая копия
`/private/tmp/graf-f140-storage-selection-20261112`, ветка
`codex/140-storage-selection-notices`, исходный Git SHA
`5c0184f61edaf28341a9b76f472b6b25a7c24928`.

**PASS только качества требований подтверждений выбора хранилища и его отмены:
15 отмечены / 0 открыты. Блокирующих замечаний к этой версии требований нет.**
Это самостоятельное ревью текста, схемы источника, границ и будущей приёмки;
реализация, тесты и выпуск не проверялись.

## Предмет и происхождение чтения

Проверены SSN1–SSN7 существующих US9/P2 T070/#4926 и T068/#4922.
Все обязательные инструкции, конституция, PRD, текущий статус, product-gates,
активные spec/plan/tasks/quickstart/research/data-model, договор уведомлений,
security/privacy и F031 RLS matrix прочитаны проверяющим полностью. Полное
собственное чтение и SHA-256 записаны сразу после завершения документа в
`f140-storage-selection-reviewer-reading-20261112.json` внешнего каталога
`/Users/yshishenya/Documents/Codex/2026-11-01/graf-f140-final-failure/`.
После сжатия контекста проверены происхождение и совпадение всех ранее
записанных сумм; применимые разделы восстановлены из оригиналов. Усечённые
первые выводы не принимались за полное чтение: выпавшие участки spec/plan
прочитаны отдельно, ссылки перечислены в журнале. Карта применимости там же.

Исходники просмотрены только для проверки осуществимости проекта: HTTP
preview и confirm/cancel в cabinet/web_routes/billing.py, создание/потребление
quote и storage_price_snapshot в billing/purchases.py, модели BillingOperation
и BillingPurchaseQuote. Это предметное чтение выбранных функций, а не
полное ревью исходников или проверка действительных прав PostgreSQL.

Действующие F278 US4/FR017–023/039–041 задают базу 5 ГБ, пакеты по 5 ГБ
до 500 ГБ и сохранение prepaid/bonus прав. Scope Summary F140 и текущие
разделы F272/F199 заменяют старые цены, одну попытку, emergency stop, runtime
launch registry и brand-distance. Исторические требования не восстановлены.
Конституция I/II/III/IV/VI/VII и product-gates сохраняют capture safety,
metadata-only evidence, правдивое удаление, независимую реализацию и отдельные
ворота. Новых сторонних материалов, таблиц, миграций, служб или транспорта
проект не вводит. Другие исторические ссылки не объявлены текущей приёмкой.

## Результат каждого вопроса

| Пункт | Итог и проверенное основание |
| --- | --- |
| CHK001 | Достаточно. Spec SSN1, Plan SSN «два callers», Quickstart SSN1–2 разделяют подтверждённый schedule, действительную отмену, повтор consumed quote и пустой no-op. Проверка версии идёт до no-op; устаревшая вкладка не отменяет новый выбор. Оба перехода увеличивают post-version только при реальном действии. |
| CHK002 | Достаточно. SSN1/2 и Plan SSN предписывают source+outbox в одной caller-транзакции без внутреннего commit. Подтверждённое отсутствие права/email сохраняет действие без доставки; read/write/enqueue error откатывает всё. Quickstart SSN2/4/5 предусматривает различие и rollback. |
| CHK003 | Достаточно. SSN2 и Plan source gate требуют исходного active/unmerged personal Owner, workspace owner marker, active Owner membership, subscription.billing_owner_id и active verified непустой ExternalIdentity до enqueue и повторно до сохранённого claim. Минимальный email/id выбирается из действующих адресов; адрес не сохраняется в payload. |
| CHK004 | Достаточно. SSN2/5, договор SSN и Plan явно сохраняют mandatory preference bypass, неизменного адресата, запрет следовать merge/новому Owner и отсутствие backfill. Optional threshold/helper не используется как финансовая authority. |
| CHK005 | Достаточно. SSN3, договор SSN и Model scheduled связывают момент подтверждения, исходные/выбранные точные bytes, month/year, полную принятую RUB цену и ends_at с сохранённым quote. Даты представимы в Europe/Moscow и показываются с секундами/МСК; цена — точные копейки. Текст исторический, не обещает нынешний лимит, новую попытку/успех/чек. |
| CHK006 | Достаточно. SSN4 и Model canceled сохраняют время отмены и удалённый положительный объём без новой цены/consent, invoice или provider action. Catalog не требуется; оплаченные интервалы/grants не пересчитываются. Исторический canceled/current объём не насильно приводится к новой лестнице. Это согласовано с F278 FR019/023/040 и no-op. |
| CHK007 | Достаточно. Договор SSN задаёт отдельные закрытые поля scheduled/canceled, canonical UUID/decimal/UTC ISO8601, int32 version, bigint bytes/amount, rejection bool/float/sign/leading zero, представимость Москвы и effective>saved. Новое target — 5–500 ГБ с шагом 5 ГБ; неизвестные поля отбрасываются, неполная схема даёт пустой снимок для suppression. Единственный action_path=/billing/storage на public origin, без ids/token/денежных параметров; контакты/provider/meeting content запрещены. |
| CHK008 | Достаточно. Model SSN и Plan source gate связывают scheduled operation succeeded/storage_schedule/provider_id=None с consumed quote purpose/workspace/Owner/key purchase:<quote.id>, полным request_snapshot==quote.snapshot, pre-version и post=pre+1. operation.created_at задаётся тем же UTC now подтверждения и лежит в исходном полуоткрытом quote-окне. Base/add-on/cycle/target/RUB/полная сумма сверяются из принятого snapshot без нынешнего каталога. Canceled имеет ровно четыре типизированных поля, actor/post-version/старый объём, отдельный storage-cancel key и отсутствие invoice/consumed quote. |
| CHK009 | Достаточно. SSN5 и Plan допускают более позднюю доставку исторического события после применения/нового выбора, но запрещают новый claim при утрате исходных полномочий, closed/merged либо признаках начала финализации у исходного requester. Cooling само по себе не финализация. История не обещает отзыв уже claimed POST; Quickstart SSN4/5 проверяет границы. |
| CHK010 | Достаточно. Plan и договор SSN требуют нового чтения source в отдельной claim session и сравнения полного poll tuple workspace/recipient/event/payload/template/channel с locked delivery. Mutation не отправляет старый body. Malformed snapshot/retry metadata подавляется, source SQL/lock error даёт durable retry, commit failure запрещает transport. Старую очередь не достраивают из текущего состояния. |
| CHK011 | Достаточно. SSN6/Plan/договор задают сохраняемый интервал не менее 60 секунд, максимум пять суммарных попыток, durable attempt+failed/postal_outcome_unknown до HTTP, проверку future due и запрет автоматического replay unknown/crash после claim. Known retryable Postal failure сохраняет тот же предел. Quickstart SSN5 требует отдельного соединения до callback, restart и отказа commit. |
| CHK012 | Достаточно. Plan фиксирует shared NOWAIT source order operation→quote при scheduled→workspace→subscription→identity→membership→verified identities→существующие closure requests исходного requester, затем delivery FOR UPDATE. NOWAIT на каждой source строке исключает обратное блокирующее ожидание workspace-first financial/identity-first merge writers. Claim commit освобождает все locks до HTTP; Quickstart предусматривает конкуренцию/NOWAIT/poll mutation/finalization. Это проект проверки, не доказательство фактических блокировок. |
| CHK013 | Достаточно. SSN7 и Quickstart SSN1–6 требуют настоящего HTTP preview→consent confirm→cancel, caller commit, нового PG session и ordinary sender; положительный producer нельзя подменять enqueue. Матрица содержит месяц/год/base/add-on/downgrade/prepaid/bonus/below-floor, исторический каталог, no-op/stale version, rollback, source/recipient/RLS, concurrency/finalization, known/unknown/restart/commit errors. Реальные LOGIN/NOBYPASSRLS/FORCE RLS и только синтетика/stub заданы явно. |
| CHK014 | Достаточно. Model/Research/Plan SSN используют existing quote/operation/outbox, новую отмену как succeeded no-money kind без invoice/provider/consumed quote, один явный стык monitoring.OPERATION_KINDS. Широкий audit не получает сумму/письмо. Прежний maintenance billing_reconciliation и tenant RLS не расширяются; никаких новых таблиц/миграций/framework/транспорта. Этого достаточно для проекта; PostgreSQL и monitoring regression ещё обязательны. |
| CHK015 | Достаточно. SSN7, конец Plan/Quickstart и исходные task rows сохраняют T068/T070 открытыми, общую матрицу/FR107/O16 и paid-upgrade/method-required/transient-purge вне этого результата. #7524 требует реального получения; Dev/release/deploy имеют собственные ворота. Требования не используют Fixes/Closes и не обещают закрытие исходных issues по частичному срезу. |

## Применимость исторических чеклистов

Полностью перечитаны пять общих списков. Их файлы и markers не менялись.
Подсчёт ниже вычислен по фактическим строкам, а не скопирован из старых
текстовых итогов: у ux и post-plan-readiness некоторые исторические
итоговые абзацы сохраняют прежние числа после более позднего X7.

| Список | Фактические отмечены / открыты | Применимость к SSN и оставшаяся граница |
| --- | --- | --- |
| requirements.md | 17 / 8 | CHK002/012: исходный Owner/scope/auth/RLS; CHK009/017: no-op/errors/storage history; CHK011/013: safety и честный русский текст; CHK014/015: отдельные внешние ворота. SSN уточняет только уведомления; refund/renewal/full-storage/pricing/launch конфликты общего списка не принимаются. |
| security.md | 11 / 6 | CHK001–004/006–007/009–011: browser недоверенный, текущая роль/CSRF, минимальные существующие права, safe payload и audit, account close. Нового operator correction/refund/encryption пути нет; общие открытые пункты остаются. |
| ux.md | 17 / 3 | CHK002–005/007–009/012: историческое действие, точные bytes/копейки/МСК, один доступный авторизованный переход и честные ошибки. Новый экран/редизайн/assets не вводятся. Старый browser-only CHK006 заменён F210/F278; письмо ведёт на разрешённый кабинет, без восстановления старого ограничения. Ручная доступность/визуальная приёмка не подтверждаются. |
| operations.md | 10 / 8 | CHK004/007/009/010/012: новый известный no-money kind, bounded durable delivery, dedup и отдельные launch gates. Полные money/reconciliation/observability/runbook/recipient gates остаются. Удалённый emergency stop не восстанавливается. |
| post-plan-readiness.md | 25 / 15 | CHK004/014/019/025/029/031/033/034/036/037/039/040: existing storage truth, сохранение prepaid/bonus, closure/merge, ошибки/конкуренция/RLS и честные безопасные тексты. Принимается лишь эта конкретная SSN-проекция; полная F140, общие конфликты X4–X6 и эксплуатационная матрица не закрываются. |

Прежние узкие ревью threshold/ACN/fair-use являются историей соседних
срезов, не основанием автоматически отметить SSN. Новый список проверен
отдельно по текущим источникам; их claims реализации или фактической приёмки
этим отчётом не подтверждены.

## Первоначальный контроль версии до детализации

На момент ревью tasks.md байтово совпадает с HEAD; содержит все 87 исходных
task rows, T068/T070 остаются `[ ]`. Детализации SSN в нём ещё нет по
согласованному порядку. Данный PASS разрешает её подготовить, после чего
требуется повторное независимое чтение добавленных шагов/зависимостей и
Analyze перед любым исходным кодом. Остальные product-файлы проверяющий
не менял.

| Файл F140 | Байт | SHA-256 проверенной версии |
| --- | ---: | --- |
| `spec.md` | 232651 | `5357b3242da42a947cef5e654117a3472548cfaa8e628cde555f38e544db81bb` |
| `plan.md` | 143952 | `57c597b5ec4880de831cc616b4b817472159cc8f843b724f1f584ea97a7fb099` |
| `research.md` | 87012 | `5ebda730d41934a03067c9c9d47e32e041455e6048b27245653f40eb3313b271` |
| `data-model.md` | 73084 | `85500a2611fb282dccb5105cff78ea0c453c62edc81dc29446f319070b4b4e1e` |
| `quickstart.md` | 143878 | `8c398019695d93d3cf4bc82d8e7cd22558f655175361c6703a3cebdb26503f2e` |
| `contracts/notifications-support.md` | 29588 | `7b9ed1c0734cbdefc23c3670bf13b08bd9d1ff48970fa4788a905166137f1610` |
| `tasks.md` | 97340 | `f95cfb943afe3e4e70ac147ada6b176ad1ab8e7ce37474e9823cadc5b8a34049` |

Проверяющий изменил только собственный checklist и этот отчёт; внешний JSON
хранит provenance чтения. Финальный checklist повторно читается после записи,
контрольный подсчёт должен быть 15/0. Отчёт относится к этим шести design
версиям и текущему исходному tasks, не только к общему Git SHA. Любая
существенная правка требований требует повторного независимого допуска.

**Непроверенные ворота:** детализация SSN tasks/Analyze, RED/GREEN и полная
предметная PostgreSQL/RLS/конкурентная приёмка, независимое ревью кода/Converge,
точные head/base/CI/PR, фактическое получение #7524, GRAF Dev, выпуск и
развёртывание. Тесты, службы, браузер, платежи и почта проверяющим не запускались.

## Повторное независимое ревью tasks после PASS требований — 12.11.2026

**PASS детализации SSN: девять подшагов достаточны, блокирующих замечаний нет.
Итоговый чеклист SSN сохраняет 15 отмечены / 0 открыты.** Теперь проектный
результат включает текущий tasks ниже. Первоначальные утверждения выше о
байтовом совпадении всего tasks с HEAD и отсутствии детализации относятся
к предыдущему этапу; эта новая проверка их заменяет для продолжения.
Analyze, реализация и фактическая приёмка по-прежнему впереди.

Назначение повторного ревью прочитано из внешнего
`f140-storage-selection-tasks-review-assignment-20261112.md` (вывод81badb).
Полностью самостоятельно прочитан изменённый tasks.md: выводы99783d
(1–260), bba6e7(261–540),2953db(541–820),dfe698(821–1135). Усечения нет.
Чтение сразу зарегистрировано в прежнем собственном readingJSON.
Проверены текущие hashes всех ранее принятых design docs/инструкций:
изменился только tasks; подтверждённый корпус требований остаётся тем же.

Проверенная версия tasks: **1135 строк,110317 байт**, SHA-256
`27ebc76d23e885803123f9da65d02a229b139ee4bce1a89f289fe2ffd08acf36`.
Добавление содержит144строки/12977байт. Первые97340байт совпадают с HEAD
буквально и имеют SHA-256
`f95cfb943afe3e4e70ac147ada6b176ad1ab8e7ce37474e9823cadc5b8a34049`.
Все87 исходных полных task rows вместе с markers совпали; T068/T070 `[ ]`.
Новых task IDs или самостоятельных issues не добавлено.

| Подшаг tasks | Сверка с требованиями и проектом |
| --- | --- |
| 1 — RED | SSN1/2/7: настоящий HTTP preview/consent confirm, deferred schedule/cancel, отдельный committed read и ordinary sender, исходный Owner/mandatory, no-money. Запрещено принять collection/import error вместо предметного RED. PostgreSQL17/runtime LOGIN/NOBYPASSRLS/FORCE RLS и штатный bootstrap/runner названы; RED предшествует изменениям продукта. |
| 2 — producer | SSN1/2/4, Model/Plan: оба действительных callers заменяются новым небольшим source модулем, сохранены quote/consent/price/blocker checks и ранний repeat. UTC now подтверждения и полуоткрытое окно, post-version=pre+1, проверка версии до no-op. Canceled — отдельный succeeded no-money source с закрытыми четырьмя полями/key/временем, без каталога/invoice/consumed quote/provider. Caller commit, rollback при ошибке и no-backfill при отсутствии получателя указаны; monitoring получает только новый известный kind. |
| 3 — parser/text | SSN3/4/6, договор SSN: обе фазы, точные типы и canonical формы, int32/bigint границы, target5–500ГБ/шаг5ГБ и исторические current/canceled, effective>saved, UTC/МСК/секунды/копейки, suppression неполного snapshot. Безопасный /billing/storage и правдивые исторические утверждения; canceled не выдумывает цену/дату/будущие права, next_attempt_label не вводится. |
| 4 — source/recipient | SSN2/5, Model/Plan: source identity/kind/state/key/provider, consumed quote/Owner/version/window, полное равенство snapshot и RUB/base+addon проверяются из исходной истории. Закрытый canceled source, исходный active/unmerged Owner/marker/membership/billing_owner/current verified address, отсутствие перенаправления, финализация и cooling разделены. Shared NOWAIT source order до deliveryFORUPDATE и прежние RLS/maintenance context названы; optional threshold helper не выдаётся за mandatory authority. |
| 5 — claim | SSN5/6: полный poll tuple сравнивается с locked delivery, mutation не отправляет старый текст. Missing/malformed/source read-lock ошибки разделены, retry≥60с/≤5 и future due проверяются под lock. Durable failed/unknown+attempt и commit до HTTP, commit failure→0transport, locks освобождены; known failure повторяется ограниченно, unknown/crash/restart после claim автоматически нет. Соседние families сохраняются. |
| 6 — причинная приёмка | SSN7/Quickstart1–4: обе фазы от browser источника, repeat/no-op/stale/new selection, rollback, месяц/год/base/add-on/decrease/bonus/prepaid/below-floor и catalog failure/history. Recipient/identity/email/source/tenant/context/финализация/legacy damage включены; ручной delivery допустим лишь для отрицательного повреждённого входа. Paid rights не меняются ради уведомления. |
| 7 — конкурентная приёмка | SSN5/6/Quickstart5: независимые соединения/NOWAIT на существенных строках, обратные финансовый/merge/finalization порядки, два sender, poll→claim mutation; в callback видны сохранённые attempt/unknown и свободные locks. Future/due/max5/invalid JSON/known/unknown/crash/restart/commit rejection/потерянный ответ commit названы без реальной сети или ожидания часов. |
| 8 — регрессии | SSN7/Quickstart6: названы существующие purchase journey/storage/quotes, monitoring PostgreSQL/unit, notification renderer и соседние sender/storage cases. Новый no-money kind не становится unrecognized или деньгами. Узкий runner, запас диска, отдельные результаты/хеши/cleanup без фиктивного суммирования заданы. |
| 9 — завершение среза | Spec Kit/SSN7: независимое ревью кода, Converge, профильные проверки, собственный fragment, Refs4922/4926, точные head/currentbase/три GitHub checks/common validator/замечания/штатный merge/readback. Dev/release/deploy/#7524 отдельно, T068/T070 открыты, #7899 последняя. |

Порядок зависимостей согласован: requirements15/0→повторное tasks review
→Analyze→сверка существующих issues→RED1→producer2→parser3→source gate4
→sender5→acceptance6/7→regression8→review/converge9. Общие billing.py/worker.py
изменяются последовательно. Указанная возможность отдельно готовить renderer
unit cases после RED не отменяет общего порядка и не требует новых агентов.
Минимальный результат содержит обе фазы; проект не обещает независимость
положительной T068 от ещё не сделанной T070.

Проверка путей выполнена чтением файловой системы (вывод28c781): все названные
существующие source/test/runner/bootstrap/validator/fragment пути найдены.
`billing/storage_selection_notifications.py` отсутствует, что согласуется с
явным поручением создать новый модуль, а не является потерянной зависимостью.
Полное содержимое тестовых файлов этой проверкой не рецензировалось;
существование пути не приравнивается к наличию или прохождению сценария.

Повторно подтверждена байтовая неизменность относительно HEAD восьми
исторических чеклистов. Это контроль сохранности, не новая общая приёмка:

| Чеклист | SHA-256 | Отмечены / открыты |
| --- | --- | ---: |
| `requirements.md` | `6ce78a75d5e3b0bc533aaacc90fa9555761a812f1f41d042c8e95a207cbd90c9` | 17 / 8 |
| `security.md` | `e1210f57cdb45dd5a5599a766a332380e61e601357cd40cb69ef1be117aa5b31` | 11 / 6 |
| `ux.md` | `5d22f9cd06e10527505bd0c8ccb44890ec5d7d49368880894b19bc05a6230080` | 17 / 3 |
| `operations.md` | `ed75a8c7f5c89cbc651894d08380a48058cba42bcb30475e04089a870460c665` | 10 / 8 |
| `post-plan-readiness.md` | `9c4390640741935e0cd0a3f8651f586679ac5c5dcde0f3ab1250b64d7bb2e869` | 25 / 15 |
| `storage-notices.md` | `fce41d115b2b619d21368f103be6a4ff912a4a73beb727cc3b661f63732296ff` | 14 / 0 |
| `fair-use-operator.md` | `cbb2b3b488114741e769373fe2833d85db798ae6043a81d6dd185e21934b10db` | 19 / 0 |
| `account-close-notices.md` | `4d869a227feec3993ac18c35192b50653048cc34740967dc03d4b279e869c393` | 14 / 0 |

Сохранённый PASS даёт продолжить Analyze и проверку существующих issues.
Он не принимает код, SQL authority/locking, результаты RED/GREEN, CI точного
SHA/актуальной базы, реальное получение #7524, GRAF Dev, выпуск/развёртывание,
полные T068/T070/FR107/O16 или остальные исходные условия. Проверяющий
не запускал тесты, SQL, Docker, приложения, службы, почту и платежи.
