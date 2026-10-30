# F273/T113 — независимое повторное ревью политики запуска, 30.10.2026

**Результат: SCOPED PASS. Открытых P1: 0; P2: 0.**

Ревьюер `/root/f273_release_boundary`, существующая полоса
`high-risk-product`, T113/#7804. База Git:
`3e8efb8d571497bdea5ae8a7149a6dacf526a488`.

Принимается только рассмотренный участок политики фактического запуска
в `activation_operator.py` и его проверки на точных байтах, указанных ниже.
Это не приёмка всей T113/T112, установленного оператора, рабочего измерения
или выпуска. Исторический [первый HOLD](t113-policy-code-review-20261030.md)
сохранён без изменения. Ревьюер не запускал тесты, Docker, SSH, SQL, сборки,
GRAF Dev или рабочий сервис; выводы основаны на чтении кода, сценариев,
журналов и проверке контрольных сумм.

## Закрытие трёх замечаний первого ревью

### P2-01 — штатное сгенерированное имя secret: устранено

Политика принимает только `file` и необязательное `name` в верхнеуровневом
описании secret. Если `name` присутствует, оно обязано точно совпадать с
`twobrain-rec_` + logical secret. Чужое имя и дополнительные формы остаются
запрещёнными; отсутствие обязательного `file` даёт конечный HOLD.

Это соответствует прочитанной настоящей нормализованной Compose-модели,
которая содержит оба поля. В тестах есть положительный `secret_generated_name`
и отрицательный `wrong_secret_name`. Прежнее расхождение между настоящим
выходом Compose и синтетической моделью закрыто.

### P2-02 — параметры существующего именованного тома: устранено

`_runtime_preflight` получает имена только фактически подключённых томов
`Type=volume` и выполняет read-only `docker volume inspect` с закрытым набором
полей. Проверяются точное покрытие имён, `Driver=local`, `Scope=local`, пустые
Options и совпадение фактического Source с Mountpoint. Сам запрос подключения
контейнера также остаётся ограниченным: посторонние driver options, subpath
и неподдержанные формы запрещены.

Каталог тома проходит канонизацию, проверку защищённых предков, ACL, запрет
групповой/общей записи и проверку действительного дескриптора каталога.
Штатный владелец данных может отличаться от установщика. Содержимое тома
не читается. Его метаданные и идентичность каталога включены в закрытый digest;
volume inspect и проверка файловой системы повторяются в финальной сверке.

Таким образом, заранее созданный local volume с
`type=none,o=bind,device=...` больше не получает допуск только за правильное имя.
Прочитаны отрицательные случаи driver/scope/options/Mountpoint/отсутствия
metadata/symlink/name/type/subpath, положительный полный preflight
`volume_good`, отказ `volume_options` до Settings и `volume_changed`
на повторной сверке. Реальная inspect-проба использует настоящий собственный
именованный Linux-том.

### P2-03 — автоудаление контейнера после остановки: устранено

У всех проверяемых контейнеров `HostConfig.AutoRemove` обязан быть строго
`False` до Settings и мутаций. `RestartPolicy` сверяется с закреплённой
декларацией restart либо значением `no`; допустимы только ожидаемые поля,
а счётчик повторов разрешён лишь для `on-failure`.

Отрицательные проверки AutoRemove/restart/retry подтверждают отказ. Отдельный
RED-журнал старой версии содержит два причинных `DID NOT RAISE`: AutoRemove
и restart retry. Новый механизм остановки или перезапуска не добавлен.
Прежний риск удаления writer после stop при необходимости возврата прежних
ID закрыт предварительным отказом.

## Остальные рассмотренные границы

Прочитаны полный diff двух кодовых файлов, затронутые реализации и вызовы,
принятый precode, сценарий Linux-матрицы и окончательная настоящая
inspect-проба. Повторно рассмотрены следующие свойства:

- Модель берётся штатным Compose только из закреплённого снимка с
  `--env-file /dev/null --no-interpolate --no-env-resolution
  --no-path-resolution`; выход ограничен 2 МиБ. Имя проекта и набор служб
  закрыты, фактические ID должны точно покрывать допустимые службы.
- Списки argv не разбиваются повторно. Строковая форма разбирается один раз;
  одиночный `$` отвергается до однократного преобразования `$$`.
  Наследование пустых Entrypoint/Cmd сверяется с Docker Engine merge,
  включая очистку image Cmd явным непустым Entrypoint. User, WorkingDir
  и исполняющие переменные окружения сверяются с source/image defaults.
- Права, caps, security options, namespaces, устройства, read-only/init/groups,
  точные Memory/NanoCpus/Pids, закрытые loopback-порты, logging и healthcheck
  проверяются до Settings. Подключения tmpfs сверяются с HostConfig;
  отсутствие отдельного tmpfs в фактическом Mounts допускает форму Engine,
  но пересечение destination с volume/secret отвергается явно.
- Mount list имеет закрытые типы и destination. Bind допускает только
  rprivate и штатный CreateMountpoint bool; посторонние propagation/options
  не получили исключения ради прохождения проверки.
- Один logical secret связан с одним canonical Source и полной идентичностью
  у всех потребителей. Статический источник связан с исходной декларацией,
  динамический — только с предусмотренным целым `${NAME:-DEFAULT}`.
  Проверяются предки, ACL, права, обычный файл и единственная ссылка;
  содержимое ненастроенных secret не читается.
- Политика выполняется до Settings и продуктовых мутаций. Финальная сверка
  заново получает source model и volume metadata, повторяет файловые проверки
  и требует прежний digest. Существующие проверки runtime/inventory/source/
  release/socket/PID/Settings сохранены. Дескрипторы закрываются в `finally`,
  ошибки дают конечный ActivationHold, внешний ответ сохраняет четыре поля.

Новых P1/P2, существенных противоречий принятым требованиям или ослабления
конституции в этом участке не обнаружено. Доверенные daemon/toolchain,
закреплённые source/image и отсутствие произвольной параллельной root-подмены
остаются принятыми допущениями. Проверка не обещает идентичность произвольных
дочерних процессов контейнера.

Полная идентичность каталога включает его метаданные. Обычная запись в корень
тома между двумя проверками может консервативно привести к HOLD. Это свойство
доступности допуска, а не подтверждённый обход защиты; сама эта policy продукт
не останавливает.

## Принятые доказательства и их пределы

1. Окончательный профиль operator/bootstrap/fence/provider config/config
   validation: **433 passed, 6 skipped, 2 warnings**. Предупреждения прежние:
   ранее импортированная pytest fixture и deprecation Starlette/httpx.
   Это прочитанный журнал исполнителя, а не повторный запуск ревьюером.
2. Окончательная Linux-матрица: **69 passed**, exit code 0, пустой stderr;
   JSON связан с точными текущими хешами operator и tracked tests.
   Прочитанный сценарий извлекает четыре точных тела проверок из tracked tests,
   использует собственный временный том и кандидатный source. На Linux
   ancestry/ACL не подменяются. Модель и Engine metadata в этой матрице —
   синтетические dictionaries; установленный неизменяемый оператор и полный
   рабочий runtime она не проверяет.
3. Окончательная inspect-проба получает настоящие Config/HostConfig/Mounts
   двух собственных контейнеров Compose и volume metadata. Она приняла
   положительную конфигурацию и отвергла четыре подмены argv/health/tmpfs/volume.
   Использованы точные multiline entrypoint из `rec-minio-init` и
   `rec-temporal`, но скрипты и эти два контейнера не запускались.
4. Контроль `volume_replacement` в JSON означает изменение digest после
   создания файла в собственном корне тома. Это доказательство обнаружения
   изменения метаданных каталога; оно не выдаётся за физическую замену inode.
5. В окончательной настоящей inspect-пробе нет bind и secrets: общая файловая
   система Mac дала `EOPNOTSUPP` при listxattr. Отказ ACL сохранён. Промежуточный
   rslave также не принят вместо rprivate. Registry/права/ACL проверены отдельно
   на настоящем Linux; сквозной реальной Compose-пробы всего набора secret/bind
   эта стадия не доказывает.
6. Compose-isolation JSON сообщает одинаковую source model при намеренно
   посторонних host environment, `.env` и `env_file`. Ревьюер прочитал артефакт,
   самостоятельно этот эксперимент не выполнял.
7. RED volume-журнал содержит 17 отказов из-за отсутствия аргумента `volumes`
   у прежней сигнатуры. Это RED нового контракта, **не** 17 причинных доказательств
   прежних обходов. Вывод о закрытии P2-02 основан на коде и финальных проверках.
   AutoRemove RED, напротив, содержит два причинных `DID NOT RAISE` старого кода.

Артефакты сообщают `production_touched=false`, удаление собственных ресурсов
и временных зависимостей. Ревьюер проверил сценарии очистки и их отчёт,
но отдельную текущую инвентаризацию Docker не выполнял. Существующий образ
использован без build/pull. Новые зависимости или инфраструктурный механизм
не добавлены.

## Requirements и scoped analyze

Все 117 вопросов качества перечитаны; отметки не изменены:

| Checklist | Отмечено | Не отмечено |
| --- | ---: | ---: |
| requirements | 16 | 0 |
| privacy-measurement | 45 | 0 |
| security | 27 | 0 |
| infra | 29 | 0 |
| **Всего** | **117** | **0** |

Это качество требований, а не число выполненных продуктовых проверок.
Контрольные суммы checklist сохранены. По разрешённому владельцем исключению
F273 использованы ранее полностью прочитанные базовые документы с повторной
проверкой их хешей и полное чтение затронутых требований/зависимостей.
Конституция, PRD, current-product-status, product-gates, spec, plan, quickstart
и затронутые contracts остались на принятой основе. Последнее изменение
tasks.md прочитано отдельно: добавлен отчёт этого участка, полная задача
не закрыта. Прочитаны соответствующие примечания плана роста и changelog.

Scoped analyze этого участка: **PASS**, открытых critical/high и P1/P2 нет.
Общий bootstrap остаётся `HOLD/full_preflight_not_implemented`,
`activation_recovery_unverified` сохранён. Не принимаются полные DB/schema/
roles/legal/register/lifecycle/local-retention/access/guard/capacity preflight,
верхние initial/backup/verify/actual restore/resume, shell/CD/rollback/daily,
T112, T113/#7804, AC01–AC06, T0/ready, IP/аналитика, выпуск, трафик или продажи.
UID1003 этим ревью также не подтверждён.

## SHA-256 снимка повторного ревью

Короткие пути checklist относятся к `specs/273-paid-traffic-analytics/`.
`.dev/growth/` — локальные ignored доказательства, а не новые tracked файлы.

```text
apps/server/src/twobrain_rec_server/product_analytics/activation_operator.py
93ed892c7f92c537222d37f1b47d4054b37361e0809913daef8d578492427245
apps/server/tests/unit/test_activation_operator.py
968afb642fd910774653c36276ebf8c91f5b727608d6e83ae5c1bb3c4efd60d9
.dev/growth/t113-policy-precode-20261030.md
7fd99cf8c4b73d137cab023038d90d83c16da5449cc1d851164519b9fe5b79ec
.dev/growth/t113-policy-compose-20261030.json
94d4818314a12c048839a809462bdd261e685ece26ec44a903e2ab896a2fd9e1
.dev/growth/t113-policy-profile-20261030.log
2b6d89533b837ce3df707e1ffcb814a13c8e3457bb1de59bedb5ebff4587906a
.dev/growth/t113-policy-native-20261030.py
1eefe4e1172959742a1de42033939b501806391ef7c4a9c54e8bbf0fb5eec7e2
.dev/growth/t113-policy-native-20261030.json
78b91afbd5aa5e8aab1f413eda22be4018f494b78f046812bd6d11a785eedf81
.dev/growth/t113-policy-inspect-probe-20261030.py
17b9eb2a52a57f897fc8c6e8fa165f58dff8aefb0437b10b3a2d7625f803bac9
.dev/growth/t113-policy-inspect-probe-20261030.json
3059e51428f72f80445cf06cac6de0c007cb56d5f5809ee8334cb30c35b63f1c
.dev/growth/t113-policy-compose-isolation-20261030.json
5db419f60248943ac855a037cebbad5bce758fa22b23fb6d2f9f58d6a3b7edb7
.dev/growth/t113-policy-volume-red-20261030.log
a9d88e3860b28e8ff97382c3644f827ff6f4578bda9059ad05d51f707a330143
.dev/growth/t113-policy-autoremove-red-20261030.log
10ec6b9be5f06bd10534336c56be97f47326b47e3a93f0d4ef207e1d7ff95c0c
validation/t113-policy-code-review-20261030.md
fdeef9876c87118c6a4e56a8cb4971ef5118f344aa975d70159147b5d1ed1c81
validation/t113-policy-design-review-20261030.md
f3c11d9d32e0e313fedcadef7d44ed1af521b18b2ae8d91869ebb94df2ab9bfc
validation/t113-runtime-policy-20261030.md
f46280733296527c12e84a1cc50248a2fe303dd90b3783e4b61b9a809d51f7f4
tasks.md
fb66324afbb1dce6b1e545ebf7666354e29a8acf05ca4711e8e02715d3812d01
checklists/requirements.md
6755318d0b7a76a9f6439446ad42362272d43859cc6f4b3c045b5c36ad1ed9a2
checklists/privacy-measurement.md
8c390000a2da12cf719348d56c08dcb21d886aac98ba1a90ad3d5c41e141cb4f
checklists/security.md
57f082b0b90faf7a3302db0aa1b9aacd29948641e824578ca4f86eee4dee9cb8
checklists/infra.md
998175e297553cedac7f4d7b2829459fcb3f1b650b3b3b6d072e9065437bfa94
```
