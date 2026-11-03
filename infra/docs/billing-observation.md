# Наблюдение за сверкой биллинга: установка и восстановление

F140/T077/O16 J5/J6, требования A1–A7 в
`specs/140-user-account-billing/contracts/operator-observation.md`.
Это инструкция для отдельно разрешённой установки. Наличие файлов, успешные
изолированные проверки и слияние PR сами по себе не означают работающую почту.

## Назначение и границы

Основное задание работает на существующем astraglobal, встречное — на ОС
существующего 2brain.dev. Они независимы от rec-maintenance, Temporal и общей
PostgreSQL. Остановка Docker на одном узле обнаруживается другим по возрасту
сохранённого tick, если второй узел и почтовый маршрут доступны. Общий отказ
двух узлов, сети или почты не имеет гарантии тревоги и не является принятым
владельцем риском.

Ответственный — владелец GRAF; канал — выбранная им почта. Реальный адрес,
ключ Postal, URL с паролем и ключи SSH существуют только в закрытой
эксплуатационной конфигурации. Не переносить их в Git, отчёты, командную
строку, переменные общего приложения или журналы systemd/Docker.

Проверка выполняется каждые300с. Подтверждённые технические failure/conflict
либо возраст отсутствующего свидетельства≥900с создают тревогу. Возраст
неизвестной попытки не является финансовым отказом. Повтор failed/unknown
письма допускается не ранее300с после сохранённой reservation; durable
accepted того же message key исключает повтор. Crash между приёмом письма
и сохранением исхода оставляет unknown и может привести к физическому дублю.
Accepted подтверждает транспорт, не доставку в ящик или прочтение.

Журнал сохраняет исходные detected/deadline, назначение владельца, важность,
подтверждения и реакцию. Успешный следующий probe не закрывает incident.
Конкретный accepted_risk требует отдельного явного решения владельца здесь,
с привязкой к текущему incident/basis и исходному сообщению. Общая политика,
молчание, письмо и root/DB role не заменяют такое решение.

## До установки

1. Получить независимые code review/converge и обязательные проверки точного
   исходного SHA и основы. Установка и реальная почта имеют отдельное
   эксплуатационное разрешение. До него не выполнять команды ниже на рабочих
   узлах, не включать timers и не отправлять учебное письмо.
2. На каждом узле выбрать уже доставленный application image с точными ID,
   platform и source SHA. Сверить `org.2brain.graf.dev.source-sha` и единственный
   `GRAF_DEV_SOURCE_SHA` в образе. Нужны установленный Docker, `/usr/bin/timeout`
   внутри существующего Debian-образа, Python3 на ОС и закреплённые host keys.
   Автоматического pull/build/Compose start/restart нет.
3. Подтвердить независимый Postal route с обоих узлов без зависимости от
   rec-maintenance/общей БД. Не останавливать рабочие службы ради учения;
   изолированные сценарии отказов не заменяют проверку реального маршрута.
4. Завести выделенный непривилегированный числовой UID/GID1000–60000,
   свободный на соответствующем узле. Он владеет только своим узким журналом,
   не Docker socket, конфигурацией запуска или общими секретами приложения.

## Файлы установки

Root устанавливает `infra/scripts/billing-observation-probe.sh` и
`infra/scripts/check-billing-observation.sh` в `/usr/local/libexec/` с
владельцем root, режимом0755 и недоступными для записи другим родителями.
Второй сценарий допускает только tick/witness. Первый — фиксированные режимы
source/status и локальные административные операции. Его общий код не даёт
SSH-клиенту права выбирать режим: отдельные forced command и sudoers ниже
закрепляют ровно source либо status. Окружение и stdin клиента не передаются.

Root создаёт закрытый каталог `/etc/graf/billing-observation` и разносит
разделы примера `infra/env/billing-observation.example.json` по файлам:

| Файл | Владелец / режим | Содержимое |
| --- | --- | --- |
| `launcher.json` | root /0400 | Точные image ID/source/platform, выделенный UID, существующая разрешённая Docker network, роль узла. |
| `source.json` | root:выделенный GID /0440 | Source profile/generation и существующий exact-maintenance database URL. Только на узле БД. |
| `mail.json` | root:выделенный GID /0440 | Роль/profile/generation/binding_version и узкая конфигурация Postal с получателем. Без общих Settings. |
| `ssh.conf`, `known_hosts` | root /0400 | Фиксированные aliases/identity files и предварительно проверенные ключи узлов. |
| `relay/decision.json`, `relay/recovery.json` | root:выделенный GID /0440 | Create-once перенос конкретного решения либо явная сверка восстановления. Только на время соответствующей операции. |

Роль основного узла — primary, встречного — witness; его source.json читает
БД отдельно от встречного задания. Source profile и проверенное поколение
согласовать с эксплуатационной lineage. Binding version — неприватный UUID,
который меняется при изменении получателя. Пример содержит недопустимые
заполнители; он не является готовой рабочей конфигурацией.

Root создаёт `/var/lib/graf-billing-observation` с выделенным UID/GID и0700;
его родители root-owned без записи группе/остальным. Journal создаётся только
через явный `--activate`. Для временных входов systemd создаёт root-owned0700
`/run/graf-billing-observation`; ручные операции используют такой же каталог.
Если нужен backup/restore, `/var/lib/graf-billing-observation-backup` — отдельный
закрытый mount проверенного хранилища с тем же UID/GID и0700, не копия рабочей
БД или стенда. У `relay/` root:выделенный GID0750; его родители root-owned.
Ни адрес, ни секреты не входят в backup журнала.

## Узкие SSH-права

Основной узел использует два разных ключа: alias `graf-billing-source` для
source и `graf-billing-peer` для встречного status. Встречный использует
собственный status-ключ к основному узлу. `ssh.conf` задаёт только проверенные
HostName/Port/User, отдельный IdentityFile, `IdentitiesOnly yes`,
`IdentityAgent none`, `AddKeysToAgent no`. Ключи root-owned0400, доступ к F273
и его каналу не заимствовать. Не добавлять shell, ProxyCommand, LocalCommand,
Match exec, изменяемые Include или пересылку сокетов.

На принимающей стороне выделенный SSH-пользователь не получает Docker group,
общий sudo или интерактивный доступ. Для каждого ключа root закрепляет
`restrict` (включая запрет user rc, PTY и forwarding), проверенный `from=`
и ровно одну команду. Шаблон без настоящих ключей:

```text
command="/usr/bin/sudo -n -- /usr/local/libexec/billing-observation-probe.sh --source",restrict,from="VERIFIED_OBSERVER_ADDRESS" ssh-ed25519 REPLACE_WITH_SOURCE_PUBLIC_KEY
command="/usr/bin/sudo -n -- /usr/local/libexec/billing-observation-probe.sh --status",restrict,from="VERIFIED_PEER_ADDRESS" ssh-ed25519 REPLACE_WITH_STATUS_PUBLIC_KEY
```

Sudoers разрешает каждому такому пользователю только точные соответствующие
путь и аргумент с `NOPASSWD:NOSETENV`; никаких wildcard, оболочки, редактора,
произвольного image/module/path или relay. У sshd для этих пользователей
выключены PermitTTY/PermitUserEnvironment/PermitUserRC, включён
DisableForwarding; перед применением проверить `sshd -t` и `sudo visudo -c`.
Forced command не исполняет клиентскую команду. Клиент вызывает только alias,
без удалённой строки команды; stdout ограничен16KiB, stderr не публикуется.

## Первое включение

После разрешения root выполняет отдельно на каждом узле:

```sh
/usr/local/libexec/billing-observation-probe.sh --activate
/usr/local/libexec/billing-observation-probe.sh --status
```

Activate не отправляет письмо. Повторная activation поверх journal/hold
запрещена. Status только читает и не освежает tick. Доступность контейнера/API
не заменяет progress producer или durable tick наблюдателя.

Установить только свои service/timer из `infra/systemd/`: основную пару
на astraglobal, witness-пару на2brain.dev. Включать только соответствующий
timer после проверки режима и конфигурации. Интервал300с, без случайной
задержки; полный запуск ограничен60с. Source/status wrapper ограничен25с,
сама БД15с/statement5с/lock2с, один Postal POST≤10с. Host оставляет4с на
проверку удаления только собственного именованного контейнера; внутри
контейнера отдельный timeout убивает задачу и после потери Docker-клиента.
При kernel/daemon outage удаление не гарантируется и запуск не считается
успешным. Временные входы при неподтверждённой очистке сохраняются закрыто
для разбора, не удаляются как мусор активной проверки.

Проверить реальные периодические ticks с обоих узлов, частичный source envelope,
доступность независимой почты и получение разрешённого учебного письма
владельцем. Сохранять только SHA/время/коды/контрольные суммы и ссылки на
приёмку; не копировать адрес, endpoints, SQL, ключи, URL с паролем или текст
частной переписки. Не объявлять принятие Postal подтверждением ящика/чтения.

## Журнал, backup и восстановление

Один authoritative append-only `journal.jsonl`: вся цепочка, activation,
accepted/unknown, consumed refs и исходные сроки. Второй изменяемый snapshot
не создаётся. Lock≤2с объединяет writer/relay/backup. Before-record hold содержит
только постоянный marker. Fsync файла запрета/каталога предшествует append/fsync
journal; снять можно только свой проверенный marker, затем fsync каталога.
Только после всей цепочки разрешены внешний POST и успешный ответ.

Старый hold, обрыв строки, ошибочная цепочка, исчерпание места или лимита не
чинятся обычным запуском. Не удалять/обрезать tail, не пересоздавать историю,
не очищать hold копированием. После ошибки fsync каталога уже после unlink
сценарий возвращает отказ и пытается вернуть hold; отказавшая FS не даёт
гарантии сохранения нового marker. Синхронный fsync не прерывается Python
timeout: его ограничивает внешний runner, с честной границей kernel outage.

`--backup` под тем же lock создаёт отсутствующий `/backup/journal.jsonl`,
синхронизирует всю цепочку и возвращает sequence/head. При hold отказывает.
Отдельно сверить копию/последнее подтверждённое head в закрытом хранилище.
`--restore` допускает только отсутствующий журнал, проверяет полную копию,
восстанавливает в отдельный candidate и сохраняет recovery hold до сверки.
Отсутствующий рабочий journal после activation не является новым bootstrap.

Для явного `--recover` root-custodian сначала сверяет целую цепочку,
expected_head, последнюю проверенную копию и реальные решения. Закрытый
create-once recovery.json содержит expected_head/source_generation/evidence_ref.
Same generation допустимо только для storage-only сверки целой цепочки без
source discontinuity. Restore источника или discontinuity требует нового
сверенного source_generation и согласованного закрытого профиля. Accepted,
consumed refs, исторические попытки и паузы не удаляются и не сокращаются.
Неверный/чужой/повреждённый marker или неполный tail требуют отдельного
разбора custodian; автоматического присвоения такого файла нет. Откат всех
доступных копий нельзя обещать обнаружить по локальной hash-chain.

Пределы:16KiB на record/manifest,64MiB/262144records на journal,
500incident generations,255 UTF-8bytes на refs; весь replay входит в60с.
Лимит даёт hold/отказ без trimming/удаления/автоматического архива.

## Реакция и откат установки

`--transfer` читает только root-owned create-once decision.json из relay.
Он связывает source/profile/generation, incident/generation, текущие
expected_basis_revision/basis_hash, action, evidence class/ref, message ref/time
и digest точного реального решения. Один durable record объединяет переход
и consumed ref; повтор, старое основание или неверная привязка отвергаются.
Root-custodian переносит фактическое решение, а hash не удостоверяет автора
чата. Investigating не закрывает; resolved требует evidence устранения;
accepted_risk требует конкретного явного решения владельца здесь.

Для отката остановить/отключить только соответствующий новый timer и отозвать
только его выделенные source/status ключи и точные sudoers-разрешения.
Сохранить journal/hold/accepted/consumed/backup и приватную конфигурацию по
штатной custody-процедуре. Не останавливать финансовые службы, не менять
их locks/commits/retry/оплаченный срок/согласие, не трогать F273 и чужие задания.
Полный FR089/O6, остальные источники/сроки/58gaps и T070/T077/#4932 остаются
открытыми до всех исходных критериев; этот run guide их не закрывает.
