# Независимое ревью требований account-close notices

Исполнитель: `/root/f140_t068_requirements_review`, независимый проверяющий.
Дата: 2026-11-12. Рабочая копия: `/private/tmp/graf-pr7960.OlbitEdL/crisp`.
Ветка: `codex/140-account-close-notices`; исходный HEAD:
`cbdbae725e14a7c261210ca0e56f7fd9087b5b48`.
Область: F140, T070/#4926 и T068/#4922, `high-risk-product`.

Статус: независимый PASS качества требований ACN1–ACN6. Все 14 пунктов
подтверждены в указанной ниже области; блокирующих расхождений нет.
Проверяющий изменяет только этот отчёт и `checklists/account-close-notices.md`.
Изменения основного исполнителя в остальных документах сохранены.

## Собственное чтение и происхождение

Записи относятся к этому исполнителю и этому диалогу. Это чтение текущих
оригиналов, а не принятие чужого пересказа или внешней карты root.
Идентификаторы ниже — tool output chunks в текущем диалоге.

| Документ | SHA-256 | Собственное чтение |
| --- | --- | --- |
| `spec.md` | `34e3c95154181aaee5f88c75aa05d715b78519701038225f7a67451e44350310` | Последовательные исходные чтения `2a71e1`, `269a77`, `85c6e4`, `fb99c3`, `7fd552`; пропуски усечённых выдач дополнены `61ecaa` (380–415), `3a95af` (682–749), `47e3f9` (750–797), `598db5` (798–925); ACN1354–1401 — `3b1ece`. Полный документ восстановлен собственным чтением. |
| `plan.md` | `61eec1553e52d1f3302ed2b7a8615ded5493e2ef770bc8b8015b04e6c7765f5c` | Полностью, последовательные неусечённые части `f16be8` 1–245, `c7749d` 246–505, `7965d6` 506–780, `b08408` 781–1055, `dd5b49` 1056–1310, `3b1ece` 1311–1455. |
| `tasks.md` | `f95cfb943afe3e4e70ac147ada6b176ad1ab8e7ce37474e9823cadc5b8a34049` | После нового appendix заново полностью: `236e45` 1–225, `6e3330` 226–450, `b80550` 451–675, `6eea27` 676–875, `6dab0c` 876–991. Старый собственный корпус `f73a67`/`f5c60b`/`6834bf`/`ca18ea` сохранён точно как префикс; подробности повторной проверки ниже. |
| `quickstart.md` | `b8aeccc1aff13c455196b367002f3f2a73a72504e6da3a5ec81338f7127de71f` | Полностью: `f141ce` 1–275, `44eef2` 276–560, `5c5b9f` 561–850, `6a0663` 851–1130, `362c25` 1131–1405, `47e3f9` 1406–1522. |
| `docs/prd-voice-layer-final.md` | `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2` | Полностью: `86bc0a` 1–350, `bca6b8` 351–850, `499e5e` 851–1300, `d470ba` 1301–1830, `28eb7f` 1831–2300, `04a149` 2301–2474. |
| `docs/current-product-status.md` | `ac6cb05dc7a60b2c18cc21694b9ac052b4a0a60d91fb1527084e46f71e83bae2` | Полностью: `04a149` 1–290, `a0eadf` 291–560, `915f6a` 561–830, `d32210` 831–1120, `7738b3` 1121–1450, `5a65df` 1451–1800, `fb7ebd` 1801–2140, `c2fbfb` 2141–2413. Датированные исторические результаты не приняты за новую эксплуатационную проверку. |

Контроль сумм перечисленных текущих файлов: `5b8e52`. Чтение не подтверждает
код, runtime, PostgreSQL, analyze/converge, CI, выпуск, реальное письмо или issue closeout.


## Применимые основания и зависимости

Хеши повторно сверены в `70154a` и `ab3e5b`. Текущий полный договор уведомлений
прочитан в `d02448` и повторно в `2ff320`: прежняя сумма договора после правки
текста основным исполнителем не используется. Прочитанные части других
документов перечислены по области; выборочное чтение не называется полным.

| Основание | SHA-256 | Область собственного чтения |
| --- | --- | --- |
| `AGENTS.md` | `24c0767f2223bb21e969079ec1ec09e0dec7c3fd3d85d02e78832f17e0775958` | Полный исходный текст, `764687`; независимое владение checklist, запреты на изменение соседних работ и обязательная процедура. |
| `.specify/memory/constitution.md` | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` | Собственное полное чтение 1–178 `f0abfc`, 179–344 `54954e`, 345–530 `607ebe`. Последующее применимое чтение `764687` не используется как новое полное чтение. |
| `docs/agent-guidance/README.md` | `2f3e0339a89d3ccdf0878026920955a189584d6a985116b069584cd78b3c75bb` | Полностью, `61ecaa`; маршрутизация применимых правил. |
| `docs/agent-guidance/document-reading.md` | `5c3ab1f885dbf324edab70c0f4b7a5451208b3d7307c1ca7a5afdd7af0c8eb22` | Полностью, `f5c60b`; исходные документы, восстановление усечённых частей, собственное чтение. |
| `docs/agent-guidance/development-process.md` | `41fa13de8addaec6cc7c13c8be9da53c2c5527a302247d85b738f20c3155e864` | Полностью, `f5c60b`; качество требований до реализации и отдельная последующая проверка. |
| `docs/agent-guidance/codex-worktrees.md` | `d7d8c9cce8315c17efaa1da05ece80c2542ca01b966f81fb848580104b785e1d` | Полностью, `764687`; ветка и назначение проверены, чужое состояние не менялось. |
| `docs/agent-guidance/spec-kit-flow.md` | `afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e` | Собственные исходные части и дополнение `0ec868`; high-risk-product, Clarify и независимое ревью. |
| `docs/agent-guidance/product-gates.md` | `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5` | Полностью, `0ec868`; auth/privacy/deletion, честный текст и отсутствие секретов. |
| `contracts/notifications-support.md` | `d0428dd85ff9eab665a0cb7518575ad250c753f8afb88b3519548615620fc04b` | Полностью, актуальный `d02448`, повторное чтение `2ff320`; Notification matrix и весь §ACN. |
| `contracts/security-privacy-compliance.md` | `38934189b91e33a070b49e61673020d41530eec3d06a4fad5bd00f3317071cfc` | Полностью, `d02448`; защита, авторизация и граница удаления. |
| `contracts/billing-lifecycle.md` | `cd1ef81b33124b493876b236c1fe3d1f1c2bbd044de152714758d82d751c8d6b` | Полностью, `d02448`; срок отмены и прежняя семантика автопродления. |
| `research.md` | `feeff6e180079f765677d29d6f2d4f7b95b67349f74f948f04322fbc41716973` | Целые применимые R10 466–488 и ACN 888–908, `ed3650`/`624042`; не полное чтение остальных независимых исследовательских разделов. |
| `data-model.md` | `50daea566daa53cf254ad5364b6a2b007dc2d504149ee9566a9398770b86b2c3` | Целые применимые modeling/existing 215–252, AccountClosure 279–335, notifications/transaction/retention 565–644 и ACN 891–899, `ed3650`/`624042`; не полное чтение независимых моделей. |
| `specs/178-account-linking-journey/spec.md` | `7e2209a434182cae4910718472d67cfd4d98e065a87d8d048d0e799f124933ae` | Применимые FR-028 и FR-031–035 прочитаны ранее этим проверяющим; linked/merged история не даёт исходное личное право. Это не полное ревью F178. |

`.specify/feature.json` прочитан в `61ecaa`: назначение относится к F140,
ветке account-close notices и существующим T068/T070. Историческое описание
fair-use в верхнем Summary плана — редакционная неточность: активное назначение,
§ACN от 12.11.2026, договор и checklist однозначно задают нынешний срез.
Противоречия поведения или необходимости нового решения владельца нет.

## Сопоставление с существующими источниками

Чтение кода проверяет осуществимость договора и границы зависимостей;
это не приёмка ещё не написанной реализации ACN.
Пути в этой таблице — относительно корня репозитория.

| Источник | SHA-256 | Проверенный факт |
| --- | --- | --- |
| `apps/server/src/twobrain_rec_server/auth/account_closure.py` | `d8744c83b2328103ab9f0d4a320e9669903414cd97e76368a5030811ddbe4079` | Полные применимые schedule/cancel/finalization и scope helpers прочитаны; повтор активного запроса возвращается до нового создания, schedule/cancel сами не коммитят. Финализация закрывает исходную identity и фиксирует frozen scope; ACN не меняет эти решения. Основные участки 168–245/291–378 повторно видны в `7526cb`. |
| `apps/server/src/twobrain_rec_server/db/models/account_closure.py` | `0b4e0910f0b1af967c49c13dc5e6dd017b91cc562f8b37bacd88ee2bf4233ab8` | Модель прочитана полностью, `7526cb`: UUID, requester/workspace, policy/state, aware timestamps и metadata уже существуют. Новая таблица не требуется. |
| `apps/server/src/twobrain_rec_server/cabinet/web_routes/settings.py` | `1e7e6d115aece1a8566b92f4cfb5b52bb9192642f5d7f9f21c20412a2df25bd6` | Применимые `_account_close_action`, session/CSRF dependencies и caller commit/rollback прочитаны; строки 1424–1485 повторно в `7526cb`. Сервисное подключение сохраняет транзакцию действующего browser caller. |
| `apps/server/src/twobrain_rec_server/auth/account_merge.py` | `7840869e398b8f621d78c27119a7ecbba15f4f6058fac1d7f54e1dd4f598e205` | Применимые целые lock/merge sections прочитаны ранее; сохранённые ссылки на requester не означают сохранённое право после merge. Поиск `0d4226` подтверждает текущие места блокировок, а не заменяет то чтение. |
| `apps/server/src/twobrain_rec_server/workflows/worker.py` | `cc98a5e1e7c3b3dee5f44d484fcc651d5e7f2299f086b6213de15616d8cc8d01` | Применимые существующие bounded sender/claim/retry и account finalization sections прочитаны ранее; `_retry_not_before`, ≥60с/≤5, maintenance context и finalization уже являются основаниями для повторного использования. Новый ACN source gate ещё не реализован. |

Миграция `0049_account_closure_requests.py` прочитана в применимой части:
RLS допускает исходного requester или `rec_maintenance_allowed()`. План сохраняет
этот доступ, не расширяет grants/RLS. ACN-claim читает только обоснованный источник
в имеющемся maintenance context. Проверка PostgreSQL LOGIN/NOBYPASSRLS остаётся
обязательной будущей приёмкой, а не выводом из наличия такой политики.

## Матрица независимых выводов

Все ссылки здесь ведут к требованиям и будущим измеримым проверкам.
PASS в каждой строке означает достаточность соответствующего требования.

| Пункт | Основания | Независимый вывод |
| --- | --- | --- |
| CHK001 | Spec ACN1, FR-018/019; Plan §ACN sources; Data model §ACN; существующий service early return | PASS. Новые schedule и cancel — разные сохранённые события; повтор активного schedule не ставит новое письмо. После canceled создаётся новая запись/request event. Семь суток и прежняя семантика закрытия сохранены. |
| CHK002 | Spec ACN1; Plan §ACN service→outbox; Quickstart ACN п.1 | PASS. В одной транзакции сохраняются переход и очередь; read/enqueue error требует rollback обоих, sender до commit невозможен. Нет вложенного commit из notification helper. Отсутствие права/адреса отдельно разрешает сам переход без письма. |
| CHK003 | Spec ACN2; Contract §ACN; Plan recipient; F178 FR-028/031–035 | PASS. Получатель неизменен — original requested_by_user_id исходного request/workspace. Billing owner, новый Owner, linked/merged аккаунт и текущая сессия его не заменяют; следование merged_into_user_id запрещено. |
| CHK004 | Spec ACN2; Contract §ACN recipient; Plan source locks; Quickstart ACN п.3 | PASS. Active/unmerged identity, personal Workspace с исходным Owner marker, active Owner membership и active verified nonempty email проверяются при enqueue и сохранённом claim. При нескольких адресах договор задаёт детерминированный минимальный действующий адрес, не сохраняет его в outbox. |
| CHK005 | Spec ACN2/5; Contract §ACN; Research ACN | PASS. Отсутствие права/адреса подтверждается как no enqueue/terminal suppressed без переназначения или backfill; ошибка чтения не приравнивается к отсутствию. Обязательное защитное письмо не выключается optional preference; paid/billing-owner право не требуется. |
| CHK006 | Spec ACN3; полный актуальный Contract §ACN; Quickstart ACN п.2 | PASS. Scheduled/canceled описывают исторические действия, все даты берутся из исходной записи и выводятся с секундами/МСК. Поздний scheduled после canceled допустим без обещания нынешнего закрытия; текст направляет проверить текущий статус. Возобновление списаний, сессий и завершённая очистка из отмены не выводятся. Формулировка «Крайний срок отмены: …» сверена после редакционной правки. |
| CHK007 | Spec ACN3; Contract общие ссылки и §ACN; product gates | PASS. Ровно одно действие `/settings/account` на configured public origin с обычной авторизацией. Нет request/user/workspace IDs, recovery/session token, финансовых данных и meeting content в письме/ссылке. Переход по ссылке сам не отменяет закрытие, не восстанавливает доступ и не создаёт сессию. |
| CHK008 | Contract §ACN full allowlist; Data model §ACN event identity; Plan snapshot gate; Quickstart ACN п.3 | PASS. Event `account.close:<request.id.hex>:scheduled|canceled` и canonical request UUID hex связываются с original recipient/workspace. Все allowlisted aware UTC ISO dates должны точно совпадать с source; policy `account-close-v1`, interval ровно семь суток. Canceled требует state=canceled и requested≤canceled<finalize; scheduled допускает historical canceled. Некорректные/неполные/старые snapshots suppressed без восстановления текущими значениями. |
| CHK009 | Spec ACN4; Contract state/frozen scope; Plan finalization; исходный begin_account_close_finalization | PASS. До начала финализации допустимы scheduled/canceled/blocked без frozen content_workspace_ids, finalization_started_at и finalized_at. Финализация/closed запрещают новый claim. Сохранённый до финализации claim может дойти позднее; отзыву у Postal и автоматическому повтору unknown не обещается осуществимость. |
| CHK010 | Spec ACN5; Plan persisted claim; Contract retry; Quickstart ACN п.4 | PASS. До транспорта source/read/lock error и известный временный отказ Postal используют сохранённые ≥60с/≤5 попыток. Claim+counter фиксируются до HTTP; SQL locks через HTTP не удерживаются. Unknown/crash после сохранённого claim не вызывает повтор; при невозможности сохранить claim транспорт не вызывается. |
| CHK011 | Plan lock order/poll snapshot; Research ACN; Quickstart ACN п.3–4; closure/F178 source lock sections | PASS. Request→workspace→identity→membership→verified identities используют shared NOWAIT на каждой source row до delivery FOR UPDATE. Отсутствует блокирующее обратное ожидание относительно closure/F178. Mutation poll→claim не может отправить старый body; следующий poll перечитывает снимок. Принятие дизайна не заменяет будущие независимые соединения и concurrency-тесты. |
| CHK012 | Spec ACN6; Quickstart весь §ACN; исходный production browser action/service/commit | PASS. Заданы browser session+CSRF+confirmation→service→commit→outbox→обычный sender с transport stub и отдельным соединением после commit. Покрыты rollback, repeat/new request, потеря/смена прав/адреса, malformed/legacy/foreign, finalization, poll mutation, lock/concurrent sender/restart, known temporary/unknown. Настоящий worker LOGIN/NOBYPASSRLS и PostgreSQL17 обязательны. Точные исполняемые task-сценарии добавлены и независимо проверены в повторной сверке ниже; Analyze/реализация ещё не пройдены. |
| CHK013 | Spec ACN6; Tasks T068/T070; Plan/Quickstart boundary; матрица уведомлений | PASS. Исходные T068/T070 `[ ]` не сняты, другие семейства и исходы матрицы остаются отдельно. Stub не закрывает получательскую #7524, не доказывает inbox/read. Dev, выпуск, deploy и полная приёмка T068/T070 не принимаются этим ревью. |
| CHK014 | Конституция III/IV/VI и quality gates; Plan Constitution Check; Data model existing+ACN; migration0049 RLS | PASS. Используются существующие ACCOUNT_CLOSE/outbox/worker context/source model; нет новой таблицы, migration, транспорта или расширения grants/RLS. Авторизация, ручные средства capture, системный аудиопуть и прежняя семантика удаления сохранены. Только синтетические данные/transport stub; нулевой доступ к реальной почте, серверу и пользовательским данным в этой приёмке. |

## Итог и пределы допуска

Независимый PASS **качества требований ACN1–ACN6**. Требования измеримы,
совместимы с сохранёнными исходными обязательствами и достаточны для следующего
этапа: после указанной ниже повторной проверки подробных execution tasks — Analyze без CRITICAL/HIGH,
проверка существующих issues и только затем профильный RED/реализация.
Checklist прочитан после проставления evidence-backed markers и повторно после ревью tasks: **14 checked,
0 unchecked**. Это разрешение перейти к следующим проектным воротам в
назначенном объёме; это не общий допуск миновать их.

Реализация, PostgreSQL, runtime, tests, CI/common validator, Converge, реальный
transport/письмо/inbox, T068/T070 целиком, закрытие issues, Dev, выпуск и deployment
этим отчётом не проверялись и не принимаются. Ни один исходный task не отмечен
выполненным этим проверяющим. Reviewer изменил только собственный checklist и
этот отчёт, не менял код, spec/plan/tasks/research/data-model/quickstart/contracts,
Git/GitHub, сервер, данные и другие работы основного исполнителя.


## Повторная независимая проверка tasks и применимости общих чеклистов

Назначение продолжено основным исполнителем через прочитанный файл
`f140-account-close-task-review-assignment-20261112.md` во внешнем каталоге
доказательств (`33f31c`, текст назначения виден полностью до усечения выдачи
последующих объединённых документов). Область и два принадлежащих проверяющему
файла не расширялись. В этой части задача — проверка изменённого обязательного
оригинала tasks и применимости исторических ворот, а не повтор всей принятой
проверки неизменных документов.

Изменённый `tasks.md` самостоятельно прочитан **заново полностью**, строки
1–991 пятью неусечёнными частями `236e45`, `6e3330`, `b80550`, `6eea27`,
`6dab0c`. Текущий файл — 97340 байт, SHA-256
`f95cfb943afe3e4e70ac147ada6b176ad1ab8e7ce37474e9823cadc5b8a34049`.
Первые 87154 байта имеют точную прежнюю сумму
`3563aa2210ae30d1dd7cc48722b3c0e2fadcb38dc1a250b07cc682dd52c0669b`.
Собственная проверка `8c56b9` также сравнила все полные исходные task rows:
87 до/87 после, строки и отметки **точно совпадают**. Приложение добавляет
9 последовательных шагов внутри прежних T070/#4926 и T068/#4922, а не новые
канонические задачи или issues.

### Покрытие и порядок девяти шагов

| Шаг tasks appendix | Требования и самостоятельный вывод |
| --- | --- |
| 1, T068 RED | ACN1/2/6, CHK001–005/012. Проверяется настоящий browser handler с session/CSRF/literal confirmation; schedule/repeat/cancel/new schedule, три ожидаемых исторических snapshots из отдельного соединения. RED должен показать отсутствие продукта, а не ошибку импорта. Rollback включает recurring version и очередь; отсутствие права/адреса не блокирует сам допустимый переход. Отрицательные session/CSRF/role/workspace перечислены. PASS полноты проектной задачи. |
| 2, producer | ACN1/2, CHK001–005/014. После service flush нового schedule/cancel, без внутреннего commit, прежний early return сохранён. Только original requester/marker/membership/active unmerged identity/verified address; mandatory bypass, no backfill/recipient substitution. Existing event/outbox и delivery key, никаких schema/grants изменений. PASS. |
| 3, snapshot/copy | ACN3/4, CHK006–008. Строгие phase/UUID/aware UTC dates, отбрасывание неизвестных полей, некорректный снимок пустой для suppression. Исторические секунды/МСК, одна безопасная авторизованная ссылка, отсутствие ложных обещаний. Старый generic test не разрешает ослабить source proof. PASS. |
| 4, source gate | ACN2/4, CHK003/004/008/009/011. Полная связь event/request/recipient/workspace/snapshot, policy v1/семь суток, cancellation interval и state/frozen finalization признаки. NOWAIT на всех source rows в заданном порядке; delivery lock позднее. Права не расширяются. PASS. |
| 5, sender | ACN4/5, CHK005/009–011. Missing-email rows не теряются в selector; retry metadata и not-before проверяются под lock. Snapshot mutation не отправляет старый body. Source failure/known temporary имеют persisted ≥60с/≤5, unknown/crash не повторяются; claim+attempt до HTTP, locks освобождены, failed commit означает 0 HTTP. Другие семейства не меняются. PASS. |
| 6, причинная приёмка | ACN1–4/6, CHK001–009/012/013. Production browser→separate committed read→ordinary sender/локальный stub; mandatory false-preference, обе historical фазы, malformed/legacy/tampered и все source mismatch/потеря прав/финализация. Реальный ограниченный worker context и cross-tenant границы. Прямая ручная очередь не подменяет положительную цепочку. PASS. |
| 7, concurrency/retry | ACN4–6, CHK009–012. Независимые соединения удерживают каждую source row, проверяют обратный F178/closure порядок, concurrent sender и poll mutation. Transport callback видит сохранённые claim+attempt и свободные DB locks; restart/due/future/max5/unknown/crash/commit failure и invalid retry JSON перечислены без реальной почты или ожидания времени. PASS. |
| 8, профильные регрессии | ACN6, CHK012–014. Названы существующие account closure/fanout/lifecycle/notifications и затронутые account merge/sender cases; штатный focused PostgreSQL runner, без фиктивного суммирования разных прогонов. Пути существуют в текущем дереве; новый producer имеет явно назначенный путь. PASS. |
| 9, review/Converge/PR | ACN6, CHK013/014. Независимый code review, Converge, Ruff/process/diff, собственный F140 fragment, exact-SHA/currentbase три PR checks/common, открытые замечания и проверка результата merge. Temporary synthetic cleanup и сохранённые logs/hashes; Dev/release/deploy/#7524 отдельно, T068/T070 `[ ]`. PASS полноты будущих ворот, не их исполнения. |

Порядок requirements14/0→tasks→Analyze→existing issue canon/sync→RED1→
producer2→copy3→source gate4→sender5→acceptance6/7→regression8→review/converge9
согласован с принятым high-risk-product планом. Нет выполнения продукта до RED,
новой схемы/транспорта, самостоятельного коммита helper или переноса широкой
приёмки на один тест. Общие auth/worker стыки выполняются последовательно;
отдельная подготовка renderer cases допустима в указанных непересекающихся
файлах после RED. Блокирующих пропусков порядка/пути/покрытия не найдено.

### Применимость восьми исторических общих чеклистов

Каждый документ прочитан полностью из текущего оригинала: launch-readiness —
`8d7491`; operations/payments — `1bcb4f`; requirements/security/ux — `6af0e0`;
product-market — `04dd99`; post-plan — `bbb0de`. Объединённая выдача `33f31c`
была усечена, поэтому не используется как свидетельство полного чтения восьми
документов. Суммы и счётчики по фактическим checkbox rows — `8c56b9`.
Исторические текстовые подсчёты внутри документов местами отличаются от нынешних
строк; они не переписывались и не выдаются за новые результаты.

| Checklist, текущая сумма SHA-256 | Нынешние строки checked/unchecked | Применимость к ACN и сохранённые ограничения |
| --- | --- | --- |
| `launch-readiness.md` — `99268dc6ac32dab5bce0bb1303bcd26cd412a0feb9edbca2f395eb94e1d3ade5` | 32/8 | CHK005 RLS/worker и CHK007 notices durability применяются прямо: ACN2/4/5, tasks1/4–7 задают exact source/role/tenant, persisted retry/claim/restart/terminal. CHK004/024/026/039 требуют сохранить no-recovery-route, deletion precedence, authority/privacy; ACN не меняет closure/retention и не даёт session/recovery token. Открытые CHK017/018/021/022/033/040 относятся к чужим payment/refund/storage/full-launch условиям: ACN их не разрешает, не реализует и не использует как основание. Global launch PASS не выдан. |
| `operations.md` — `ed75a8c7f5c89cbc651894d08380a48058cba42bcb30475e04089a870460c665` | 10/8 | CHK007 notification dedup/failure применим: event identity, persisted count/claim, suppression/retry/failed/unknown заданы. Общая открытая CHK002 о gap owner/status/resolution не закрыта этим локальным sender; ACN требует видимого состояния прежней очереди, не отменяет полный incident lifecycle. Открытые registry/emergency-money/refund/renewal CHK001/003/008/011/013/015/017 и реальные canary/approvals остаются отдельными; нет новых money operations или разрешения production enablement. |
| `payments.md` — `b3cc064b5ce60e31b62ae7d68982591b771b568a8dead0e4713b63121a30a10f` | 14/6 | Применимы atomic recurring refusal CHK016 и разделение событий от money truth: tasks1 требует rollback recurring version, ACN не меняет FR018/103, отмена closure не обещает восстановления consent/charges. Срез не создаёт платежей, grants, refunds/receipts или planned invoice intervals. Открытые CHK006/009/011/014/017/020 и FR105 implementation не принимаются. Для двух защитных historical фаз эти внешние коммерческие решения не требуются; regressing отказ от будущих списаний запрещён. |
| `post-plan-readiness.md` — `9c4390640741935e0cd0a3f8651f586679ac5c5dcde0f3ab1250b64d7bb2e869` | 25/15 | CHK001/019/029 lifecycle/deletion/role loss, открытые CHK031/036 и notice/recovery часть CHK038 применимы: tasks1/4–7 покрывают atomicity/source rights/CSRF/tenant failure/unknown и finalization; источник не получает нового пути восстановления. Без schema/money/UI changes нет зависимости от открытых storage values/refund/renewal rows. Широкие outage/operations/full cross-artifact CHK031/034/036/038/040 не сняты: принят только конкретный ACN исходный договор, а не все подсистемы. |
| `product-market-2026.md` — `68219e884c21a06a149da841689c265f473fc5855cdb12d5df346d218aa44873` | 36/4 | CHK018 различает account close/cancel/payment/refund, CHK027/028/030/033/034 требуют scope/truth/safe next action/privacy/deletion; ACN3 и tasks3/6 выполняют эти требования к тексту проекта. Открытые CHK001/008/009/019 (segment, packaging/WTP, refund consistency) не закрыты и остаются launch blockers. Защитные письма не продают тариф, не меняют цену и не заявляют public launch; целевой сегмент/WTP не условие данного source gate. |
| `requirements.md` — `6ce78a75d5e3b0bc533aaacc90fa9555761a812f1f41d042c8e95a207cbd90c9` | 17/8 | Открытые CHK002/012 по actors/tenant/CSRF/privacy прямо применимы, решены лишь для ACN через исходного requester/Owner/personal marker/active verified identity, sender source proof, actual LOGIN/RLS и safe content. CHK009/011/015 также соблюдаются: errors/unknown, capture/deletion, ограничения launch. Остальные открытые CHK014/017/018/019/023/025 остаются вне изменяемых money/storage/launch процессов, глобально не принимаются. |
| `security.md` — `e1210f57cdb45dd5a5599a766a332380e61e601357cd40cb69ef1be117aa5b31` | 11/6 | Открытые CHK001/002 trust/Owner/tenant и CHK003/006/007/010 прямо применимы: browser CSRF/session/confirmation, original source privileges повторно до claim, неизменные grants/RLS, safe URL/copy и честная deletion boundary. CHK016 про post-closed refund recovery не расширяет ACN: после finalization/closed новый claim запрещён, /settings/account обычная авторизация без recovery session. CHK009/012/017 не дают новых audited money/refund/emergency полномочий; глобальные пробелы не сняты. |
| `ux.md` — `5d22f9cd06e10527505bd0c8ccb44890ec5d7d49368880894b19bc05a6230080` | 17/3 | CHK002/004/005/009 применяются к понятным historical phases/датам/одному действию/правдивым обещаниям, CHK007/008 сохраняют доступный существующий маршрут. Нового экрана, asset или layout нет; форма/CSRF/confirmation и ссылка сохраняют прежний путь. Открытые CHK013/016/020 про renewal/storage/refusal outcomes не оцениваются как законченные. ACN не обещает current billing state или восстановление списаний и не даёт приёмки T079/manual UX/Dev. |

Все восемь списков суммарно содержат **162 checked / 58 unchecked** по текущим
строкам; это инвентаризация, а не новая общая приёмка. Ни одна отметка этих
восьми файлов не менялась. Ссылки на старый T075 BLOCK относятся к датированной
проверке другого проекта/среза; здесь не утверждается исправление всех B1–B3
или X4–X7. Там, где общий вопрос прямо применим к ACN, его текущая конкретная
формулировка независимо сопоставлена с ACN/tasks выше. Неснятого препятствия
именно для проектного ACN source/copy/sender среза не найдено. Все исходные
эксплуатационные, финансовые, ручные и публичные условия сохраняются.

Итог повторной проверки: **PASS требований и детализации задач ACN1–ACN6;
account-close checklist 14 checked / 0 unchecked**. После правок он полностью
перечитан ещё раз. Analyze/issue canon/sync по-прежнему обязательны до кода.
Нового implementation/runtime/PostgreSQL/CI/inbox/launch PASS нет.
