# T113: фактические настройки и файлы работающих служб

30.10.2026. Основа426cde62b308fa9630fe872de72e8c321ade2325.
F273/T113/#7804, high-risk-product; Legacy Impact untouched.

В существующую проверку runtime подключена штатная production Settings из
настоящего Config.Env. Сохраняются её JSON/NoDecode/alias/проверки и подстановка
пароля с правильным URL-кодированием. Переменные оператора и .env не подмешиваются.
Все обязательные и работающие необязательные GRAF writers проверяются; остановленные
не запускаются. Формат внешнего результата не меняется, добавляется private digest.

Для каждого настроенного файла проверяются exact read-only bind, закрытые права,
доступ UID100 с реальными группами и проход по destination каталогам. Source и
фактический destination через /proc/PID/root должны совпасть по inode/байтам.
Обычные validators читают неизменяемый RAM-снимок тех же байтов. Все FD и Settings
живут до повторной runtime/source/process проверки и закрываются до выхода.
Пустой публичный placeholder разрешён только для штатного точного пути и закрытой
таблицы выключенных возможностей. Неизвестный/изменившийся вход даёт конечный HOLD.
Секреты, реальные пути и полный Settings в вывод не попадают.

## Проверки

- [x] Исходный HEAD:29 новых случаев завершились ожидаемым отказом из-за отсутствия
  Settings bridge;1 Linux-only пропущен. Журнал t113-settings-red-20261030.log.
- [x] Общий локальный профиль operator/bootstrap/fence/provider-config/config-validation:
  357PASS,6SKIP,2 прежних предупреждения;5,71с. Профиль проверяет production validators,
  обычные настройки, файловый допуск и отмену подготовительного запуска.
- [x] На Linux выполнены4 точных тела отслеживаемых тестов, извлечённые AST:
  38PASS/0SKIP. Настоящие sealed memfd, запрет записи/truncate и закрытие FD
  после успеха/ошибок; собственные временные зависимости удалены.
- [x] Отдельный настоящий Linux Docker file bind: неизменный комплект PASS;
  host rename сохраняет прежние байты подключённого файла; Settings bridge HOLD.
  Собственные контейнеры и выделенный учебный том удалены. Процессная identity
  в этом механическом тесте подставная: он не доказывает полный runtime gate.
- [x] Ruff, Spec Kit governance, development-process, fragments и whitespace.
- [x] [Повторное независимое ревью](t113-settings-code-rereview-20261030.md)
  приняло финальный код: P1=0/P2=0, оба прежних P2 устранены; суммы совпали.

Первое [независимое code review](t113-settings-code-review-20261030.md) нашло
два P2: расширенные ACL и неподтверждённый источник пароля PostgreSQL. Теперь
ACL проверяются на удерживаемых FD файлов и каталогов, включая повторную сверку.
Исходный password-компонент обоих настроенных адресов БД обязан содержать ровно
`__POSTGRES_PASSWORD__`; штатная Settings подставляет проверенные байты.
Четыре отрицательных URL-случая воспроизвели отказ прежней реализации
(4FAILED, t113-settings-review-red-20261030.log). Linux-профиль отдельно
проверил настоящие ACL: запрет UID100, чтение посторонним UID1003 и запись
в каталог. Первый ACL-запуск на tmpfs получил EOPNOTSUPP; окончательный
запуск на отдельном Linux-томе дал38PASS. Том удалён; EOPNOTSUPP не засчитан
как доказательство исправления.

Первый опыт с каталогом Mac через Docker Desktop после rename получил ENOENT,
поэтому не был выдан за Linux retained-inode proof. Окончательная проба использовала
свой настоящий Linux-том и отдельно подключённые файлы. Native тесты используют
текущий пакет исходников с готовыми зависимостями образа; это механизм, а не
неизменяемая установка всего будущего кандидата.

[Независимое precode/scoped analyze](t113-settings-design-review-20261030.md)
закрыло3 замечания: фактический bind, байты валидаторов и disabled placeholder.
117 требований отмечено/0 открыто; исполнитель отметки не менял.

## Контрольные суммы

- `.dev/growth/t113-settings-native-20261030.py`: `01a3000750fbc88020224073877fb3dcd6fc9a8292f42014aed0dd03054a75fb`.
- `.dev/growth/t113-settings-review-red-20261030.log`: `c46d7ce17a07b6fc3bf3d0c6d6646860a849d8a7cc145f3b2704dac1fe6b71f3`.
- `apps/server/src/twobrain_rec_server/product_analytics/activation_operator.py`: `5b0c8b0dcc14f1165880c81af92a4a2c6485641a6f5745f730af8e37e6a2bf5c`.
- `apps/server/tests/unit/test_activation_operator.py`: `1aff262898d13828532b35581e01bd50abf43241c2272d593db8b02db2a57426`.
- `.dev/growth/t113-settings-profile-20261030.log`: `455d7671a8cb02e93999ff59eea5b1c1a8c160157cc9b627eb3c7034f8c8d638`.
- `.dev/growth/t113-settings-native-20261030.json`: `1dbaff80cf750bd9c2c4464038e3f3d53beb7480d7543c48b95ddc721eb4adad`.
- `.dev/growth/t113-settings-bind-probe-20261030.py`: `c0e83b892ad03b65c9d997b7c06fb4d3b8be673f3ecbe6ec72c78ed697a04c4f`.
- `.dev/growth/t113-settings-bind-probe-20261030.json`: `eeb0d76afe30913b51ee17823db3c27accb4ea4cba3d631c1cb67f1601afce8e`.

## Остаток и границы

Это часть открытой T113; отдельный PR/Full/CD/выпуск не выполнялись.
Полный Compose policy/DB/schema/roles/retention/resource/access/capacity preflight,
initial/verify/actual restore/resume, shell/CD и T112 остаются обязательными.
Формальный итог запуска всё ещё HOLD/full_preflight_not_implemented;
activation_recovery_unverified сохранён. Рабочие T0/ready не создавались,
IP/аналитика/получатели не включались. Не подтверждённая серверная группа
также запрещает рабочий root-запуск; права сервера не менялись.
Никаких новых запросов владельцу о группе для этой проверки не требуется.

Сверка с принятым полным алгоритмом: нет новых требований, задач, получателей,
таблиц или зависимостей; оставшиеся операции уже в T113/T112. Полное convergence
всей фичи этим не объявляется. G015/G017, AC01–AC06 и3 оплаты от3 новых внешних
клиентов до19.01.2027 остаются открытыми; учебные результаты не считаются трафиком
или продажами.
