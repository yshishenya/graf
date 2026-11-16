# T112 — несжатый возврат соединения и ограниченная диагностика

16.11.2026. Продолжение существующего `high-risk-product` F273/T112/#7698,
T113/#7804 в `/private/tmp/graf-f273-result-visibility-20261116`,
ветка `codex/f273-result-visibility-20261116`, основа
`50c9ecab6586a39650e78039775311278a7d2ba9`.
Изменён только новый native contract-test и документация. Runtime и
`changes` побайтово совпадают с `237d368b94c61908f853262ec1be545504951dc8`.
Рабочий `_result_period_context` остаётся закрытым. Независимая приёмка
нынешней поправки ещё не получена; общий **HOLD сохраняется**.

## Полученное независимое ревью

Полностью прочитано [повторное ревью](t112-ordinary-return-rereview-20261116.md),
SHA-256 `4618fe7668ef0feef4732cda697049827c4ac82d9d5e4d02b448ab41777ab5f7`.
P1=0/P2=1: порядок invalidate→checkin(None) и смена DBAPI принимаются,
но прежний callback отбрасывал каждый checkin после первого. Поэтому
count==1 не доказывал уникальность. Это пробел наблюдения, не runtime-дефект.
Допущен минимальный test-only подсчёт всех возвратов точного entry в границах
целевой операции; законные последующие выдачи B/F/POST не включаются.
Прежние report/design не изменены. Отдельный исходный repeated unavailable
этим замечанием не объясняется.

## Законченная chain-диагностика — причина repeated неизвестна

Запущенный до этого продолжения процесс33683 завершился EXIT0:
**87 PASS**,150.37s pytest/155s runner, один прежний warning, без skips.
Cleanup: `isolated_container_removed`, `postgres_test_result=pass`.
Журнал `/private/tmp/graf-t112-unknown-post-chain-20261116.log`, SHA-256
`0b668de206529d98088bea9d1352f4249554ec1f4d62d3653f622cea7930de19`.
Тестовый integration этого опыта — прежний `64b6abed…`, budget `f12c9615…`.
Это не полный профиль последующей поправки.

Normal POST1/POST2 accepted. Fault POST1 unavailable, M1=True, старое
поколение закрыто, F/B здоровы, watchdog=False; POST2 accepted.
Безопасная цепочка ожидаемого **первого** fault-исключения:
`ProjectionBudgetExceeded` (`_result_session_context:382`) → `TimeoutError`
(`timeouts.__aexit__:116`) → `CancelledError` (`protocol.query:369`).
Она относится к намеренно удержанному подтверждению COMMIT и **не является
причиной первоначального отказа второго POST**. В этом опыте оба вторых POST
приняты; исходный repeated-отказ не воспроизведён, причина не установлена.
Новые циклы повторения ради PASS не запускались.

Временный plugin наблюдал только новый native test, оборачивал базовый
`_refuse`, transaction boundary, HTTP post и proof helpers, сохраняя originals.
Другим тестам fixture сразу возвращала управление. Он не тождественен более
позднему предложению reviewer о Python exception/call trace без замены методов.
Trace-опыт по этому новому предложению **не выполнялся**. Нынешний журнал
не выдаётся за его независимую приёмку или причинное объяснение старого сбоя.
Plugin после завершения удалён из дерева; малая воспроизводимая копия
`/private/tmp/graf-t112-unknown-post-observer-20261116.py`, SHA-256
`66f44ab4f1f38261aca3df3342cce0aab8097f0144e190fac7026df7e0387cd5`.

## Причинная поправка счётчика

Простое удаление подавления с count1 до B дало **2 FAIL**,56 deselected,
9.92s pytest/16s runner/EXIT1. Контейнер штатно удалён.
Журнал `/private/tmp/graf-t112-native-commit-raw-checkin-20261116.log`, SHA-256
`ef4c38ea9f869ee5ec7c13adb3a8717d3b8d982e3903381c1bc2a2edf689ca80`.
В обоих случаях наблюдались два checkin одного entry до завершения HTTP.
Этот RED сохранён; он не объявляется двумя возвратами одной и той же выдачи.

Минимальное уточнение использует уже существующий публичный checkout callback:
COMMIT фиксирует ordinal текущей выдачи (`len(checkouts)`), raw collector
сохраняет ordinal **каждого** checkin целевого entry после COMMIT. В markers
попадают все возвраты именно этой выдачи; фильтра по наличию первого marker
больше нет. Повторный checkin до новой выдачи останется в списке и провалит
count1. Проверка fault выполняется в ранней точке; дополнительная проверка
count1 normal/fault — непосредственно до получения B, при закрытом gate.

Сохранённый raw вывод offsets `[0,1]` в обоих случаях показывает: второй
возврат относится уже к следующей выдаче слота. Поэтому его нельзя включать
в число возвратов аналитической COMMIT-выдачи. Прочитаны настоящий
`session_renewal_middleware` и его регистрация в `_setup`: после handler он
может использовать тот же pool. Точный caller второго возврата отдельной
трассой не установлен; его происхождение именно из renewal не утверждается.
Последующие законные возвраты B/F/POST наблюдаются, но не пересчитывают уже
проверенную целевую выдачу. Native/Session методы, SQL, сроки, настройки пула,
assertions M1/F/B и последующего POST не менялись.

## Проверка нынешнего кандидата

Адресный профиль после корреляции: **2 PASS**,56 deselected,10.30s pytest/
15s runner/EXIT0; один прежний warning, без skips. Normal0.720s/fault1.554s,
M1 faultTrue, foreign/reuseTrue, watchdogFalse, raw offsets `[0,1]`.
Оба следующих POST и полные сравнения прежних строк прошли.
Cleanup `isolated_container_removed`, `postgres_test_result=pass`.
Журнал `/private/tmp/graf-t112-native-commit-checkout-window-20261116.log`,
SHA-256 `aae40ec23e0989343af25e53e407cbc9b01ca4fa772001a9dc8695a8255b3bfe`.

| Текущий файл | SHA-256 |
| --- | --- |
| Integration | `1a3267352ff6b838daa153f5dacc105a98eaed29d57a930f8e244ecf8229daa0` |
| Budget, неизменён | `f12c96159912479d5fc3c59a00bd5df0eccc944486b4900df9b7edebf72f5eb7` |

87 не складывается с2; прежний общий профиль не приписывается новому source.
Все три процесса этого продолжения завершены; их session IDs не опрашивать.
Следующий обязательный шаг — независимое ревью нынешней корреляции и точных
логов существующим `/root/public_counter_readiness_review`. Подготовлено
поручение `/private/tmp/graf-t112-ordinary-raw-checkin-review-request-20261116.txt`;
сам файл не доказывает доставку/живое ожидание/приёмку.

18 mapped inputs проверены SAME. Reviewer-owned checklist124/0 из полученного
ревью не менялся. Analyze `0252da92dd9c3ff435a13bf55c0234afbb010abd9a3a1c49f8e42461427c18dc`
применим к прежним FR-021/025/SC-006; новых требований/схем/получателей нет.
Scoped сверка: normal return, M1 unknown ack, same-pool F/B, явный следующий
POST сохранены; остатки уже в открытых T112/T113. Полная F273 не converged.
Независимый вердикт по новой поправке не получен; P2=0 не объявляется.
Отдельный unknown repeated HOLD сохраняется независимо от подсчёта.

Контент/вёрстка и production не менялись. Почта ГРАФ — Postal, миграции на
Stalwart нет. T098/T113/restore/T0/Product Radar и коммерческие AC открыты.
Сбор выключен; master merge freeze до принятого выпуска Метрики сохранён.
Новых PR/merge/Full/CD/публикаций/визитов/регистраций/оплат этим опытом нет.
