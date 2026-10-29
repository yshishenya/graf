# T113: независимое ревью runtime binding и фильтра T0

30.10.2026, проверяющий `/root/f273_release_boundary`, исполнитель `/root`.
Ветка `codex/f273-local-period-20261029`, основа
`a4355571bd214eead4dcd7a9bfdc636bf5d39f32`, high-risk-product.

## Объём и текущий результат

Прочитан текущий diff и необходимые целые функции ingest/milestones,
Compose/CD/image helper и профильных тестов. Сверены принятый проект B/T0
и два независимых до-кодовых отчёта. Ревьюер код и тесты не менял и ничего
не запускал; доказательства ниже — прочитанные журналы исполнителя.

**SCOPED PASS реализации runtime binding и фильтра T0.** Блокирующих
дефектов прочитанного кода не найдено. Последний пробел проверок закрыт:
сначала ledger-профиль вызывал примитив без callback и не покрывал sync ветку
нового `inspect.isawaitable`. По замечанию ревьюера исполнитель добавил четыре
прямых случая sync/async × valid/unknown provider. Они проверяют callback,
сохранённые состояния, один immutable счёт при повторе и ноль строк при отказе.
Тест прочитан, финальный PostgreSQL профиль116PASS подтверждён журналом.

## Проверенный код

| Граница | Вывод |
| --- | --- |
| Runtime до DB | source/image получаются из двух обязательных process env и проверяются полными регулярными выражениями до sessionmaker. Readiness не является источником expected. |
| Packaged schema | ScriptDirectory читает migrations относительно установленного package. Единственный head сравнивается с revision БД; отсутствующий head закрывает admission. Тяжёлый worker не импортируется. |
| DB metadata | Прямой SELECT текущей удерживаемой сессии использует pg_catalog и public.alembic_version/user_identities. Ровно одна строка, совпадение DB name с разобранным Settings.database_url и packaged revision обязательны. Cluster ID/name/OID/schema не читаются из receipt. |
| T0 | После реального read_ready для local_only проверяется серверное created_at текущего principal: не NULL, timezone-aware и строго `started_at < created_at <= clock_timestamp()`. Client occurred_at не определяет принадлежность. Ранние account-вехи не ждут результата; T112 остаётся закрыта. |
| Последний await | Callback вызывается после DB SH273,3 и account identity lock. После последнего await metadata заново выполняются legal/mode/flags/read_ready и local configuration/T0 проверки; нового await внутри callback нет. |
| Lifetime | Прежний filesystem SH, один owner task вокруг всей DB-сессии, repeated shield, извлечение результата/исключения и освобождение после close сохранены. Дополнительный callback await находится внутри этого владельца. |
| Доставка | local_only возвращает пустой tuple до resolver/exporter. INSERT создаёт оба not_requested. Нет commit/transport внутри callback; сеть не добавлена. |
| Callers | Обе HTTP-формы и server-auth используют тот же ingest; direct ledger caller остаётся низкоуровневым примитивом. Принятая account+event уникальность и immutable on-conflict результат не менялись. |
| Service image IDs | Compose передаёт общее process env из отдельных API/maintenance operator переменных. CD получает pinned ID каждого service/side; прежние IDs не приравниваются. |
| CD пути | Candidate binding задаётся после image prepare до первого up; остаётся при позднем recreate API. Оба previous-пути вызывают bind previous до up; compatibility вызывает bind candidate и сбрасывает stale previous значения. |
| Inspect | Helper сверяет actual running `.Image` с pinned ID, затем требует ровно один env ID при declared capability или фактически присутствующем env. Missing/wrong/duplicate не принимаются. Ошибка выводится конечным reason, полный env не печатается. |
| Совместимость | Наличие capability записано в существующую service metadata из environment Compose точного source. Историческая запись без поля и без env сохраняет только проверку image. Формат image/pull_policy override не расширен. |
| Закрытые ворота | Безусловный `activation_recovery_unverified` в legal_basis_gate остаётся. Произвольный receipt, даже с совпавшим binding, не включает рабочую аналитику. |

## Исправление перехода со старого выпуска

Первоначальная промежуточная проверка `side == candidate` требовала новое env
даже у завершённого исторического candidate, созданного до capability.
Это могло сломать `current-override` и его существующих потребителей.
Исполнитель самостоятельно выявил и исправил этот дефект до окончательного
ревью: `activation_binding_required` определяется по Compose указанного source,
а отсутствующее поле старой записи не превращается в true. Новая регрессия
проходит finish и current_override с исторической записью без capability.

Отсутствие env у такого старого runtime — не analytics PASS и не доказательство
безопасного старого writer. Общий rollback/revoke/capability gate остаётся
открытым. При declared capability отсутствующее env по-прежнему отклоняется.

## Прочитанные причинные доказательства

- До исправления ingest: **12 failed /2 passed** на отрицательных binding,
  границах T0 и изменении решений во время нового await. Это ожидаемые RED;
  положительный контроль не был единственным результатом.
- Финальный PostgreSQL профиль: **116 passed,2 warnings /29.15s**;
  журнал подтверждает удаление собственного изолированного контейнера.
  Проверены mismatch шести expected, before/equal/after T0, NULL/future
  created_at, неверная trusted DB name, unknown/multiple DB revision,
  новые callback ожидания, прежние lock/cancellation/HTTP/ledger случаи и
  отдельные sync/async callback положительные/отрицательные случаи.
- Image/CD до кода: **6 failed /2 passed**. После capability correction:
  **33 passed /0.32s**, включая исторический candidate/current_override,
  wrong/missing/duplicate env, executable up каждого recovery-пути и
  compatibility candidate после причинного отказа previous up.
- Прочитаны скрипт и JSON настоящей маленькой Docker-пробы: встроенный source,
  actual image/env соответствие, отрицательный wrong env и cleanup своих
  контейнеров/анонимных томов/образа. Проверяется настоящий helper inspect;
  приложение GRAF не собиралось и не запускалось.

Пауза metadata-теста устроена внутри AsyncSession.execute **до** вызова
реального execute: это причинное управляемое ожидание нового callback, затем
реальный SELECT и финальная проверка. Она доказывает свежесть после этого
await; не следует описывать её как наблюдённую SQL-блокировку самого metadata
SELECT в pg_stat_activity. Отдельный прежний identity-wait тест действительно
наблюдает PostgreSQL lock wait и подтверждает порядок после account-lock.

Operating receipts в положительных fixtures учебные; production verifier
не готов. Старые HTTP/lifetime fixtures подменяют read_ready, а отдельные
binding tests восстанавливают настоящий read_ready с реальными DB metadata.
Это корректное разделение проверяемого среза и незавершённой эксплуатации.

## Требования и открытая приёмка

Требования B/T0 и проект SHA-256
`1f52514ca2339ba67e58fb50f2104670e282b646c8f911a33688e290df65fc13`
приняты до кода; до-кодовый общий итог117/0 относится к качеству требований.
Никакие отметки checklist в этом проходе не менялись. Старый A gate не
использован для возврата требования всей прежней marketing history.

T0 не установлен. Initial verifier, полный product drain, реальный restore/
rollback и непрерывность послеT0, T112, отдельная рабочая приёмка остаются
открытыми. Учебный PASS, коммит или технический выпуск не доказывают трафик,
новых внешних клиентов, активации, оплаты или выполнение коммерческой цели.

## Контрольные суммы снимка

| Файл | SHA-256 |
| --- | --- |
| ingest.py |a442bb42c8d8d0b2db29bb6e07dcf505c3a9e83031ed2d727db1d6c365a47d9f |
| milestones.py |01ba585942c8322692307088cc3af6ece5af8d5d189956a468781a70e252d3d1 |
| infra/docker-compose.yml |9098cb15c8c4a675beae529664e128d46a2dc50671dee8171d05b659b482bcc6 |
| release-images.py |4715a72ad17ca4d78114e2ecd354e9f35f43e9a6e1d355ca4a7bcea24ed95f7d |
| cd-remote-runtime.sh |86c88314db12f9f10423b5e38c44c4682092c358f521ac590b4e12e9539b0d35 |
| test_release_images.py |0696c3291db8a9b61f383ea7229ad5e6993f50d82097dda9418bea7049488acd |
| test_activation_milestone_ingress.py |21b4fbfa667e4ba74786af01768d0cf35655bd5ef665ff082c16f393b3099634 |
| test_activation_milestone_ledger.py |205d44df6f1f29ed4ac2aedae51212acb7baefa5b98112b089c66e2311741a20 |
| Докодовый runtime review |a52433f0115ee017a9d79bc1bfba7bdf060ac0a40fbbcd80b079e43a32aa1a8b |
| Докодовый B/T0 review |0b633c9c405ea1a3f67f35a672c2251621952c7e92307a56df471876ac9817d0 |
| binding RED log |7509a36bdabd79a0f02dd3382505b1fa9cc7bb54688885a943afe224c80b6f23 |
| binding final116 log |8b1fcdd3a58e8659cb35108036c4c241015cc39f0ff8bec024d7cb074dfa6ec1 |
| image RED log |1192871d2d9c6af1d7651fb1160543b4f4b6cce6c516d5d285dbb3ab5073393d |
| image final33 log |c41c7e0a39633c7f6bb7f438c9c8dcaad58c030ef685dd44e9552954261dc1f9 |
| Docker probe script |df692a948ac01b3315d607e85835813f5dca7b08b2d8d431d8974fa5e29f73a9 |
| Docker probe result |215b75a90bcbe52614c85b91c543f7b1a7a8c34dd0a630bcf3dd747889bb41f0 |

Изменён только этот разрешённый отчёт. Ревьюер не менял код/требования/
Git/GitHub/runtime, не запускал тесты/сборки/подключения и сохранил чужие правки.
