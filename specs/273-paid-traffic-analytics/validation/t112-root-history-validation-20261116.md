# T112 — история корневой транзакции до получения соединения

16.11.2026. Полоса `high-risk-product`, существующая F273/T112, issue #7698.
Рабочая копия `/private/tmp/graf-f273-result-visibility-20261116`,
основа `3ab916f2439d86914c83d22a78d1a518a6b21ebf`.
Это изолированный срез HTTP-бюджета; рабочий сбор выключен.

## Основание и область

Принятый причинный baseline `c420927a7633596ca392799b61e46022ae7234d2`
не переписывался и не повторялся. Normal PASS и fault FAIL при удержании
ответного EOF старого поколения остаются исходными результатами.
Предыдущий пробный runtime diff отменён; его 30 mock GREEN и незаконченный
native запуск не принимаются за проверку нового решения.

Независимый исправленный проект прочитан до новой реализации:
[public lifecycle witness](t112-pool-return-preflight-20261116.md#исправленный-public-design--положительное-свидетельство-истории-root),
SHA-256 отчёта при допуске
`4b9b5f5a291fa2ce29b5d6cbf3bb0711a3f3e43b37d8041cf1f8d929d996848a`.
Он отозвал прежнее ошибочное требование active root в Pool.close.
18 обязательных входных хешей совпали, применимые оригинальные разделы и
зависимости восстановлены в том же диалоге. Карта чтения вне Git:
`/private/tmp/graf-t112-root-history-reading-20261116.json`.
Prerequisite `--require-tasks --include-tasks` PASS; прежние четыре
reviewer-owned checklist124/0 и scoped analyze требований не изменены.
Before/after_implement hooks выключены. Новые spec/task/issue не создавались.

Изменяются только общий `api/product_analytics_guard.py` и его существующие
unit/contract tests. Callers, auth/CSRF/renewal, C1/I1 и прежний формат lease
не расширяются. Тексты, вёрстка, настройки, SQL schema и зависимости прежние.

## Изменение

В `_ResultViewOwner` добавлена отдельная краткоживущая `unbound_roots`.
Она связывает exact root lease с исходной task, независимо от последующего
handoff `lease[2]`. Прежний lease остаётся списком из трёх элементов.

Свидетельство создаёт только настоящий public after_transaction_create
корневого AUTOBEGIN при согласованных task/Context/Session/current root,
без nested и с обоими active=True именно при создании. Повторный callback
того же root не создаёт новое разрешение. Public child/subtransaction/nested,
before_commit, after_rollback/after_soft_rollback, начало after_begin и конец
root окончательно отзывают его через saved Session.info exact lease, включая
событие в другом Context. Finished-root cleanup и проверка нулевых остатков
запроса включают новый реестр.

В public Pool.close новое разрешение требует сохранённой истории того же
root и текущих root.is_active=False/Session.is_active=False. Все прежние
проверки owner/task/no cancellation/no connection lease/current Session,
native generation/wrapper/entry identities, !in_use/no entry keys и native
open/noTX выполняются до public driver.terminate(). При mismatch нет terminate,
owner.failed или изменения чужих maps. Сам Pool.close уже выбрал exact idle
поколение для физического закрытия; !in_use не доказывает резерв запроса.
Причину recycle событие не раскрывает. Private SQLAlchemy API, retries и
новые timers в runtime не добавлены.

## Проверки реальных Session событий и отрицательных условий

Новые исходные проверки до runtime:43 FAIL/198 deselected,1 прежний warning,
1.62s. Это RED отсутствующей новой истории, а не повтор native baseline.
После кода:41 PASS/3 FAIL. Три оставшихся отказа нашли ошибку тестового
ожидания: after_begin ещё выполняется внутри provisioning; ACTIVE возвращается
в finally после события. Прочитан настоящий `orm/session.py:1210–1272`.
Ожидание исправлено на наблюдаемую последовательность, runtime не расширялся:

| Публичная стадия | root.is_active / Session.is_active | Свидетельство |
| --- | --- | --- |
| after_transaction_create | True / True | Есть, exact lease/original task |
| Engine.do_connect | False / False | Есть |
| after_begin | False / False | Уже отозвано до binder |
| Возврат SELECT | True / True | Не появилось заново |

Профиль44 PASS/198 deselected/0 skips/0.23s. Затем добавлены проверка
реального after_begin в пустом Context с early-return binder и no-rearm,
проверка witness в finished-root cleanup и запрет mint для explicit BEGIN.
Полный unit файл: **243 PASS /0 skips /1 прежний fixture warning,17.03s**.
Проверены nested/foreign Context child, commit, rollback/partial rollback,
новый root своим creation event, успех/ошибка/настоящая task cancellation;
нулевые connection/root/witness maps и отсутствие Session.info после close.
Public Pool dispatch с моделями проверяет точные отрицательные identities;
SQLite lifecycle и эти модели не подменяют native PostgreSQL опыт.

## Native PostgreSQL: промежуточная ошибка наблюдателя

Первый новый запуск закончился штатно:2 FAIL/27 deselected,5.75s,
runner8s/EXIT1, собственный временный контейнер удалён. Оба POST пришли
примерно за0.05s; root False/False, witness и15 identity checks совпали,
driver был уже закрыт в позднем public Pool.close listener. Но observer
ждал upstream EOF, который при native terminate может не быть наблюдаем:
клиентский EOF заканчивает relay через FIRST_COMPLETED, отменяя ответный pump.
Именно ожидание upstream marker истекло через1s. Это не native GREEN,
не доказанный новый отказ продукта и не установление причины прежнего90s
зависания другой попытки.

Принятый проект уже допускает этот настоящий cleanup в §«Доказательства после
будущей реализации». В relay добавлен только наблюдаемый client EOF marker;
клиентский pump не удерживается. Fault EOF gate теперь закрывается до POST,
до runtime callback. Тест наблюдает client EOF, окончание stream и независимое
исчезновение backend/locks, сохраняя все ранние проверки исходного2s.
Assertions внутри Pool.close не бросаются: callback сохраняет snapshot,
одноразово отключается, выставляет close_seen в finally. Отдельный public
Session observer заранее сохраняет owner/root/task; POST имеет собственный
handle. Перед teardown test listeners снимаются, gates открываются,
watchdog останавливается. Join только своих сохранённых задач и закрытие
учтённых handles/dispose имеют отдельные ограниченные сроки; они не заменяют
раннее продуктовое доказательство.

## Окончательный адресный native опыт

**2 PASS /27 deselected /0 skips /1 прежний warning,3.75s,runner8s/EXIT0.**
`postgres_test_cleanup=isolated_container_removed`,
`postgres_test_result=pass mode=focused`.

| Наблюдение | Normal | EOF gate закрыт |
| --- | --- | --- |
| Полный POST | accepted,0.058s | accepted,0.057s |
| Actual root/Session flags при close | False/False | False/False |
| Exact witness и15 close checks | Все True | Все True |
| Native уже закрыт до library graceful close | True | True |
| Client EOF / upstream EOF marker | True / False | True / False |
| Старый backend/locks исчезли без отмены task | True | True |
| Watchdog освободил gate | False | False |

Accepted в обеих ветвях ожидаем: предотвращено само graceful ожидание.
Это синтетический non-ledger handler, не принятие настоящих вех.
До открытия fault gate и dispose в исходном2s проверены:
полный ответ; завершение старого relay/root/pumps/writers/wait_closed;
нулевые own tasks/owner/root/witness/Session.info; pool.checkedout=2;
F и новое P того же pool сохраняют exact PID/SELECT1/commit; новое T вернулось
idle/noTX/no locks с тремя reset/checkin парами auth/tenant/renewal;
продление auth реально committed, ledger0. После этих проверок следующий
checkout/SELECT/commit успешно переиспользует пул. Живое новое idle соединение
не объявляется утечкой. Два проверенных случая не покрывают любой возможный
library dispose/overflow/recycle или закрытие произвольной Session.

## Замечания независимого ревью и последние локальные исправления

Новый reviewer addendum, прочитанный целиком после первых запусков, имеет
SHA-256 `3653b0575a2d8212fb5fdd270fc4b921da5651bb9a989aae615f2d894f789c52`.
Его итог — P1=0 новых runtime-дефектов, P2=3, implementation HOLD.
Способ client EOF принят, но более поздние GREEN reviewer ещё не принял.
Отчёт проверяющего не переписывается основным исполнителем.

- P2-N1: исходный upstream marker заменён настоящим client EOF и окончанием
  stream; gate вооружён до POST. Дополнительно observer теперь использует
  тот же исходный абсолютный deadline, что полный запрос и все ранние проверки.
- P2-N2: новые revoke/close callbacks проверяют форму root list3 и witness
  tuple2 до распаковки/индексов; revoke проверяет тип owner и Session binding
  до обращения к его maps. Непригодная metadata не ремонтируется. Добавлены
  14 отрицательных случаев неверной формы, owner/root и неизменности данных.
- P2-N3: существующий finished-root cleanup тест теперь содержит живой witness;
  owned удаляет его, все прежние contradictory/pending/foreign случаи сохраняют.

Адресный unit после этих правок: **59 PASS /198 deselected /0 skips /
1 прежний warning,0.21s**. Новый native запуск с окончательной формой данных
и общим deadline: **2 PASS /27 deselected /0 skips /1 прежний warning,3.83s**;
runner7s/EXIT0, isolated_container_removed/result pass. Normal/fault оба
accepted, client EOF True/upstream EOF False, все15 checks True,
rootFalse/False, native_closed True, backend_gone_before_cancel True,
watchdog False. Все ранние resource/F-P/newT/renewal/ledger0/reuse assertions
достигнуты и прошли. Это подтверждение основного исполнителя; независимое
снятие P2 и общий implementation PASS ещё не получены. Прежний243 остаётся
проверкой предшествовавшего точного guard/unit, не объявляется полным набором
последней формы кода. Общий regression до независимого допуска не запускался.

Текущие кодовые изменения остаются незакоммиченным кандидатом.
Собственный diff трёх файлов и fragment дополнительно сохранён вне дерева:
`/private/tmp/graf-t112-root-history-candidate-20261116.patch`, SHA-256
`c51af0f0f2bcc1ae0c1f68956173ca14b4183b2d723fcd8ca6982f43a1dcbb47`.
Новый запрос
ревью подготовлен в `/private/tmp/graf-t112-root-history-review-update-20261116.txt`;
подтверждённая доставка нового поручения после reviewer3653b057 и живое ожидание
его результата не установлены. Ошибочные calls wait с cell_id=none не являются
передачей поручения/проверкой агента или среды и ничего не подтверждают.

## Доказательства предыдущего шага до трёх замечаний

| Файл | SHA-256 |
| --- | --- |
| guard | `33ec2b127cdf1feae0d342233904d8a25345a0bc99dfc99dab7f3645685cdc5a` |
| unit | `f3415b22a0818550518ab1ef5e072a4f7078d0d1fd6d6d1d9670ee9b0e48509e` |
| contract | `c863b978885c759e1a30b0ac3e20a56017110735e21417a82cda638c6b7af5e1` |
| `/private/tmp/graf-t112-root-history-unit-red-20261116.log` | `85b4125cc71b08dcec1406da60ccb893eff46ca29770a5ab3c161eefddc1b47f` |
| `/private/tmp/graf-t112-root-history-unit-green-final-20261116.log` | `d6c17d0291a33affb900c79a0a6644e697417c729c2b69551be3811be2fa87a6` |
| `/private/tmp/graf-t112-root-history-unit-full-20261116.log` | `c8c76236260f9875881d0a8a80c0924ba26ab96e5a74e2ebaf050b83f80a18b4` |
| `/private/tmp/graf-t112-root-history-native-20261116.log` | `515d1c00d1b332f2bc9c9f956117e5257f62c8b6a53dd488bd350076050bddb5` |
| `/private/tmp/graf-t112-root-history-native-final-20261116.log` | `7c097e78821e5f2bac93c3a96b05f0e2575478a014a9776bd790dacec62a07b4` |

## Окончательные локальные входы

| Файл | SHA-256 |
| --- | --- |
| guard | `0ee850ee5310ff1c83d3c6e32d209ce8cee97951393863e937ac33f8e51421bc` |
| unit | `24aa677d108b6c19fd1dff6ac3a19c4ce9674e5ac8e7a43276721e5bce0d9107` |
| contract | `6c1274ef26d94df8caed306bf0e8b0cef5a81f45e0d2174726c149fbed9e45f5` |
| `/private/tmp/graf-t112-root-history-shape-unit-20261116.log` | `f2d13d68492f4e7e763fdf69873ff497737b889dde32d5a18310aefe81dfce29` |
| `/private/tmp/graf-t112-root-history-native-reviewed-20261116.log` | `9a3aec477786216b669ae1b677c0c739ef03c3a2b6f7216e0895b1a6651f93e6` |

Независимое повторное ревью реализации и новый затронутый regression-профиль ещё
требуются. Последний принят после реального изменения, а не повторяется ради
активности. T112/T113, реальные issuance/renewal/защищённый POST и общий
admission/ledger, остальные commit/cleanup исходы, browser/native acceptance,
readiness/actual restore/ёмкость, T098, выпуск и коммерческая цель остаются
открытыми. Новых визитов, регистраций, оплат или публичных сообщений нет.

## Полный unit после окончательных N1–N3 — 16 ноября

Терминальный журнал `/private/tmp/graf-t112-root-history-unit-final-all-20261116.log`
подтверждает **257 PASS / 0 skips / 1 прежний fixture warning / 16.86s / EXIT0**.
SHA-256 журнала:
`020491b716bf258405c7b4e2220334fc80c93635007268b682cca254c4f4f703`.
Повторный запуск не выполнялся. Все три текущих кодовых SHA-256 в таблице
«Окончательные локальные входы» сверены и совпали. Предыдущие 243 PASS
остаются исторической проверкой версии до окончательных проверок формы.

Это полный unit-файл, а не общий профиль PostgreSQL. Общий профиль из
257 unit + 29 contract + 8 integration (`test_product_activation_analytics_rollout.py`)
ещё не запускался; он следует после повторного независимого заключения
по исправлениям N1–N3. Подготовленный запрос обновлён реальным терминальным
результатом: `/private/tmp/graf-t112-root-history-rereview-final-20261116.txt`.
Подтверждённая доставка этого нового поручения и живое ожидание результата
не установлены. Последнее независимое заключение по-прежнему HOLD
`3653b0575a2d8212fb5fdd270fc4b921da5651bb9a989aae615f2d894f789c52`.

Ошибочные обращения к `functions.wait` без действительного running cell ID
не передали поручение, не проверили состояние агента и не доказывают отказ
среды. Они не являются ожиданием ревью и не дают основания повторять тесты
или обходить независимую проверку. Кодовой commit/push, PR, выпуска,
рабочего включения, изменения сайта или почты не было. T112/T113 и
коммерческая цель остаются открытыми.

## Независимая приёмка и общий PostgreSQL-профиль — 16 ноября

После предыдущей записи получено и полностью прочитано повторное независимое
заключение: **SCOPED implementation PASS, P1=0, P2=0**. Все N1–N3 закрыты.
Отчёт проверяющего `t112-pool-return-preflight-20261116.md`, SHA-256
`1316131eedeccb03abc2f1333e3d86ae3daf0b74010db0568b429d1c9c554862`.
Это подтверждает состоявшуюся доставку последнего поручения; прежняя запись
об отсутствии подтверждения доставки описывает состояние до получения ответа.
124 checked / 0 unchecked; 18 исходных хешей требований совпали.
Проверяющий изменил только собственный отчёт. Кодовые SHA-256 остались теми же.
Историческая причина P1-R1 устранена и принята только в проверенном idle
precheckout Pool.close сценарии. Recycle reservation proof, уже начатый
native graceful close и все прочие исходы этим не принимаются.

После независимого допуска один раз запущен общий затронутый профиль:

```sh
UV_PROJECT_ENVIRONMENT=/Users/yshishenya/Documents/crisp/apps/server/.venv \
UV_NO_SYNC=1 GRAF_TEST_WORKERS=1 \
/opt/homebrew/bin/bash apps/server/scripts/run_local_postgres_tests.sh --focused \
 tests/unit/test_result_view_http_guard.py \
 tests/contract/test_result_view_http_budget.py \
 tests/integration/test_product_activation_analytics_rollout.py -q
```

Итог: **294 PASS / 0 skips / 1 прежний fixture warning / 50.50s / EXIT0**;
runner focused54s, `postgres_test_cleanup=isolated_container_removed`,
`postgres_test_result=pass mode=focused partitioned=false shard=none`.
Коллекция294=257unit+29contract+8integration, collection digest
`8c4e6787e34cc23b0e2e3a77d64c9065cfea262520cf5cbef5b1067b94da385d`.
Журнал `/private/tmp/graf-t112-root-history-regression294-20261116.log`, SHA-256
`57900f094db18ab00e6e04934af61e0a64d740d7bb3e1b271d27a1836cc982e1`.
Диск перед запуском146609904KiB, выше80ГБ. Рабочие сервисы не затрагивались.

### Сверка завершения конкретного исправления

Проверены текущие исходники, contract §5/7, spec FR-021/025/SC-006 и
существующие T112/T113. Полоса реализации high-risk-product сохранена.

| Обязательство этого исправления | Текущее подтверждение |
| --- | --- |
| Положительная public-история AUTOBEGIN и окончательный отзыв | Реальный Session lifecycle, unit257, независимый source review |
| Непригодные root/witness не разрешают terminate и не повреждают metadata |14 отрицательных случаев, N2 scoped PASS |
| Finished-root cleanup удаляет только собственный witness |Дополненный тест с живым witness, N3 scoped PASS |
| Полный ответ и окончание собственных ресурсов в исходном2s |Native normal/fault и общий294; client EOF prevention, не held upstream EOF |
| Сохранность чужих F/P в том же пуле и следующий checkout |Exact PID/SELECT1/commit, pool/reset/checkin и reuse assertions |
| Сохранение закрытого рабочего измерения и прежних границ |Нет рабочего запуска, HTTP admission не подключён; T112/T113 открыты |

В конкретном исправлении новых непокрытых обязательств не выявлено.
Это ограниченная сверка завершения, не полная сходимость всей F273.
Оставшаяся работа уже описана открытыми T112/T113: реальные proof issuance/
renewal, общий защищённый POST/admission/ledger, карточность/размер входа,
прочие close/commit/cleanup исходы, browser/native и recovery. Подтверждено
по текущему `product_analytics/ingest.py`: `_result_period_context` остаётся
закрытой заглушкой; один helper не подтверждает реальный HTTP-триггер.
Новых дублирующих задач не добавлено; tasks/spec/plan/checklist неизменны.
GitHub exact-SHA CI, PR/merge/выпуск и рабочая приёмка ещё не выполнены.
