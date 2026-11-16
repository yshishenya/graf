# T112 — обычный возврат и задержанное подтверждение COMMIT

16.11.2026. Существующий срез `high-risk-product` F273/T112/#7698,
T113/#7804. Основа кодовой ветки `codex/f273-result-visibility-20261116`:
`237d368b94c61908f853262ec1be545504951dc8`.
Изменены только два существующих contract-test файла и отчёты.
Рабочий код, ограничения времени, настройки пула и настоящий закрытый
`_result_period_context` не изменялись. Это не полная приёмка T112.

## Проект и наблюдаемые условия

До кода получен и полностью прочитан независимый
[проект двух случаев](t112-ordinary-return-design-review-20261116.md),
SHA-256 `04f10392b802ffd769dcd95324de4f1070f125ac29385f121547475611ad9c6f`:
TEST DESIGN PASS, P1=0/P2=0, requirements16/0 + security27/0 + privacy52/0 +
infra29/0 =124/0. Более ранний
[предварительный отчёт](t112-ordinary-return-preflight-20261116.md)
сохранён отдельно. Отметки reviewer-owned checklist не менялись.

Отдельный искусственный медленный default reset не добавлен: после завершённой
транзакции штатный asyncpg adapter не начинает второй сетевой rollback.
Вместо него normal проверяет настоящий reset→checkin аналитического соединения,
его здоровое повторное использование и неприкосновенность другого соединения
того же пула. Fault удерживает только server→client ответ точного COMMIT stream.
Методы Session/Connection/driver не подменяются; публичные события только
наблюдают состояние и закрывают адресный test gate. Assertions находятся вне
callback и не становятся искусственной причиной отказа COMMIT.

Общий request pool имеет два слота, default FIFO/reset/recycle и pre_ping.
Настоящий GET получает proof до удержания чужого соединения F. Два
последовательных native connects связывают публичный pool entry/native driver
с соответствующим relay stream без предположения о конкурентном порядке.
F остаётся выданным, второй slot T последовательно обслуживает настоящий
auth/tenant/аналитический POST. Отдельный прямой observer не считается F.

В fault обязательная M1 до отмены доказывает две durable account-строки другой
сессией, присутствующий idle backend T без транзакции/блокировок, удержанный
реальный ответ, отсутствие after_commit и неотменяемую ещё COMMIT task.
F при закрытом gate выполняет SELECT/PID/commit с прежним поколением.
После unavailable, до gate.set/dispose и в исходном hard2s проверяются:

- закрытое старое native поколение, исчезнувшие backend/locks;
- законченные relay root/pumps/wait_closed, закрывающиеся writers;
- пустые собственные guard/Session/Connection registry, отсутствие owner tasks;
- сохранный F и новый borrower B того же pool entry с другим native driver/PID;
- повторные SELECT/PID/commit F/B до и после позднего gate.set.

Normal сохраняет исправный idle driver и PID, наблюдает exact
`commit → after_commit → reset(True,False,False) → checkin`.
Живое соединение здорового пула не объявляется утечкой. Watchdog3s нужен только
для выхода из неуспешного опыта и обязан не сработать при принятом результате.

Отдельный следующий настоящий POST имеет собственный обычный бюджет и должен
примирить прежние account keys. Сравниваются полные сохранённые строки,
включая event ID/время/payload; автоматического повтора первого запроса нет.
Два запрещённых provider транспорта считаются независимо, ожидается ноль.
Все данные синтетические. Этот POST не является реальным внешним просмотром.

## Законченные исходные результаты

Журналы остаются в закрытых временных материалах; в Git включены только
метаданные и контрольные суммы.

| Опыт | Фактический результат | Журнал `/private/tmp/` и SHA-256 |
| --- | --- | --- |
| Два новых случая на неизменном runtime | 2 PASS,56 deselected,11.47s/runner16s,EXIT0 | `graf-t112-native-commit-baseline-20261116.log`; `abc2cb44935541c26031ac99040a84ea6c554bb34e5428be7144116efc2f1f24` |
| Оба затронутых файла целиком | 85 PASS /2 FAIL,170.28s/runner177s,EXIT1 | `graf-t112-native-commit-profile-20261116.log`; `3d7afbecd7e1018be9f677a26ce6bb163794e113abff46002b141be1edf265ea` |
| Причинное наблюдение двух отказавших сценариев и normal | 2 PASS /1 FAIL,55 deselected,13.27s/runner18s,EXIT1 | `graf-t112-native-commit-diagnostic-20261116.log`; `6883a2f322d819bf955ca9049a6ab69e5d44bc22d1f8af208a8acaa4002a544e` |
| Оба файла после TTL-поправки, с временным observer | 86 PASS /1 FAIL,164.41s/runner170s,EXIT1 | `graf-t112-native-commit-profile-observed-20261116.log`; `4da055cc19fba584c0c267311d80c29fdd4eba51e3623a578fa7c0fcf1f287cf` |
| Окончательный профиль двух файлов без plugin | 87 PASS,150.46s/runner154s,EXIT0 | `graf-t112-native-commit-final-20261116.log`; `5bbd2af489357de43a880b7739b6f219983ecb8caf8478c833af85f16e2fa28e` |

Все шесть runner, включая адресную P2-проверку ниже, завершились; их временные PostgreSQL контейнеры удалены.
В каждом запуске один прежний PytestAssertRewriteWarning; пропусков нет.
Первый baseline: normal0.778s, fault1.555s, M1=True, foreign/reuse=True,
watchdog=False. Первый общий профиль: normal0.754s, fault1.552s до ранней
приёмки/F/B; отказ fault произошёл только на следующем отдельном POST,
который вернул unavailable вместо accepted. Это не отменяет наблюдение M1,
но не принимает весь сценарий reconciliation.

В диагностическом повторе native normal/fault прошли целиком, включая
следующий POST:1.103/1.556s до ранней приёмки. Причина первоначального
unavailable следующего POST **не установлена**. Повторный PASS не объясняет
его и не доказывает стабильность при любой нагрузке. Ожидаемый отказ первого
fault POST имеет ProjectionBudgetExceeded после задержанного COMMIT;
этот ожидаемый отказ не приписывается второму POST.

## Причинная поправка прежнего TTL-теста

Второй отказ общего профиля —
`test_valid_to_expired_race_never_starts_a_renewal_session`.
Он вернул renewed. В неизменном обработчике этот исход возможен только при
первоначальном `age == expired`, поэтому целевая valid→expired фаза не достигнута.
Диагностический повтор непосредственно записал `proof_age=expired`.
Тест задавал age599, но целочисленная подпись оставляла менее секунды до TTL,
а AfterReadClock до своего shift продолжал читать реальные часы.
Точное число миллисекунд исходного сбоя не установлено.

Независимый проверяющий подтвердил причину и допустил узкую test-only поправку:
route clock теперь вычисляется от `issued_at` конкретного подписанного proof:
ровно599s до настоящего свежего чтения и604s после него. Реальный verifier,
загрузка/locks БД, монотонные work/cleanup сроки и TTL не меняются.
Тест требует наблюдения обеих фаз, unavailable, одной admission сессии,
нулевых INSERT/COMMIT и пустого ledger. Отказ не превращается в разрешение
renewal и не устраняется повышением бюджета.

## Окончательный профиль и независимая приёмка

Наблюдаемый общий повтор подтвердил TTL599→604, настоящий fresh read и оба
native случая целиком, включая следующий POST. Время normal1.143/fault1.589s,
watchdog=False. Но весь профиль FAIL: прежний near-total size-test получил
KeyError на отсутствии собственного first-refusal marker. Причина проверена
по источнику: временный observer добавил `_refuse` на подкласс
ResultInspectionSession, а этот прежний тест наблюдает тот же метод базового
ResultProjectionSession. Новый override обошёл его callback. Runtime helper
всё ещё вызывался, но наблюдаемая трасса прежнего теста была изменена.
Это ошибка диагностического стенда, не PASS размера и не доказанный новый
runtime-дефект. Сам observer в кандидат не входит и уже удалён.

Окончательный запуск двух файлов без observer завершился: **87 PASS**, без
пропусков,150.46s/runner154s/EXIT0, `isolated_container_removed`,
`postgres_test_result=pass`. Набор содержит оба новых native случая и причинную
TTL-поправку ровно по одному разу. Ни один красный результат выше не
заменён суммой отдельных PASS. Исходное unavailable следующего POST в первом
общем профиле остаётся необъяснённым; оба последующих диагностических PASS
и окончательный87PASS не устанавливают его причину.

Независимое [implementation review](t112-ordinary-return-implementation-review-20261116.md)
сохраняет **HOLD/P1=0 подтверждённых дефектов продукта/P2=1**.
P2-01 — отсутствие точных assertions fault invalidate→checkin(None) и
смены DBAPI identity при B, хотя эти metadata уже собирались.
Неизвестный первоначальный отказ следующего POST — отдельное основание HOLD,
а не объяснение P2. Финальный reviewer report полностью прочитан,
SHA-256 `d537d25dd8185c792eb5450e0faee531634434b39bc7bc2c85a33efe7cbff924`.
Новый GREEN не снимает исходную неизвестность.

По допущенному reviewer минимальному проекту добавлены только недостающие
assertions вне callbacks и до gate.set: ровно один target invalidate,
последующий checkin, returned_dbapi=None, у borrower B fault DBAPI новый,
normal прежний. Сроки/стенд/runtime не меняются. Адресная проверка завершена:
**2 PASS**,56 deselected,10.74s/runner15s/EXIT0, контейнер штатно удалён,
resultpass. Normal0.690s/fault1.548s, оба watchdog=False; следующие отдельные
POST и сравнение строк прошли. Журнал `graf-t112-native-commit-p2-20261116.log`
в `/private/tmp/`, SHA-256
`8817b0beb968b984664bda8d8da2adeaf6ac921706e059e35806ff579650de56`.87PASS относится к
предыдущему source83c90ab8 и не выдаётся за исполнение ещё отсутствовавших
assertions. Полный87 повторно не запускался: изменились только четыре
assertion строки двух адресно проверенных случаев. Независимое повторное
ревью требуется после законченного результата.

Финальный normal0.992s/fault1.550s до ранней приёмки/F/B, оба watchdog=False;
следующие отдельные POST также прошли. Clock trace `[599,604,604]` подтвердил
настоящий fresh read. Collection87/digest
`6d62f13844d8b8bd0585c7b7032e595806dc81de0189e50d55d7a7a46a85b28d`
совпадает с первым общим профилем. Не было расширения набора до старых312.

| Окончательный файл тестового кода после P2 | SHA-256 |
| --- | --- |
| `apps/server/tests/contract/test_result_view_http_budget.py` | `f12c96159912479d5fc3c59a00bd5df0eccc944486b4900df9b7edebf72f5eb7` |
| `apps/server/tests/contract/test_result_view_http_integration.py` | `64b6abedf4d3793747c725c7909ac942351b974e9539a5c49f528890f5fa8a85` |

## Требования и границы

18 исходных требований сверены SAME с собственной картой чтения того же
диалога. Analyze
`0252da92dd9c3ff435a13bf55c0234afbb010abd9a3a1c49f8e42461427c18dc`
сохраняет применимость. Нового runtime-дефекта этим опытом пока не доказано;
новая правка runtime потребует отдельного независимого проекта.
Scoped `speckit-converge` выполнен после законченного профиля:
prerequisite `--require-tasks --include-tasks` PASS, before/after_converge
hooks не настроены; неподдерживаемый этим проектом `--require-spec` не
использован. Сопоставлены FR-021/025/SC-006, четыре решения проекта
(native normal, M1/unknown ack, same-pool cleanup/reuse, следующий явный POST)
и принципы II/III/IV/VI/VII. Новых требований/contradicts/unrequested нет.
Остатки partial: T112 — неизвестная причина первого отказа следующего POST,
остальная ручная/native/failure приёмка; T113 — настоящая общая готовность
и восстановление. Всё уже входит в открытые T112/T113, поэтому дублирующие
task IDs и фаза не добавлялись, tasks.md побайтово сохранён.
**Полная F273 не converged; implementation HOLD не снят.**

Ruff по двум файлам, agent-context и diff-check PASS; runtime source и
changelog fragment не менялись относительно основы. Итоговые ссылки и
reviewer hashes сверяются перед контрольным сохранением. Сохранение
кандидата не будет означать допуск к merge/release.

Старые312/233/120 не складываются с новым набором. Причина исходных12FAIL
прежнего HTTP-среза также остаётся неизвестной; текущий опыт её не объясняет.
Контент/вёрстка сайта, службы, nginx/DNS/Compose, Postal, очереди, письма,
резервные копии, настройки аналитики/IP и рабочий сбор не изменялись.
Stalwart не выбран почтой ГРАФ. Слияния в master остаются приостановлены
до завершения выпуска Метрики. PR/merge/Full/CD для этого среза не выполнялись.
T098/T113/restore/T0/Product Radar и коммерческие критерии открыты.
