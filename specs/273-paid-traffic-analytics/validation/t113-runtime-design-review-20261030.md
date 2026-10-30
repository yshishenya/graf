# T113: независимое ревью проекта проверки рабочей среды

30.10.2026. Проверяющий `/root/f273_release_boundary`, исполнитель `/root`.
Основа `bade9285ee84b2767e4f1a8ac6ec8ffdbca6cfb8`, полоса
`high-risk-product`. Ревью до кода; рабочая среда не запускалась и не менялась.

## Решение

**SCOPED PASS проекта ограниченной runtime-проверки; обязательных замечаний
до кода не осталось.** Разделение GRAF и сторонних служб, собственные user/
entrypoint правила `rec-minio-init`, фиксированный локальный Docker и
PID/maps алгоритм приняты. Отказ от воспроизведения Compose hash принят:
эта стадия проверяет фактический binding, не полную готовность конфигурации.
Новая архитектура не требуется. Ограниченный проект согласуется с принятым
полным оператором. Ни код, ни рабочее выполнение этим решением не приняты.

Полностью прочитан `.dev/growth/t113-runtime-precode-20261030.md`.
SHA-256 последней полностью прочитанной редакции:
`8844144bffc54735a78a2413fe2fb384b2123b64af9415e4cdc40c4eba016df3`.
Последующее изменение предложения требует сверки именно новых байтов;
этот вывод не следует переносить на иной проект без повторного чтения.

## Принятое сужение: actual binding вместо воспроизведения Compose

Первоначальная редакция `f8351f36d8dd8d07c52c4ae4deeacafbfb4d0b1beb0396c3fbf554567dc35fda`
предлагала повторять Compose `config --hash '*'`. После чтения shell выявлены
LANGFUSE_RELEASE, activation image переменные и нормализация optional secrets,
которых нет в простом `--env-file`. Исполнитель заменил этот подход чтением
реальных Config/HostConfig/Mounts и проверкой их digest/неизменности; последняя
редакция полностью перечитана. **Это сужение принято.** Для данной стадии
новая реализация экспорта CD environment и дублирование shell не требуются.

Фактический config-hash label включается в снимок вместе с настоящей
конфигурацией, но не является самостоятельным policy PASS. Следующая полная
проверка должна получить Settings из той же реальной container configuration
и соответствия mounted paths; host `.env` не является container Settings.
Изменившаяся реальная конфигурация — HOLD. Полная корректность настроек,
secret policy, mounts и доступа остаётся закрыта. Это соответствует требованию
проверить их до будущих мутаций и не выдаёт стабильность за корректность.

Postal network допустимо определить из actual API inspect как единственную
сеть кроме PRIVATE, затем подтвердить её идентификатор и согласованность
membership всех служб существующим inventory validator. Произвольное имя
от caller не допускается. Переход от Config/HostConfig/Mounts к закрытому
digest выполняется лишь в памяти; секреты/пути/полный Env не публикуются.

## Первоначальное замечание1: классы initializers — закрыто

Пункт4 предложения распространяет GRAF source label/`GRAF_DEV_SOURCE_SHA` и
пользователя `twobrain` на всех writers и initializers. Но принятый набор
`INITIALIZERS` включает `rec-minio-init`; в Compose это сторонний
`minio/mc:RELEASE.2025-05-21T01-59-54Z`, без GRAF source и user `twobrain`.
Требование в текущей формулировке всегда отклонит штатную установку.

Минимальная явная матрица:

| Класс | Обязательные проверки |
| --- | --- |
| GRAF writers; `rec-migrate`; существующий `rec-db-runtime-bootstrap` | Pinned image ID из текущего completed release; фактический image inspect ID; source label и точное единственное source env в image и container; container user соответствует `twobrain` из принятой конфигурации; userns policy |
| `rec-minio-init` | Точный pinned ID своего стороннего image; actual image/container/config binding; exited0; user/entrypoint по собственной разрешённой Compose-конфигурации. GRAF source/UID не требуется |
| PostgreSQL/MinIO/Temporal | Собственные pinned image/config/network/health bindings; никаких вымышленных GRAF source или UID100 |
| Running GRAF writers | Дополнительно настоящий host PID/starttime, UID100/GID101 и identity maps |
| Exited/created optional GRAF writers | Image/config/source проверяются, PID0 и отсутствие running; процессные UID/maps не выдумываются. Будущий start требует новой проверки |

Под source label здесь понимается label неизменяемого image, дополнительно
к сверке container; произвольного container label недостаточно. При проверке
Env выбираются лишь нужные ключи с отказом duplicate/missing, полный Env не
выводится. Существующая проверка `_validate_inventory` exited0 для initializers
сохраняется; обязательные writers отдельным условием должны быть running.

## Первоначальное замечание2: локальный Docker и процесс — закрыто

Фраза «daemon локальный Linux» пока не задаёт проверяемого способа выбора
endpoint. Docker client/context может указывать на другой daemon; тогда
`State.Pid` не имеет смысла относительно host `/proc` оператора. Одного
`docker info` с OSType=linux или имени узла недостаточно.

Минимально закрепить существующий локальный Unix socket этой установки
явным endpoint для helper/Compose/inspect; не наследовать DOCKER_HOST/context
caller и не использовать TCP/SSH endpoint. Проверить, что выбранный daemon
Linux, без rootless/userns-remap; container HostConfig.UsernsMode не вводит
другую политику. Не создавать новый socket/proxy/daemon.

Для каждого running GRAF writer: из selected inspect сохранить полный
container ID, immutable image ID, state/PID, StartedAt/restart identity;
прочитать `/proc/PID/stat` starttime, status Uid/Gid и оба map; повторить
inspect и starttime после чтения. Все четыре real/effective/saved/filesystem
UID/GID должны совпасть с принятыми100/101, карты — identity. Parsing stat
должен учитывать скобки и пробелы в поле comm, не брать field22 простым
split всей строки. Отсутствующий процесс, PID reuse, новая state/restart/
container/image/config identity, неизвестная карта — HOLD. Совпадение должно
быть связано с тем же локальным Docker endpoint на всём сроке проверки.
Это конкретизирует уже обещанные PID/maps bindings, не требует запуска
остановленных контейнеров или чтения их данных.

## Что в остальном согласовано

Installed `Python -I -B -m` внутри собственной snapshot/venv lifetime и
существующего lock сохраняет принятый путь. `current-override` читает
существующий completed release, проверяет source/runtime и image-only
override; пустой/unfinished результат остаётся HOLD. Весь inventory/private
network/oneoff набор переиспользуется без ослабления, optional отсутствие и
exited/created состояния различаются. До/после сверяются override, source,
selected container metadata и bindings. В evidence идут лишь счётчики/digest,
не environment, приватные пути, command/health logs или raw inspect.

Все дочерние операции должны оставаться внутри ранее проверенного владения
process group/lock/temp, общего deadline и защёлки отмены. Вызов helper не
принимает произвольную команду. Launcher принимает только точный ограниченный
результат installed модуля; неполный/лишний вывод не открывает runtime verified.
Любой успешный runtime-срез всё равно заканчивается exit1/
`HOLD/full_preflight_not_implemented`, без T0/ready, DB/stop/revoke/provisioning.
Безусловный `activation_recovery_unverified` не снимается.

## 117 требований и согласованность

Повторно перечитаны все117 фактических вопросов, контрольные суммы прежние.
Отметки не менялись; замечания выше относятся к конкретному алгоритму,
а не к отсутствию требований исходной фичи.

| Список | Отмечено | Открыто | SHA-256 |
| --- | ---: | ---: | --- |
| requirements | 16 | 0 | `6755318d0b7a76a9f6439446ad42362272d43859cc6f4b3c045b5c36ad1ed9a2` |
| privacy-measurement | 45 | 0 | `8c390000a2da12cf719348d56c08dcb21d886aac98ba1a90ad3d5c41e141cb4f` |
| security | 27 | 0 | `57f082b0b90faf7a3302db0aa1b9aacd29948641e824578ca4f86eee4dee9cb8` |
| infra | 29 | 0 | `998175e297553cedac7f4d7b2829459fcb3f1b650b3b3b6d072e9065437bfa94` |

Суммарно **117 `[x]` /0 `[ ]`**. Spec/plan/quickstart/activation-milestones/
operations/constitution и принятый полный проект сохранили ранее проверенные
SHA-256. Их полное чтение переиспользовано в рамках разрешённого исключения
F273; новые применимые участки shell/Compose/helper/inventory прочитаны.
Новое полное чтение PRD/всей истории статуса не заявляется. История маркетинга
до T0 не возвращается в условия допуска.

## Основные контрольные суммы

| Материал | SHA-256 |
| --- | --- |
| Полный проект оператора | `5d1e069f3fe18f31a21c72c9b0abc41614ff8bfc00c3269f27b1f3cb596738ec` |
| cd-remote-runtime.sh | `86c88314db12f9f10423b5e38c44c4682092c358f521ac590b4e12e9539b0d35` |
| release-images.py | `4715a72ad17ca4d78114e2ecd354e9f35f43e9a6e1d355ca4a7bcea24ed95f7d` |
| Compose | `9098cb15c8c4a675beae529664e128d46a2dc50671dee8171d05b659b482bcc6` |
| activation_operator.py | `cf7a6d1107eb6c5c7c58e3db88a9b571bd51b32b8d558ca82e55cbdc3a91fabd` |

## Предыдущее повторное чтение и последняя неточность — закрыта

Полностью прочитана редакция
`adf2d8852185c76ca438d28ac435b0533d86a9b58ae51bd844df8fee65533238`.
Docker endpoint, очистка contexts, socket/root policy, Linux/no rootless/userns,
последняя закрывающая скобка stat, точные карты и повторные ID/image/PID/
StartedAt/RestartCount теперь имеют конкретный алгоритм и закрывают прежний
вопрос2. Матрица GRAF/сторонние закрывает прежнее общее применение GRAF source
к `rec-minio-init`.

Осталась ошибочная фраза пункта4 новой редакции:

> его image Config.User/Entrypoint/Cmd сверяются с container (Compose не задаёт
> ему иной user/entrypoint; command из фиксированного snapshot проверяется
> следующим полным config gate […]).

В действительном snapshot `infra/docker-compose.yml` service `rec-minio-init`
имеет **явный `entrypoint: [/bin/sh, -c, многострочная программа]`**. Поэтому
равенство Entrypoint/Cmd container и defaults стороннего image не является
условием штатной установки и даст постоянный HOLD. Проверка такого равенства
не нужна для принятого узкого binding.

Минимальная замена без новой архитектуры: `Config.User` сверить с собственным
image default, поскольку Compose этому service user не задаёт; фактические
Entrypoint/Cmd включить лишь в тот же private configuration digest и сверку
неизменности. Соответствие entrypoint/command фиксированному snapshot отложить
в уже названный полный config gate; не объявлять policy readiness сейчас.
Если исполнитель хочет проверять их семантику уже здесь, expected должен
происходить из явного snapshot Compose override, а не из image default.
Для данной стадии достаточно первого, меньшего варианта.

Контрольные суммы четырёх списков повторно совпали; ранее перечитанные117
вопросов остаются117 отмечено/0 открыто, отметки не менялись. На этой предыдущей
редакции оставалось только описанное сравнение; его исправление проверено ниже.

## Финальное precode/scoped analyze решение

Полностью перечитана последняя редакция
`8844144bffc54735a78a2413fe2fb384b2123b64af9415e4cdc40c4eba016df3`.
`rec-minio-init` теперь сравнивает с собственным image default только User,
а реальные Entrypoint/Cmd входят в private digest/сверку неизменности;
явное переопределение entrypoint в Compose признано. Проверка их соответствия
snapshot остаётся в будущем полном config gate. Последнее замечание закрыто.

Согласованность с прежними spec/plan/quickstart/activation-milestones/operations
повторно проверена по неизменным контрольным суммам; полное чтение требований
переиспользовано по исключению F273. Новых противоречий или обязательных
пропусков в этой ограниченной стадии не найдено. Четыре checklist сохранили
прежние hashes и итог **117 отмечено/0 открыто**, без правок отметок. Это
проектный SCOPED PASS для реализации/проверки runtime binding, а не гарантия
готовности будущего кода, настроек, секретов или рабочей установки.

Будущее кодовое ревью должно сверить точную матрицу классов, selected metadata,
Docker endpoint/identity/PID/maps, стабильность Config/HostConfig/Mounts,
повторный override/source binding, точный child protocol и сохранение
deadline/cancellation/cleanup. Настоящая учебная Linux-проба не подменяет
проверку рабочего root-запуска. До полного preflight итог всегда exit1/
`HOLD/full_preflight_not_implemented`; guard не снимается, T0/ready не создаются.

Изменён только этот отчёт. Ревьюер не менял код/spec/plan/tasks/checklists,
Git/GitHub/production, не запускал тесты, Docker, SSH, SQL или другие операции
с побочными действиями. UID1003 по-прежнему не подтверждён; новых вопросов
владельцу нет. Полный preflight, T0, выпуск, трафик, продажи и T112/T113
остаются вне приёмки.
