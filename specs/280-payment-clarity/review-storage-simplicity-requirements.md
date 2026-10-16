# Независимая проверка требований простого хранения

Дата: 2026-10-15. Ветка: `codex/280-storage-simplicity`. Область: FR-053–056, T062–064. Проверка требований до реализации, независимо от автора. Владелец отчёта изменил только этот файл и `checklists/storage-simplicity.md`; code/spec/plan/tasks/GitHub/commits/release/deploy не менялись. Чужие изменения сохранены.

## Вердикт

**REQUIREMENTS PASS — 7 отмечено, 0 не отмечено.** Блокирующих пробелов или противоречий требований в этом ограниченном срезе не найдено. Этот результат не означает завершённой реализации, проведённой проверки браузером, смены почты, денежного действия или готового выпуска. Анализ и сопоставление с issues остаются отдельными воротами до реализации.

## Основания по пунктам

| Пункт | Конкретное основание |
| --- | --- |
| CHK001 | FR-053 задаёт первый блок «занято из общего объёма», одно главное действие владельца и вторичное действие записей. FR-055 помещает историю в закрытое нативное раскрытие. FR-002/004 и уточнение15.10 задают иерархию и один уровень подробностей. `reference-subscription-krisp.md` указывает наблюдаемый краткий Plan Details, источники и пределы исторического наблюдения; уточнение15.10 называет официальные повторно прочитанные источники, независимый код/ресурсы GRAF. |
| CHK002 | FR-054 явно разделяет включённые5ГБ, дополнительный шаг5ГБ, каталожную стоимость только дополнения месяц/год и общий тариф. Эти цены не равны списанию сегодня; точная доплата за все оставшиеся оплаченные интервалы остаётся в существующем серверном превью. FR-003/006/007 не позволяют спрятать финансовые условия перед подтверждением. Plan запрещает переписывание расчёта/каталога. |
| CHK003 | Quickstart15.10 перечисляет5/10/15/500ГБ, month/year, нулевую/максимальную цену дополнения, отсутствие каталога, prepaid/bonus, будущее уменьшение при выключенной оплате. FR-055 требует различимый бонус внутри истории, видимые будущий объём и отмену даже при отключённой оплате; неизвестная цена и неподходящий тариф не дают ложного платного действия. |
| CHK004 | FR-053 сохраняет unavailable без чисел и шкалы, явный stale,80/95/100%, резервы, free/exhausted и owner/member privacy. FR-055 сохраняет ввод при ошибке промокода. Quickstart перечисляет эти ветви плюс receipt missing; FR-011 и план сохраняют role/CSRF/quote/идемпотентность, неизменные денежные проверки и модель. |
| CHK005 | Действующий FR-012 определяет WCAG2.2AA, фокус/клавиатуру, контраст,320px/200% и обе темы. Plan15.10 и quickstart требуют Chromium/WebKit, desktop/320px, темы, клавиатуру, контраст, no-JS и причинный RED/GREEN; названы существующие contract suites и PostgreSQL storage harness. FR-055 требует рабочий выбор/расчёт без JS. Конкретный результат проверки ещё не заявлен. |
| CHK006 | FR-056 задаёт existing authenticated link/verify/unlink, proof нового ящика, защиту последнего способа входа и запрет прямой подмены verified/email в БД. Quickstart отдельно охватывает конфликт/merge preview без автослияния, сохранение user/subscription/записей и primary/receipt/notification. Старые документы не переписываются, контакты/коды не сохраняются в tracked evidence, владелец вводит код на сайте. |
| CHK007 | Plan15.10 требует новый exact-SHA/base PR CI, frozen Full, CD dry-run/execute, runtime/public evidence. T064 оставляет T011/T012/umbrella открытыми до соответствующих фактов. Подтверждение пользователем поступления денег явно отделено от доставки нового письма; новые списания не требуются. FR-015/016 и исторические чеклисты сохраняют независимые source/UX/browser обзоры, человеческую приёмку и метрики отдельно. |

## Конституция и действующие ворота

Прочитаны `.specify/memory/constitution.md`, `docs/agent-guidance/README.md`, `spec-kit-flow.md`, `product-gates.md`, применимые участки baseline/current status и `reference-subscription-krisp.md`. Противоречий требованиям независимого кода, происхождения ресурсов, доступности, видимых существенных условий, защиты auth/tenant/CSRF и честных границ удаления/денег не найдено. Изменение тарифа, схемы или финансовой модели не требуется и не разрешено этим срезом. Новые проверочные пункты оценивают качество требований; прежние отметки не принимаются за новое выполнение кода или выпуск.

Все существующие checklists прочитаны как gate; ранее отмеченные пункты и исторические пояснения не переписаны. Текущие механически пересчитанные состояния:

| Checklist | checked | unchecked |
| --- | ---: | ---: |
| `invoice-consistency.md` | 16 | 0 |
| `optional-renewal.md` | 10 | 0 |
| `payment-return.md` | 17 | 0 |
| `promo-inline.md` | 16 | 0 |
| `promo-presentation.md` | 6 | 0 |
| `promo-refresh.md` | 9 | 0 |
| `provider-rejection.md` | 10 | 0 |
| `requirements.md` | 8 | 0 |
| `storage-simplicity.md` | 7 | 0 |
| `subscription-clarity.md` | 14 | 0 |
| `ux-payment.md` | 18 | 0 |

## Отпечатки проверенных документов

| Файл | SHA-256 |
| --- | --- |
| `spec.md` | `f2d82072be049fb5e1aaed780a500d577dd7e67ff16d8e67f22df21a78dc88df` |
| `plan.md` | `decc32efd0cc82c83fa95ce39d63572b3ac2aff508900e0dd1ad1b538589f65f` |
| `tasks.md` | `c9c8efbddc3f46a6deba413c33cb28b0a1a3aaf337e7c996e66ef072ae608d74` |
| `quickstart.md` | `8526687e312d4e56febd400b2a7e0c6671c82e2fd3e99a029874b75954a26b49` |
| `analyze-storage-simplicity.md` | `ea53082f4c8ca59899f835d41cb2a47068f7bcdef98bf44de8d48086850ce783` |
| `reference-subscription-krisp.md` | `4433254abe7be2894ec5459eb9f5912316bd45ff164e19952b3b22d776c51966` |

После записи перечитан весь итоговый `storage-simplicity.md`: **7 `[x]`,0 `[ ]`**. Неотмеченных пунктов и блокирующих замечаний нет. Последующие проверки реализации, issue sync, независимые source/UX/browser обзоры, convergence и выпуск не выполнены этим обзором.

Повторное чтение после issue sync: T062→#7598,T063→#7599,T064→#7600 присутствуют в актуальном `tasks.md`; новый mapping не меняет содержание требований. Отпечатки tasks/analyze обновлены после чтения, checklist повторно проверен:7/0, PASS сохраняется.


## Независимое обновление обзора 2026-10-16

**REQUIREMENTS PASS — checked 7 / unchecked 0.** Ветка `codex/280-storage-simplicity`, активная область FR-056–059 / T066–068. Исторический текст обзора от 15 октября, таблица его SHA-256 и его старые номера выше сохранены без правок; они описывают прежний снимок. Это обновление оценивает только качество требований и согласованность механической перенумерации. В этом обновлении reviewer изменил только `checklists/storage-simplicity.md` и настоящий отчёт; реализацию, spec/plan/tasks, GitHub, commit, release/deploy не менял.

### Карта и доказательство механической замены

| Прежний номер | Актуальный номер | Значение |
| --- | --- | --- |
| FR-053 | FR-056 | Использование и состояния хранения |
| FR-054 | FR-057 | Цена дополнения, полный тариф и точная доплата |
| FR-055 | FR-058 | Раскрытие истории, будущий объём и безопасные состояния |
| FR-056 | FR-059 | Штатная смена почты с подтверждением владения |
| T062 | T066 | Упрощение использования и выбора места, #7598 |
| T063 | T067 | Проверка восстановления почты, #7599 |
| T064 | T068 | Проверки и выпуск хранения, #7600 |

Сохранённый manifest `storage-renumber-2026-10-16.json` прочитан из локального каталога доказательств текущей задачи. Для spec/plan/tasks текущие SHA-256 совпадают с `after`; обратная одновременная замена идентификаторов и диапазонов даёт точное побайтовое совпадение с `before` для всех трёх файлов. Для исходной части analyze результат тот же: её SHA-256 после перенумерации `ed548abe7ac9c7da1926c5971d6e9e3b54e609db992198396e7875240e09268c`, а обратная замена восстанавливает прежний `ea53082f4c8ca59899f835d41cb2a47068f7bcdef98bf44de8d48086850ce783`. В текущем analyze дополнительно прочитан отдельный раздел «Сверка номеров 2026-10-16»; итоговый отпечаток включает его. Quickstart и reference не изменились относительно исторических отпечатков.

В актуальном `tasks.md` определения задач уникальны: 64 определения без повторов, в том числе T066/#7598, T067/#7599, T068/#7600. Определения FR в spec также уникальны, четыре новых требования — FR-056–059. Область хранения не занимает зарезервированные повторным аудитом T062–065 / FR053–055 / SC018. Старые номера в исторических частях настоящего отчёта и в явной карте перенумерации не являются действующими определениями. Внешние заголовки/содержимое issues reviewer не изменял и не подтверждает: их синхронизация выполняется оператором отдельно. Неразрешённых коллизий в проверенных текущих документах хранения не найдено.

### Повторные основания по каждому пункту

| Пункт | Основание текущего допуска |
| --- | --- |
| CHK001 | FR-056 задаёт порядок и главное действие; FR-058 — закрытую историю; общие FR-002/004, уточнение15.10 и неизменённый reference задают иерархию и независимые ресурсы. |
| CHK002 | FR-057 по-прежнему разделяет включённые5ГБ, стоимость дополнения, общий тариф и точную серверную доплату; FR-003/006/007 и plan сохраняют финансовые условия и расчёт. |
| CHK003 | FR-058 и неизменённый quickstart покрывают month/year,5/10/15/500ГБ, prepaid/bonus, будущий объём и отмену при выключенной оплате, неизвестную цену и неподходящий тариф. |
| CHK004 | FR-056 сохраняет unavailable/stale,80/95/100%, резервы, exhausted/free и owner/member; FR-058 сохраняет ввод промокода; FR-011 и plan сохраняют role/CSRF/quote/идемпотентность. |
| CHK005 | FR-012 сохраняет WCAG2.2AA, клавиатуру/фокус, контраст,320px/200% и темы; FR-058 — выбор и расчёт без JS; plan/quickstart называют Chromium/WebKit, PostgreSQL harness и причинные RED/GREEN. |
| CHK006 | FR-059 требует штатные authenticated link/verify/unlink, доказательство нового ящика и защиту последнего входа; quickstart сохраняет аккаунт/подписку/записи, раздельные receipt/notification contact, запрет автослияния и контактов/кодов в отчётах. |
| CHK007 | T068 и plan требуют новый exact-SHA/base PR CI, frozen Full, CD dry-run/execute и runtime/public evidence; T011/T012/umbrella не закрываются без фактов. Поступление денег не доказывает новую доставку. FR-015/016 отделяют независимые обзоры от людей и метрик. |

Перечитаны конституция7.1.0, guidance index, `spec-kit-flow.md`, `product-gates.md`, применимые участки baseline/current status, активные spec/plan/tasks/quickstart, analyze, reference и собственный checklist. После точной обратимой замены требований новых противоречий применимым воротам не обнаружено. Остальные checklists не изменялись; механический пересчёт по-прежнему даёт прежние значения из таблицы от 15 октября (в сумме **131 checked / 0 unchecked**, включая7/0 текущего checklist), без заявления о повторном исполнении их исторических проверок.

### Отпечатки текущих документов после перенумерации

| Файл | SHA-256 на 2026-10-16 |
| --- | --- |
| `spec.md` | `4d5b47b9d67c9b776321088703830b894a42fbb441756e1c216046f3f53a57e8` |
| `plan.md` | `40a71971b755b3254341e48e2fb3b08f165a307adfe94c6312532a9faefc8367` |
| `tasks.md` | `eb93d07abcd2837797431edef297e7cbe52aab8888742e1572cf93f7451e74c3` |
| `quickstart.md` | `8526687e312d4e56febd400b2a7e0c6671c82e2fd3e99a029874b75954a26b49` |
| `analyze-storage-simplicity.md` | `9de617a360cd7bc8c345082ef5b6ed6ca3ada86113f5e6de9136c9f3bda56b65` |
| `reference-subscription-krisp.md` | `4433254abe7be2894ec5459eb9f5912316bd45ff164e19952b3b22d776c51966` |

После записи reviewer перечитал полный обновлённый checklist: **7 `[x]`, 0 `[ ]`**. Неподтверждённых пунктов и блокирующих пробелов качества требований нет. Этот PASS ограничен требованиями; выполнение кода/регрессий/обзоров реализации, синхронизация GitHub, смена почты, доставка, движение денег, человеческая приёмка и выпуск остаются вне результата обзора.

## HOLD операторского восстановления, 2026-10-16

Прочитаны actual `.dev/storage-simplicity/account-recovery-remote.py`, закрытые read-only account/scope snapshots и текущий FR operator scope. Частные идентификаторы/адреса не копируются. Скрипт не запускался и не менялся; БД/GitHub/коммиты/выпуск не изменялись.

**Текущий gate: HOLD — checked6 / unchecked1. CHK006 не подтверждён. Запись в рабочую БД запрещена до устранения замечаний и повторного обзора.** Предыдущие PASS относятся к обычному link/verify/unlink сценарию и не доказывают новый административный обход. Явное согласие владельца позволяет операторский recovery, но не доказывает корректность сохранения данных.

### HIGH R1 — creator-встречи не переходят к сохраняемой учётке

Закрытый source-scope подтверждает47 встреч, созданных source в сохраняемом paid workspace. Скрипт проверяет лишь83 total и отсутствие встреч в personal source workspace, а затем помечает source merged; `Meeting.created_by_user_id` не меняет. `cabinet/meeting_titles.py:51` требует точного creator для переименования; `cabinet/summary_sharing.py:174` требует точного creator для отправки итогов; `cabinet/access.py:545` определяет owner по точному совпадению. Общего разрешения merged lineage в этих guards нет. Total83 и финансовый hash не доказывают сохранение личных прав на эти47 встреч.

Минимальное решение: до alias перехода под блокировками выделить точный набор source-created встреч, убедиться, что они только в сохраняемом workspace, проверить отсутствие конфликтов `(workspace, creator, local_recording_id)`, перенести mutable creator ownership на survivor, сохранив содержимое/meeting IDs/workspace и исторический аудит. Проверить не только количество, но целостность набора и creator ACL. Уточнить это отличие живого владения от исторических audit rows в операторских требованиях.

### HIGH R2 — inactive email не означает запрет входа в survivor

Скрипт только ставит старой email identity `is_active=False`, оставляя её на active survivor. `_get_or_create_email_user` в `cabinet/web_routes/auth_email_flow.py:1045–1093` специально выбирает inactive email identity у active пользователя и после настоящего email proof снова включает её. Следовательно, заявленные отключение недоступных методов и новая защита доступа не обеспечены: очередное владение старым ящиком снова откроет paid survivor. Это отличается от OAuth inactive subject, который callbacks.py отклоняет.

Минимальное решение для ограниченной операторской операции: сохранить старую email identity и provider_subject/email/verified, но привязать её к merged source alias и оставить inactive, либо использовать уже существующий доказанный механизм запрета старого входа. Не подделывать proof и не удалять историю. Отрицательная проверка настоящего email lookup должна доказать, что старый адрес больше не выбирает survivor; новый verified Yandex identity остаётся на survivor. Старый Yandex subject inactive также должен оставаться недоступен.

### MEDIUM R3 — неполная классификация пользовательского владения и locks

Snapshot агрегирует все ссылки на source, включая47 upload_sessions и4 meeting_share_grants, но не различает живого владельца/получателя и исторического actor. Оригинальный merge переносит активные grantee grants, comment identity, preferences и join offers; `_lock_merge_domain_rows` дополнительно блокирует mutable eligibility rows. Новый скрипт использует read-only `_merge_preview_from_db` без этих domain locks и переносит только templates. Нулевые preview counts относятся к personal source workspace, а не к47 source-created встречам в paid workspace. `ingest/sessions.py:81/234` и `ingest/parts.py:53` используют точный created_by для upload resource.

Решение: повторить узкую read-only инвентаризацию по конкретным FK columns/status/workspace, оставить исторические audit/financial rows неизменными, обработать либо доказанно исключить все живые owner/grantee rows. Терминальные upload rows можно сохранить как историю только с явным доказательством отсутствия продолжаемого ресурса; иное требует переноса scoped ownership. Активные share grants/preferences/comments/offers переносить существующим совместимым путём с collision rules либо остановить при обнаружении. Применить существующие доменные locks или доказать эквивалентный барьер перед preview/проверками; не выводить безопасность только из users/workspaces lock и totals.

### MEDIUM R4 — несогласованный номер операторского требования

Текущий spec уже использует FR-056 для usage, FR-057 для цены, FR-058 для history и FR-059 для email. Новый заголовок «FR-056: явное уточнение владельца» ошибочно связывает operator recovery с UI. Исправить заголовок/связи на действующий FR-059 и обновить plan/tasks/analyze для operator scope, сохранив исторические отчёты как исторические. Reviewer сам canonical файлы не меняет.

### Что уже достаточно определено

Разрешение владельца явно описано; существующий verified Yandex proof не подделывается, ожидаются backup/dry-run rollback/operator audit, paid survivor/workspace сохраняются, role owner/member конфликт снимается явно, деньги не списываются. Выбор maintenance account_merge входит в allowlist tenant context. Эти положительные свойства не закрывают R1–R4. После исправлений нужны actual dry-run rollback, финансовые hashes/paid-through/набор данных/ACL/receipt/notification assertions и послеcommit проверка; ни один из этих результатов этим обзором не заявлен.

Проверенный исходный скрипт SHA-256: `b31adc74f1f3181c4b4df07f16eb4041e6c3224deb5ab23a7c6f0bbaecf2c180`. После обновления чеклист перечитан:6 `[x]`,1 `[ ]`; текущий operator gate HOLD.

## Повторный операторский обзор — корпоративное владение, 2026-10-16

Прочитаны обновлённый скрипт, `dry-run-result.json`, column-level/source-state/scope snapshots, backup/restore proof и код merge/identity/creator guards. Уточнение:83 встречи находятся в оплачиваемом personal workspace;47 source-created встреч находятся в отдельном corporate workspace с79 встречами. Прежнее утверждение «47 в paid workspace» было ограничено первоначальной неточной классификацией snapshot и этим уточнением исправлено. Частные идентификаторы в отчёт не включены.

- **R1 закрыт для проверенных байтов:** scoped47 Meeting creators и47 UploadSession owners переносятся в survivor только внутри corporate workspace. PostgreSQL constraints сохраняются; дополнительные template/calendar collision checks работают. Набор содержимого/ACL/финансовых данных сравнивается хэшами до/после за исключением явно переносимых ownership columns и updated_at. Counts personal83/corporate79/empty0 сохранены.
- **R2 закрыт:** оба старых метода переносятся inactive на merged alias; новый existing verified Yandex identity переносится на active survivor без изменения provider_subject/email/verified. В dry-run старый email lookup по обычным предикатам имеет0 кандидатов, новые receipt/notification соответствуют новой подтверждённой identity. Обычный старый OAuth subject также inactive. Все active sessions и устройства отзываются.
- **R4 закрыт:** операторское уточнение теперь FR-059, corporate/personal разграничение и перенос live ownership записаны в spec. FR-059 operator уточнение является прямым исключением из обычного self-service link/proof сценария; фиктивных callbacks/OTP/sessions нет.
- **R3 частично закрыт:** используются canonical root/domain locks, read-only inventory разделяет реальные FK columns, terminal invitations остаются историей. Однако предоперационная generic FK проверка разрешает таблицу целиком. Поэтому новый `meeting_share_grants.grantee_user_id=source` не остановит apply: таблица разрешена по creator column, но grantee не переносится; preview добавляет grant лишь в fingerprint, не как blocker. Текущий snapshot grantee0 не заменяет fail-closed проверку перед записью. Требуется column-level allowlist живых и исторических ссылок или явные отрицательные assertions всех непереносимых live owner/grantee columns. Ожидаемые membership status также явно должны быть active. **Текущий gate HOLD сохраняется, CHK006 unchecked; checked6/unchecked1.**

Реальный dry-run на текущем варианте завершил rollback, а не commit. Резервный dump проверен по размеру/контрольной сумме; restore выполнялся изолированно с `--network none`, вывод показывает восстановленные корневые таблицы и `isolated_restore_verified`, временный стенд удалён. Значение backup_verified в wrapper остаётсяFalse, apply не подтверждён. Эти факты не подменяют окончательный pre-apply gate или послеоперационный re-read.

SHA-256 скрипта этого refresh: `baefd28386d6a262a1f0a424c38777598771110cebcf5e60fe71c681c9d40efa`. Реализация/прод запись reviewer не изменялись.

## Окончательный операторский обзор, 2026-10-16

**REQUIREMENTS/OPERATOR PRE-APPLY PASS. Checked7/unchecked0; применимых незакрытых critical0/high0/medium0.** Review касается только подготовленной ограниченной операции по прямому запросу владельца. БД reviewer не изменял, удалённый скрипт не запускал, apply не подтверждён.

R3 закрыт после повторного чтения actual bytes: `HISTORICAL` и `CONTROL` теперь отображают table→точный набор разрешённых columns; `OWNERSHIP` разрешает только designated mutable column. Любой nonzero FK к source в иной column вызывает abort. В частности, новый `MeetingShareGrant.grantee_user_id=source` больше не проходит из-за того, что creator column этой таблицы разрешён. Это устраняет обнаруженный недостающий fail-closed случай. Проверяется ровно4 memberships и active у всех четырёх; source personal owner и corporate member, survivor personal/corporate owner дополнительно проверяются существующими preview/root shape checks. Canonical root/domain locks сохранены.

R1/R2/R4 повторно подтверждены на окончательных байтах: corporate47 creator/47 upload ownership переводятся на survivor с неизменными IDs/workspaces/содержимым и действующими constraints;83 personal и79 corporate встреч сохраняются. Templates и остальные явно перечисленные owner resources переходят без blanket FK rewrite; historical accepted_by/inviter/audit/finance остаются. Новая Yandex identity остаётся verified по прежнему proof; старые методы inactive на merged alias не выбирают active survivor в обычном email lookup. Новый receipt/notification контакт проверяется отдельно от исторических документов. Operator audit отличается от обычного proof-bound merge; ложных callback/OTP/session записей нет. FR-059 прямо описывает корпоративное владение и административное исключение.

Прочитан новый dry-run-result после обновления guards: mode dry-run, personal83/corporate79,47 creator и47 uploads, proof/content/ACL/financial unchanged, old email denied, new receipt/notification contact, alias merged внутри транзакции и53 отозванные сессии. Ветка dry-run в скрипте заканчивается rollback. Синтаксис скрипта дополнительно проверен compile() без исполнения. Backup/restore proof из предыдущего refresh сохранён: закрытый dump с контрольной суммой, isolated restore, временный стенд удалён. Wrapper `backup_verified=False` по-прежнему препятствует случайному apply; оператор вправе установить True только после фактической прочитанной проверки backup.

- Окончательный script SHA-256: `6b5ad1ea62853347390577be0b949c6fd2ea19398e425c401e1db65c9b5d3d00`.
- Проверенный dry-run-result SHA-256: `066be4d0d4398fe01104af49027c3b2496dfe54a722a251ba1a3a227fa1d56e3`.

| Документ | SHA-256 |
| --- | --- |
| `spec.md` | `e7957e21891f90eae98f9de79308b57fb688107b946be48564a7eeaeb2cee158` |
| `plan.md` | `3de9d01f9950304d6f57bd2847709fcb8eb22338c5e66009d2b0d2eea9d68711` |
| `tasks.md` | `1747a08d4d1aa3d4f8115acdc45e8cb803420cf26ae51440de9207f5379c3445` |
| `quickstart.md` | `8526687e312d4e56febd400b2a7e0c6671c82e2fd3e99a029874b75954a26b49` |
| `analyze-storage-simplicity.md` | `219198147edd290ac136248913b4cf44b1e4280b2ecef4cd71f6d1f0e9b2a6e6` |

После записи checklist перечитан целиком:7 `[x]`,0 `[ ]`. Чеклист и этот отчёт — единственные изменённые reviewer файлы. Применение требует неизменного проверенного скрипта/обычного запуска Python без отключения assertions, актуальных root/scope assertions и backup_verified; при изменившейся форме аккаунтов скрипт должен остановиться. После commit нужны новое независимое чтение account/identity/subscription/meeting/financial состояния и настоящий вход владельца новым методом. Результат объединения, доставка нового письма, человеческая приёмка и UI выпуск этим pre-apply PASS не объявляются выполненными.

Последнее ограниченное дополнение: result выводит `fingerprints=before` для послеоперационной сверки (только table names/хэши). Обратное удаление ровно этого поля воспроизводит предыдущий проверенный script SHA-256 `baefd28386d6a262a1f0a424c38777598771110cebcf5e60fe71c681c9d40efa`; иного изменения нет. Новый окончательный SHA-256: `6b5ad1ea62853347390577be0b949c6fd2ea19398e425c401e1db65c9b5d3d00`. Синтаксис проверен; допуск PASS7/0 сохраняется, новый dry-run поведенческой проверки не требуется для одного вывода уже вычисленных хэшей.

## Послеоперационная и человеческая сверка, 2026-10-16

Новый refresh не меняет markers качества требований7/0 и не отменяет историю предоперационных HOLD/PASS. Прочитаны `postcheck-result.json` и `validation-storage-simplicity.md`; основной агент сообщил о завершении apply после pre-apply PASS. Скрипт SHA-256 повторно проверен: `6b5ad1ea62853347390577be0b949c6fd2ea19398e425c401e1db65c9b5d3d00`, совпадает с окончательно проверенным. Reviewer не применял операцию и не выполнял новый живой запрос; факты ниже основаны на прочитанных результатах независимого послеоперационного чтения основного агента.

Postcheck фиксирует: postcommit_verifiedTrue;83 строки personal и79 corporate встреч;53 неудалённые owner-встречи с фактическими view/edit/share решениями;27 выбранных неизменяемых таблиц содержимого/ACL/финансов совпали по хэшам. Оплаченный срок не изменён, новый primary/receipt/notification контакт выбран; oldmethods retired, прежние sessions/devices revoked, source merged alias. Два календарных источника синхронизированы после recovery. Это не восстановление удалённых встреч и не утверждение, что все83 встречи доступны как неудалённые.

Общий хэш всех изменяемых таблиц послеcommit ранее не совпал; он не выдан за успешную полную сверку. Новый PASS ограничен27 явно проверенными frozen content/finance таблицами и отдельными проверками ACL/identity/subscription. Изменяемые календарные/сеансовые таблицы живут дальше; наличие поздней синхронизации и нового входа зафиксировано отдельно и не используется как недоказанное универсальное объяснение любого различия.

В validation записано подтверждение владельца после обычного нового Яндекс входа: «Вошёл, встречи и подписка на месте». Это человеческое подтверждение входа/наличия данных, переданное основным агентом и сохранённое в validation; reviewer не подменяет его собственным проверенным банковским или почтовым результатом. Правильный адрес новых receipt/notification не означает доставку нового письма. Прежнее подтверждение поступления денег учитывается отдельно; новых платежей этим обзором не создано.

- postcheck-result SHA-256: `97dc51ad70d79e2d8a6ac0495301679fc35ee68a34a7d3247c669428d97e0270`.
- validation SHA-256: `471405b6caf2a6bd75758345a7bef18b1758479c37283ac7e26a790510f17185`.

**REQUIREMENTS7/0 и выполненная ограниченная operator recovery подтверждены описанными evidence; release/retention/human-usability gates остаются открыты.** Нового UI в production этот refresh не подтверждает. Только два owned review отчёта изменены reviewer, canonical/code/checklist/PR/GitHub/prod read-only.

## Требования адреса будущего чека, 2026-10-16

**Независимый REQUIREMENTS PASS — checked7/unchecked0; blockers0.** Это допуск уточнённого buildable FR-059/T067 до изменения кода. Предыдущие UI/source/operator PASS не доказывают исправление renewal planner; пройденное восстановление доказало только нынешние profile/manual receipt/notification контакты.

Прочитаны текущий `_verified_receipt_contact` и все6 route callers, `billing/receipts.py`, `plan_due_renewals` с созданием invoice и повторным использованием уже существующей операции, parameterized planner test, новый spec/plan/quickstart/analyze и T067. Причинный RED actual `.dev/storage-receipt-contact-red.log`:1failed/1passed,106deselected; при current verified synthetic owner старый invoice snapshot ошибочно остаётся источником, при currentNone прежний historical fallback проходит. Это достаточное доказательство причины и измеримого ожидаемого изменения, а не результат будущего исправления.

CHK006 расширен: общий existing selector переносится в `billing/receipts.py` с сохранением фильтров `user_id==billing_owner`, activeTrue, verifiedTrue, email non-null, прежнего порядка/limit и dbNone поведения. Route alias сохраняет совместимость existing callers. Новый planner invoice выбирает подтверждённый действующий контакт owner первым; при его отсутствии сохраняется прежний successful invoice snapshot fallback. Если ни одного пригодного контакта нет, прежнее receipt_contact_required остаётся; чужой/неподтверждённый/disabled контакт не становится current. Это не изменение способа оплаты, согласия или разрешения списания.

Spec явно запрещает переписывать старые/начатые invoice или pending snapshot. Существующий code path при найденной операции повторно использует existing operation, новый BillingInvoice конструируется только для selected new attempt; исправление должно менять источник контакта исключительно для создания этого нового документа. Amount/paid period/recurring authority versions/method validity/idempotency/dispatch не меняются. Реальные дополнительные деньги, включение autorenew и объявление письма доставленным не разрешены проверочным срезом.

План и quickstart требуют существующий planner RED→GREEN с current/fallback, настоящую PostgreSQL проверку owner/active/verified отрицательных predicates, затем renewal/unit/receipt/manual purchase siblings. Эти проверки достаточны для минимального переноса общего helper и выбора нового snapshot; новые API/схема/абстракция/провайдерный POST не нужны. После реализации нужен отдельный independent source refresh и current checks; прошлые UI48/48/operator postcommit evidence не закрывают этот код. T067/#7599 является существующей задачей contact recovery; внешний issue update/новый release остаются ответственностью основного агента, reviewer GitHub не менял.

| Прочитанный документ | SHA-256 |
| --- | --- |
| `spec.md` | `7f42556c73c14f425fb4f19d2c942c2c232558c2341498eb7942c86845eee544` |
| `plan.md` | `d302b0dddbb6479fcd07b01a3d61cd36608acbc2b0b5f25c5f68a5907131387e` |
| `quickstart.md` | `3396bf3f3a15dfcd573b9449491e25b6d63249fe72d9c603a8a6a01aedcc2de5` |
| `analyze-storage-simplicity.md` | `6ab30cfd6c86b626f4e24362a57b678eafe550e7f68b9f16140934658db9d490` |
| `tasks.md` | `1747a08d4d1aa3d4f8115acdc45e8cb803420cf26ae51440de9207f5379c3445` |

После правок перечитан весь checklist:7 `[x]`,0 `[ ]`. Изменены только owned checklist и этот report; реализация/canonical/БД/Git/GitHub read-only.
