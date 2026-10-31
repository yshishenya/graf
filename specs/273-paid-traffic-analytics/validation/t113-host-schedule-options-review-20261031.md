# T113/J1: два варианта ежедневного запуска по UTC

31.10.2026. Независимый проверяющий `/root/f273_release_boundary`.
Основа `ad363160d049b9bed1346955ba0af5cc806c9470`, F273/T113/#7804,
`high-risk-product`. Этап только чтения и сравнения вариантов; записан только
этот отчёт. Чужие изменения сохранены. Код, требования, планы, чек-листы,
Git/GitHub, сервер и Dev не менялись. Тесты и серверные операции не запускались.

## Вывод

**Рекомендован вариант1: существующий host cron, ежеминутный вход и проверка
UTC внутри нынешнего bootstrap до подготовки uv.** Он сохраняет прямо
принятый host-cron путь из
[полного проекта](t113-full-operator-design-20261030.md#плановая-coherent-backup--отдельный-безопасный-исход-отказа).
Защиту от повторной автоматической остановки нужно встроить в существующую
durable attempt-модель. Одного сравнения даты последнего завершённого backup
недостаточно. Минимальный конкретный проект приведён ниже.

Вариант2 с прежними systemd service/timer технически допустим без нового
daemon или зависимости и лучше выражает UTC непосредственно календарём.
Однако это замена принятого механизма local backup, переопределение прежней
PostHog службы и дополнительная проверка sandbox/окружения/timeout/catch-up.
Он требует согласованного изменения полного проекта, plan/operations/quickstart
и отдельного точного разбора конечных drop-ins до кода. Одного `OnCalendar`
и `--scope` для него недостаточно.

Это **сравнительный проектный вывод, а не J1 PASS**. Полный indirect-execution
inventory и проверка всей установки остаются открытыми. Численные продуктовые
требования не расширяются: local backup03:10 UTC, local verify03:15 UTC,
предел операции600с, freshness<26ч и безопасный возврат продукта прежние.
Счётчик суточных запусков — служебная защита от повторов, не новый T0/cutoff.

## Прочитанные факты и их пределы

Закрытые ignored evidence основного исполнителя содержат наблюдение
31.10.2026 12:07 UTC: Ubuntu-пакеты `systemd 255.4-1ubuntu8.18`,
`cron 3.0pl1-184ubuntu2`, anacron not-installed. В снимке cron.service
загружена/активна, из GRAF units перечислены только runtime-guard.service/timer.
Прежние backup/retention units существуют в исходниках, но их установка этим
снимком не подтверждается. Package query завершён exit1: отдельные известные
records не превращены в доказательство отсутствия всех иных исполнителей.

Второй файл, наблюдение12:21 UTC, указывает Europe/Amsterdam. Прочитанные
выдержки штатного cron manual прямо говорят: per-user timezone не
поддерживается, `TZ` влияет на дочернюю команду, а не на время запуска cron;
manual предлагает проверку даты внутри дочернего скрипта. Поэтому строка
`10 3 * * *` плюс `TZ=UTC` не выполняет принятый UTC договор. Поддержку
`CRON_TZ` также нельзя предположить без доказательства конкретной реализации.
Глобальную зону сервера менять не требуется.

Ни перечень1206 loaded units/523 unit files, ни имена файлов ещё не доказывают
полную цепочку запуска. Снимок явно содержит непрочитанные cron spool и
root user-systemd root. Содержимое hooks/config/исполняемых файлов, effective
units и доступ к GRAF ещё требуют J1. Reviewer SSH не выполнял и не утверждает
актуальность установки за пределами предоставленных наблюдений.

## Сравнение

| Критерий | 1. Host cron и UTC-предикат | 2. Прежние systemd timers и local drop-ins |
| --- | --- | --- |
| Соответствие принятому full-operator design | Сохраняет явно выбранный host cron | Меняет механизм, сохраняя время и результат |
| UTC и сезонные переводы часов | Cron вызывает каждую минуту; сам Python считает UTC, не локальные часы | Явный `OnCalendar=*-*-* 03:10:00 UTC`; зона сервера не участвует |
| Повторный запуск | Нужен durable суточный claim под общим lock | Общий lock и durable попытки всё равно нужны; unit serialization не защищает от второго entrypoint или ручного запуска |
| Пропущенный запуск | Нет автоматического catch-up в рабочее время; stale/failed запрещает готовность | Старый `Persistent=true` может остановить продукт после boot в произвольный час; для backup необходим явно выбранный запрет catch-up |
| Объём доверенной установки | Одна точная root cron запись, существующий bootstrap и attempt | Две пары прежних units, их drop-ins, загруженные свойства, environment и ограничения доступа |
| Зависимости и процессы | Короткий stdlib Python вход1440раз/сутки; вне нужной минуты без uv/Docker/БД | Существующий systemd; без ежеминутного Python, но более широкий unit proof |
| PostHog defaults | Не затрагиваются | Исходники/defaults можно сохранить, но конкретные units установки переводятся в другой scope; одновременно обслуживать оба scope ими нельзя |

## Вариант1: минимальный конкретный проект

1. Одна canonical root entry в уже принятом host cron вызывает существующий
   trusted bootstrap с фиксированным режимом scheduled backup каждую минуту
   (`* * * * *`). Ни `date`, ни UTC-предикат в shell-строку не переносить:
   точные argv и источник bootstrap проверяет тот же J1. Один фиксированный
   режим добавляется в нынешний entrypoint полного оператора, не отдельный
   helper/daemon/parser. Сейчас bootstrap принимает только `--preflight`:
   предлагаемого рабочего режима в коде ещё нет.
2. В bootstrap используется его уже изолированный `/usr/bin/python3 -I` и
   stdlib UTC clock. До `_prepare`, uv sync, Docker/БД и временных каталогов
   определяется UTC день и минута03:10. В другое время — конечный `not_due`,
   без изменения ready/attempt/receipt и без заявления об успешной копии.
   Входящий `TZ`, locale, PATH, supplied date/clock/pass не выбирают расписание.
   Время и слот вычисляются доверенным процессом, а не аргументом caller.
3. Due-вход сохраняет вычисленный слот в памяти, проверяет installation/source,
   общий deployment lock и полный preflight. Общий конечный deadline начинается
   для операции и включает подготовку; uv не получает новый независимый600с.
   После подготовки не требуется снова попадать в секунду03:10:00: операция
   законно продолжается в том же конечном запуске. Ожидание lock/подготовка
   не разрешают бесконечно отложенную остановку или автоматический повтор.
4. Под deployment lock сначала read-only проверяется служебный суточный claim.
   Повтор уже потреблённого слота завершается без revoke/stop/перезаписи
   результата. Перед первым stop под прежним filesystem EX выполняется
   повторная проверка, durable revoke и fsynced claim в **существующей**
   `backup-attempt.json` модели. Не создаётся ещё один state-файл. Нужны
   versioned поля последнего потреблённого scheduled UTC слота/операции;
   они сохраняются при каждом следующем ручном и автоматическом attempt.
   Обычный manual backup не стирает claim и не разрешает вторую автоматическую
   остановку в тот же день. Слот заявляется до stop, а не после export.
5. Нынешний `_create_coherent_backup` создаёт in_progress внутри copy после внешнего
   stop/drain; `_previous_backup_attempt` требует точную схему v1. Поэтому
   добавить проверку started_at в текущую функцию недостаточно. Верхний
   оператор должен владеть одной начатой attempt от предоперационного claim
   до completed/failed и передавать её своему внутреннему backup core, который
   не создаёт второй run/attempt. Точные версия/переходы и read_ready/verify
   потребители обновляются вместе, через отдельный precode/code review.
   Старые записи без поля не означают «слот свободен»: переход требует
   проверенного provisioning/migration при закрытом scheduling, с сохранением
   истории, initial и T0. Отсутствующий/повреждённый/future state — HOLD.
6. Failed, cancelled или crash/in_progress после claim **потребляют слот**.
   Автоматического повторного stop в тот же день нет; unknown не исправляется
   новым run. Разрешённая операторская recovery остаётся прежней. Для monotonic
   high-water слота дата назад или future record означает HOLD, а не сброс
   дневной защиты; ручные попытки не понижают high-water. День вперёд не
   позволяет перезаписать неизвестный actual restore или unresolved attempt.
   Ошибка durable claim запрещает stop. Отмена не даёт completed/ready.
7. Дальше выполняется именно прежний planned coherent backup600с с
   pre-stop upload/resource checks, drain/export/byte proof/cleanup и
   безопасным resume. Последняя попытка и manifest доказывают результат;
   claim или exit0 `not_due/already_claimed` не заменяют их. Готовность не
   восстанавливается из прежней хорошей копии после failed новой попытки.
8. Проверка03:15 UTC идёт прежним retention scheduler через явный graf-local
   scope к **тому же ordinary verify**. Default PostHog branch сохраняется.
   Подмена scope/вызов старого ClickHouse пути запрещают local PASS.
   Backup может законно идти до03:20: verify не запускает второй backup,
   не обходит lock и не останавливает продукт. Его contention обрабатывается
   конечным ожиданием в пределах собственного принятого deadline либо HOLD;
   готовность определяется свежим выполненным receipt, не наличием trigger.
9. Cron tick мог отсутствовать из-за downtime/блокировки/прыжка часов.
   Нельзя обещать ровно одно успешное выполнение при отказе узла. Защита даёт
   максимум один автоматический stop на слот; отсутствие свежего результата
   обнаруживается прежними freshness/admission/alert gates. Произвольный
   дневной catch-up с остановкой продукта этим вариантом не вводится.

Это небольшое уточнение оператора, но оно относится к high-risk lifecycle.
Нельзя устанавливать cron прежде завершения общего initial/backup/verify/
restore proof и приёмки длительности паузы/клиентского повтора.

## Вариант2: условия технической допустимости

Использовать существующие имена graf-posthog-backup и retention-enforce,
без новых unit/daemon. Сохранить исходные PostHog02:30/03:15 UTC defaults;
версионированная пара local-only service/timer drop-ins задаёт единственный
scope этой установки. Это взаимоисключающие режимы, не скрытый второй запуск.

- В timer сначала сбросить список `OnCalendar=`, затем задать только backup
  `*-*-* 03:10:00 UTC` и verify `*-*-* 03:15:00 UTC`. Проверять весь effective
  список, `Unit`, Accuracy/RandomizedDelay и отсутствие добавочных monotonic
  triggers/drop-ins. Backup `Persistent=true` исходника неприемлем без нового
  решения о catch-up: минимально для local backup явно `Persistent=false`,
  без случайной задержки. Пропуск покрывается freshness/HOLD. Online verify
  может сохранять Persistent=true, поскольку не останавливает продукт.
- В service сбросить старый `ExecStart`, legacy optional `EnvironmentFile` и
  прежние writable lists, после чего задать точные root/argv/окружение и
  необходимые пути нынешнего local оператора. Старый backup shell вызывает
  PostHog, а нынешний retention shell по умолчанию читает ClickHouse: простая
  установка units не создаёт graf-local цикл. Полный actual readback должен
  проверять ExecStartEx flags, прочие Exec-команды, credentials/env/dropins,
  linked/generated/transient state и source bytes, как существующий guard proof.
- `ProtectSystem=strict`, `ProtectHome=true`, `PrivateTmp=true`,
  `NoNewPrivileges=true` сохранять, пока фактические нужные операции не
  сопоставлены с ними. Fixed backup parent, постоянный activation state,
  deployment lock и уже установленный uv/Python должны быть доступны в
  namespace службы; старые `/var/backups/graf-posthog` writable paths этого
  не обеспечивают. Не разрешать целиком root FS ради прохождения proof.
- Старые TimeoutStartSec6h/2h не доказывают общий deadline600с. Внутренний
  оператор владеет600с и cleanup; внешнее принудительное завершение службы
  ровно на600с может уничтожить ещё не завершённый cleanup/безопасный resume.
  До реализации нужно выбрать и проверить конечные KillMode/SendSIGKILL/
  TimeoutStart/Stop свойства, которые доставляют отмену supervisor и не
  отпускают locks/children раньше cleanup. Данный обзор не принимает
  конкретный новый unit timeout по умолчанию как доказанный безопасный.
- Одновременный cron backup и local timer backup запрещён. Manual start,
  reboot и daemon-reload не должны обходить once-per-slot/attempt защиту или
  стирать failure. Одного `Type=oneshot` недостаточно. Откат drop-ins к
  PostHog требует отдельной полной provider readiness; удаление override
  не должно само включать provider или возрастную очистку.

Эти различия делают вариант2 шире текущего минимального проекта. Он не
отвергнут архитектурно, но без конечных drop-in bytes/effective properties
и согласования прежнего host-cron договора **не готов к реализации/установке**.

## Обязательная проверка следующего выбранного проекта

Тестов reviewer не запускал. До кода выбранного пути нужны согласованные
plan/contracts/quickstart и scoped review точных переходов attempt. Затем
причинные RED/green в изоляции: локальные UTC/Europe-Amsterdam и оба DST;
не03:10 без uv/БД/записи; повтор/параллельный tick; manual backup между ticks;
TERM/crash до/после claim и stop; future/partial/missing state; откат часов;
невозможный fsync; contention03:15 и долгий backup; просроченный результат;
reboot/catch-up; cleanup и сохранность продукта. Дополнительно вариант2 требует
native calendar/verify и loaded-effective/namespace/cancellation probes.

Совпавшие source hashes и календарный расчёт не доказывают реальный запуск
полного argv. Рабочая приёмка после разрешённого выпуска должна наблюдать
настоящий вызов, его attempt/manifest/receipt и следующий ordinary admission.
Полный inventory cron/systemd/user roots/at/indirect executables/config/hooks,
права и source/runtime до/после проверяются J1 отдельно. Непрочитанный вход
остаётся HOLD, даже если собственный календарь корректен.

Прежние reviewer-owned117/0 чекбоксы не менялись; этот сравнительный этап
не выдаётся за новый полный пересмотр всех117 требований. Оба общих HOLD,
T112/T113, ресурсы, верхний цикл, T0, выпуск и AC01–AC06 сохраняются.

## Контрольные суммы входов

| Источник | SHA-256 |
| --- | --- |
| closed platform-schedulers evidence | `d1490f4e40a63da58126833851b1445bc6d8c7202ba9b0c54068adae691ddeed` |
| closed native-timezone evidence | `cdfb343d21e731cf64f2077d71d7b53cd6146690d54531de68dbab22b2990901` |
| bootstrap activation-operator.py | `e11efddb4001602014977be3dff5e86550978cf81bfe67f23d7ae60a0bdfbfb5` |
| activation_operator.py package | `b086459d5f3a2a16571041cc96c7120543a6ebfed3dd1ae4887a0a7405ea4ced` |
| enforce-product-analytics-retention.sh | `ab367e1af976707fbc8cff91368e7fbba3b7308db0b2ae856de904587e2a6dcd` |
| backup.service | `8c10724404ce0b0b5594884fa923ee86e2ba125e379f88e2489ef3c5f36b7dcf` |
| backup.timer | `61b1ea01cebbb871f3100c2a292a0e74231890711943d66ee77e06a535f4aed4` |
| retention.service | `0430c51e9a1d94d7e5b86985fc397a4c8a1158214726ff202ffd504c4790e826` |
| retention.timer | `a7b17e7f1244dc33e98f1a1e4de3315c4b4a2113b2bb616506f6046212bcc521` |
| operations.md | `b1c3b925a3b1c68c78ac9eaf17635f6acd4e6c3fc5af789287260aa7d4262d93` |
| plan.md | `c3660a18b172c55d95e2925f506032244e04926aad5560e0eeb76e9c223517db` |
| quickstart.md | `abd8870c4f0e67f7af20486ef6eef1c96b423c4d6287b2074ce0af5f122f456f` |
| full-operator-design | `5d1e069f3fe18f31a21c72c9b0abc41614ff8bfc00c3269f27b1f3cb596738ec` |
| installed-jobs design review | `4326d1e80da2c48a9d2672ac9cbb4b2a14cb6c4cd2792ec497cf3265d11c7906` |

Секретные команды/пользовательские crontab/содержимое встреч в отчёт не
переносились. Приложены только выводы и digests входных метаданных.
