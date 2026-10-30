# T113: фактические файлы оснований, доступа и защиты

База0817654a05a84d9d8570ee774cdb7b4559900954, прежние F273/T113/#7804,
полоса high-risk-product. Реализуется существующий полный алгоритм оператора;
рабочий сервер, GRAF Dev, выключатели, получатели, T0/ready не менялись.

## Изменение

Существующее bounded file чтение получило явный RO directory-bind режим.
Default exact-file Settings/owner-secret режим сохранён. Source и proc-root
каталоги удерживаются открытыми; сверяются dev/inode/owner/group/mode, для leaf
также bytes/size/link/time/ACL. На выходе пути открываются заново. Изменение
mtime каталога от записи соседнего файла само по себе не запрещает результат.
Для operational leaf действует прежний предел64KiB.

_runtime_operations получает только actual Env и Settings каждой работающей
службы. Проверенные четыре файла передаются штатным legal/access/guard readers
через запечатанные memfd. В guard reader добавлен optional keyword пути защиты:
None сохраняет default, явный плохой путь не переключается на другой файл.
Проверяются local_only/основание/раскрытие, доступный v2 register и отсутствие
отзыва уровня2, свежесть120с/budget/latch, access reviews/≥2 оператора/MFA/срок.

Expected access digest вычисляется из закреплённого guard script и сверяется
с настоящим root0755 installed script, его FD/bytes/identity/ancestry/ACL.
Actual Env не может подменить этот digest. При выходе readers повторяются со
свежим временем, проверяются bytes/path identity и исходный общий deadline.
Все running writers удерживают эти контексты до конца runtime preflight;
разные корректные копии дают отказ при сравнении operational proofs.
Наружу по-прежнему только4поля, детали включены в aggregate digest.

## Проверки исполнителя

- До кода: [независимый проект](t113-operations-design-review-20261030.md),
  SCOPED PASS, P1/P2=0; все117 вопросов перечитаны, markers117/0 не менялись.
- RED:32 AttributeError отсутствующего _runtime_operations на Linux; прежние
  38 Linux Settings/ACL/memfd проверки прошли. Отдельный guard RED — TypeError
  отсутствующего keyword. Это отсутствие механизма, не32 доказанных обхода.
- Профиль operator/bootstrap/fence/provider/alerting:524 passed,38 skipped,
  два прежних warnings. После форматирования imports/теста повторён затронутый
  unit профиль на окончательных байтах:395 passed,38 skipped,2 warnings.
- Linux extraction окончательных tracked tests:70 passed. Включены32 новых
  positive/negative operational сценария и38 прежних Settings/ACL/memfd случаев.
  Linux FD и sealed bytes настоящие; process identity в этой параметрической
  матрице подменён, поэтому она не выдаётся за полный running-container proof.
- Отдельная native directory-bind проба использует собственный настоящий worker
  с UID/GID100/101 и RO directory bind; root проверяющий runner входит только
  в его PID namespace с SYS_PTRACE. _process_identity, directory/file/ACL/memfd
  функции не подменены. Результаты: normal PASS; file replacement внутри
  контекста HOLD; source directory replacement при старом контейнерном bind
  HOLD; затем normal PASS и неизменное число FD. Settings-флаги в этой пробе
  заданы учебным объектом; полный Settings путь покрывается отдельными тестами.
  Это механизм на собственных ресурсах, не полный Compose/host/installed package
  или рабочая приёмка. Собственные worker/runner/volume удалены, ошибок нет.
- Ruff с прежним исключением E721, whitespace, development-process и Spec Kit
  governance проверены. [Независимое ревью реализации](t113-operations-code-review-20261030.md)
  подтвердило SCOPED PASS: P1/P2=0, три окончательных SHA256 совпали,
  все117 вопросов перечитаны, markers117/0 не менялись. Сверка с T113 не выявила
  новых неучтённых работ; существующий остаток ниже остаётся открытым.
  Полная сходимость фичи и рабочая готовность этим участком не заявляются.

Журналы/сценарии в .dev/growth: t113-operations-red-20261030.json,
t113-operations-guard-red-20261030.log, t113-operations-profile-20261030.log,
t113-operations-unit-final-20261030.log, t113-operations-native-final-20261030.json,
t113-operations-bind-native-20261030.{py,json}. Проверки выполнялись только на
собственных учебных данных. Данных клиентов/встреч в отчёте нет.

## Открытый остаток

Разбор v2 не доказывает исполнение cases/сроков/остатков. Полный retained-source
lifecycle reconciliation, local-retention SQL/schema/trigger/jobs/config,
четыре категории/таблицы, upper initial/backup/verify/restore/resume и CD/rollback/
daily/T112 ещё открыты. Сверка одного installed script не принимает все
установленные jobs/helpers/config. Compose mounts/env legal/access/guard всех
writers ещё предстоит согласовать; отсутствие actual bind сейчас даёт HOLD,
а не host fallback. Access record не подтверждает доверие UID1003 или live
membership. Bootstrap full_preflight_not_implemented и legal
activation_recovery_unverified сохранены. T113/T112/AC01–AC06 не закрываются.
Трафик, новые внешние аккаунты, активации и оплаты этим этапом не подтверждены.

## Контрольные суммы окончательных исходников

```text
33fb35d7975feef88e9ea8617afd4c386673239b340001d14f7f5d0a3f0a06b3  apps/server/src/twobrain_rec_server/product_analytics/activation_operator.py
8fe369afc4d8720c372d94cbaaa84ddbc1d1e8649cfec987c387b80ea4939a77  apps/server/src/twobrain_rec_server/product_analytics/provider_readiness.py
ab3cd09989499d21b16d0d975f197e8152f64c997a355ea1328db98a69dee317  apps/server/tests/unit/test_activation_operator.py
```
