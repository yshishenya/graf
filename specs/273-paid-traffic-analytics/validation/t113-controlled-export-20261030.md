# T113: контролируемое окно экспорта PostgreSQL

30.10.2026; F273/T113/#7804; `high-risk-product`.
Основа `a241f34b8832b3b0ed83409f25d55853e7cb3e56`, локальные изменения поверх неё.
Следующая внутренняя стадия [принятого полного оператора](t113-full-operator-design-20261030.md),
не готовый рабочий оператор и не включение аналитики.

## Сделано и проверено

- [x] `_controlled_export` сверяет source/owner identity, cluster/name/OID,
  закрытый gate, maintenance-роль, свой PostgreSQL EX `(273,3)` и отсутствие
  всех чужих PID/prepared до изменения. До начала проверяется прежний limit.
- [x] До временного `ALLOW_CONNECTIONS=true` устанавливается и повторно
  читается `CONNECTION LIMIT 0`. Обычные app/media/maintenance подключения
  отвергнуты; доверенный owner создаёт настоящий native custom-format dump.
- [x] Завершение контекста возвращает и читает `false/limit0`, дожидается
  отсутствия всех чужих PID/prepared, повторяет identity/EX/revoked.
  Прежний limit передаётся внутреннему caller для будущего явного resume;
  автоматического открытия/старта продукта нет.
- [x] Отмена ожидающего task, включая повторную, не освобождает SQL owner до
  разрешения отправленного шага. Неизвестный ответ ALTER не становится успехом;
  после попытки мутации закрытие обязательно. Cleanup имеет предел30с,
  может превысить основной deadline ради владения, но не разрешает успех.
- [x] Новые восемь native случаев сначала дали8FAIL на отсутствующем helper,
  после реализации8PASS. Полный прежний fence/operator/drain/Compose профиль:
  **80PASS,2 предупреждения,29,26с**. Свой PG17-контейнер и Compose-ресурсы удалены.
- [x] Ruff шести затронутых Python-файлов и `git diff --check`: PASS.
- [x] [Независимое ревью кода](t113-controlled-export-code-review-20261030.md):
  SCOPED PASS тех же source/test SHA256, блокирующих находок нет.
  Полный верхний оператор этим заключением не принимается.

Режимы native проверки: success, body_error, cancel_open, cancel_close,
unknown_open, missing_ex, late_pid, expired. До мутации missing_ex/late_pid/expired
сохраняют прежний limit7. После попытки мутации возвращается false/limit0;
подтверждённый session EX и revoked сохраняются. Native dump создаётся только
в своём временном контейнере; никакого рабочего содержимого или ключей нет.
Два предупреждения — существующие pytest fixture import и Starlette/httpx.

## Границы и остаток

Верхний caller ещё обязан подтвердить остановку writers, владение deployment/
filesystem EX и соединениями, завершить и reap все свои CLI до выхода из
контекста. Внутренний helper не принимает подменяемый callback/SQL/pass-file и
не имеет CLI или production-вызовов. Это не доказательство полного
`backup-rec-stack.sh` под lifecycle/отменой, полноты DB+objects, rehearsal/replay,
actual restore, безопасного product resume или ежедневной проверки.

Остаются в существующей T113: верхний оператор initial/backup/verify/restore,
внутренние owned rehearsal-ресурсы до cleanup, точное восстановление/удаления,
свежие backup/retention/access/resource proof, CD/rollback и проверка паузы.
T112 видимого результата и рабочая приёмка сохраняются. Новых задач/закрытий нет.
`activation_recovery_unverified` не снят. Рабочая T0 не установлена; writer/IP/
внешние получатели и расписание не включены; production/GRAF Dev не менялись.
Коммерческие AC01–AC06 основного плана не достигнуты этой технической проверкой.

## Зафиксированные материалы

| Материал | SHA256 |
| --- | --- |
| activation_operator.py | `662f22532e3721688637e5fd2198ac3581336371d16130438ea78c4f59060f16` |
| test_activation_product_drain.py | `986edbbbc7e4901423775b2d3db3ff2c6de91e1cae85c6bb3eb90dcfde795205` |
| RED log | `915fc6b4952392452908ae56202c4d29d456de417c7a7df3c6f96736038bbfc6` |
| GREEN log | `fb2f2b34a687fc63d70df5e2e8466dc812067a7ab1eb1649c43f8aa7eded05b8` |
| Полный профиль | `3c941ae8f1cb0d5ed1865553d5f9280d93e194a55044841305fd414ebc098e3f` |

Журналы лежат в ignored `.dev/growth/t113-controlled-export-{red,green,profile}.log`.
Тесты выполнены на локальных изменённых байтах; exact-SHA GitHub CI/merge/release
этим не подтверждаются. Требования проверены независимым reviewer117/0 и scoped
analyze до кода; повторное чтение основы сверено по хешам по разрешённому F273 исключению.

## Сверка с текущим объёмом задачи

FR-025: marker/initial запрещают второй T0; полный initial verifier ещё отсутствует.
FR-034/035/051: native экспорт проверен как внутренняя стадия, но штатный полный
backup/restore/manifest ещё не подключён. FR-032: автоматического запуска/остановки
продукта этим context нет; обязательный безопасный resume верхнего планового
оператора остаётся неисполненным. Это partial существующей T113, не новый пробел
вне её описания. Новые задачи-дубликаты не добавлены; T113 остаётся `[ ]`.

До сохранения проверено соответствие обоим независимым отчётам и контрольным
суммам source/tests; известных блокирующих дефектов внутри этих двух внутренних
стадий нет. Полная реализация, GitHub checks, merge/release и рабочая приёмка
остаются дальнейшими проверками того же кандидата.
