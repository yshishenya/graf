# T113: независимое ревью внутреннего controlled export

30.10.2026. Проверяющий `/root/f273_release_boundary`, исполнитель `/root`.
F273/T113/#7804, `high-risk-product`, HEAD
`a241f34b8832b3b0ed83409f25d55853e7cb3e56`. Проверка локальных байтов,
без запуска тестов, контейнеров, сервера, GRAF Dev или изменений Git/GitHub.

## Решение

**SCOPED PASS `_controlled_export`, `_settled_sql`, `_quiet_database` и восьми
новых native сценариев. Блокирующих находок в этом внутреннем срезе нет.**
Это механизм контролируемого owner-only окна, не полный backup, verifier,
CLI, readiness writer, resume, actual restore или завершение T113.
Рабочих callers `_controlled_export` вне тестов поиском не найдено.
`activation_recovery_unverified` остаётся в неизменённом legal gate.

Назначение взято из `.dev/growth/t113-controlled-export-review-input.txt`.
Хеши исходника и integration-тестов совпали с указанными в назначении.
Принятый проект сохраняет SHA256
`5d1e069f3fe18f31a21c72c9b0abc41614ff8bfc00c3269f27b1f3cb596738ec`;
прежние precode gates и marker review этим срезом не отменяются.

## Причинная проверка реализации

До изменения gate код проверяет допустимое имя/OID, EX/revoked того же fence,
точные identity reduced source и owner в `postgres`, отсутствие активной
транзакции, исходный false и собственный session EX `(273,3)` при отсутствии
всех чужих PID/prepared. `_quiet_database` проверяет собственный backend и
точный advisory key, а не наличие чужого EX где-либо в кластере; metadata
snapshot очищается перед чтением. Исходный datconnlimit считывается доверенно.

`attempted=True` ставится до первого ALTER: потерянный ответ после исполнения
не позволяет пропустить закрывающий путь. LIMIT0 сначала устанавливается и
подтверждается при false; только затем ставится true и повторяются gate/quiet/
revoked проверки. Yield происходит лишь после них и отдаёт исходный limit,
не соединение с новым privilege и не разрешение resume. Обычный runtime при
нулевом лимите не получает owner-вход. Изначальные source/owner соединения
и остановленные writers остаются обязанностью доверенного верхнего caller.

`_settled_sql` создаёт отдельный task операции и shield-ит его ожидание.
Повторная отмена ожидающего не завершает ожидание до разрешения этого task;
отмена затем передаётся наружу и не считается успехом. Подготовка ограничена
общим deadline, закрывающая операция — отдельными 30 секундами. Дополнительное
время cleanup разрешено, но проверка общего срока после тела и cleanup не
даёт успешного выхода после истечения исходного бюджета.

После любой попытки ALTER `finally` исполняет false, подтверждает OID/false/
limit0, ожидает полной тишины с тем же session EX, повторяет DB identities,
gate и revoked. Без отмены отказ закрытия превращается в конечный код HOLD;
при отмене `_settled_sql` передаёт отмену, не выдавая успех закрытия и не
разрешая верхнему caller считать неизвестный gate подтверждённым. Отказ не
подавляется ради обычного успешного возврата. Исходный limit автоматически
не восстанавливается, продукт не запускается, initial/T0/readiness не пишутся.
Ошибка тела, входа, отмена входа/выхода не обходят этот finally.

Граница владения сохранена явно: **caller обязан reap своих export CLI и
закончить свои DB операции до выхода из тела**. Этот context не принимает
произвольный callback или supplied-pass. Он не доказывает остановку writers
самостоятельно и не подменяет уже принятые stop/drain/верхнего владельца.
Предстоящая интеграция должна удерживать весь этот ресурсный контур.

## Восемь native сценариев и прочитанные результаты

Полностью прочитан новый тест `test_native_controlled_export` с реальным
собственным PostgreSQL17, native pg_dump/pg_restore list и отдельными app/media/
maintenance ролями. Изменения fixture сохраняют UUID-владение собственным
кластером; секреты синтетические, cleanup ограничен своим label/container.

| Сценарий | Проверяемый результат |
|---|---|
| success | Yield исходного limit7; true/limit0; обычные роли отвергнуты, native dump доступен; затем false/limit0/EX/0PID/revoked |
| body_error | Реальная ошибка тела после dump не обходит проверенное закрытие |
| cancel_open | Две отмены после реального COMMIT true не завершают task до разрешения владельца SQL; yield отсутствует, итог false/limit0 |
| cancel_close | Две отмены после реального COMMIT false ждут разрешения закрывающего владельца; отмена не возвращает успех |
| unknown_open | Исполненный true с потерянным ответом всё равно закрывается в finally, наружу HOLD |
| missing_ex | Без своего session EX нет yield и мутации limit; исходный false/7 сохраняется |
| late_pid | Посторонняя исходная сессия запрещает экспорт до изменения limit |
| expired | Истёкший исходный бюджет не разрешает экспорт или новый retry-бюджет |

Прочитанные итоговые строки журналов исполнителя:

- RED до реализации: **8 failed, 9 deselected**, 2 warnings.
- GREEN нового native профиля: **8 passed, 9 deselected**, 2 warnings, 2,44с.
- Общий профиль после реализации: **80 passed, 2 warnings**, 29,26с.

Ревьюер ничего не исполнял. Эти журналы относятся к локальным байтам, не к
CI точного коммита и не к рабочему PostgreSQL. Тестовый `pg_dump` использует
свой snapshot; выполнение полного штатного backup shell со всеми DB/object
артефактами, bytes manifest и lifecycle ещё не проверено этим срезом.
Неизвестное/неуспешное закрытие, полный SQL/CLI lifecycle и верхние failure
paths сохраняются в уже принятом общем алгоритме. Отдельного выпуска нет.

## Контрольные суммы и неизменность границ

| Файл | SHA256 |
|---|---|
| activation_operator.py | `662f22532e3721688637e5fd2198ac3581336371d16130438ea78c4f59060f16` |
| integration/test_activation_product_drain.py | `986edbbbc7e4901423775b2d3db3ff2c6de91e1cae85c6bb3eb90dcfde795205` |
| activation_fence.py | `142fcacf6f5a43c9fc2358b197245e7ef312ed57b0c3dd4dd2ad1f6da17e902b` |
| legal_basis_gate.py | `578de74b6a8362de6c73de9e2bca79e7fd60774324966dae2086d2b6daf7644e` |
| t113-controlled-export-red.log | `915fc6b4952392452908ae56202c4d29d456de417c7a7df3c6f96736038bbfc6` |
| t113-controlled-export-green.log | `fb2f2b34a687fc63d70df5e2e8466dc812067a7ab1eb1649c43f8aa7eded05b8` |
| t113-controlled-export-profile.log | `3c941ae8f1cb0d5ed1865553d5f9280d93e194a55044841305fd414ebc098e3f` |

Предварительные **117 checked / 0 unchecked** и scoped analyze уже приняты
предыдущим marker review; в этом назначении их повторный полный обзор не
заявляется. Checklist менять запрещено и они не менялись. Единственный T0,
текущие удаления и запрет нового периода после потери initial сохранены.
Рабочая готовность, T112/T113 и коммерческие критерии остаются открытыми.

Ревьюер создал только этот отчёт; исходники, тесты, checklist, spec/plan/tasks,
Git/GitHub/runtime не менял. Чужие локальные изменения сохранены.
