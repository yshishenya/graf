# T112 — черновик одного GET без глобальной трассировки

17.11.2026. Автор `/root`; существующая F273/T112/#7698 и T113/#7804,
полоса `high-risk-product`. Основа `6ecc7335962b0c1728fdab911f6b76c3321b4e80`.
Новый [независимый проект](t112-early-proof-diagnostic-design-20261117.md)
получен FINAL и прочитан целиком; SHA-256
`49fa99b03cd42e4b061605c3c2300a06712c3f03dcbb58693217241a367acbd6`.
Он объясняет ограниченность V4:0proofs на GET1159 предшествовали POST/M1,
а elapsed всего сценария не измеряет длительность проверки proof.

## Подготовленный код

[Пробник](t112-early-proof-probe-20261117.py), SHA-256
`e3c5f0d5dcec7c2f66d86ad9ec189b6689a233f12bdf27884b214316fa5030d8`.
Это отдельный prefix-only case: два native warm connects/SELECTpid/commit/close,
исходный real_app/relay и test-only http_period, затем один GET и очистка.
Нет POST/M1/watchdog/fault, global tracing, driver/Pool/SQL вмешательства.
Точные pins до исполнения закрепляют шесть исходников. Код не находится
в conftest/обычном наборе и автоматически не включается.

Семь редких границ получают прозрачные временные wrappers; они делегируют
исходный вызов и возвращают исходный объект. В records идут только access/
precondition bool, форма и len(dict), actual остатки work/cleanup из аргументов,
тип/модуль исключений и относительные времена. До получения сроков — None.
HTTP response читается только по status_code, без text/body/headers/proof.
32records и dropped/incomplete дополнены отдельной ограниченной terminal
summary семи стадий, которая не вытесняется буфером. Ошибки тела и выхода
asynccontextmanager наблюдаются отдельно с сохранением original suppression.

## Что реально проверено

[Selfcheck](t112-early-proof-selfcheck-20261117.py), SHA-256
`c73fa8b646f0d028e9f64d3b027018e4d8e0dee2203ac5c146b0211e4ddf8608`:
AST извлекает только Observation/shape/error_type/boundary/eligibility/transaction,
без imports приложения/fixture и без HTTP/БД.

**15 synthetic PASS/EXIT0**, network_calls=0/database_calls=0: None/empty/
nonempty с запретом чтения keys/values; один original call, исходные args/self
и identity результата; исходная ошибка/отмена; enter/body/cleanup ошибки,
подавление исходным context manager, один enter/exit; ContextVar reset,
cap32/dropped/incomplete и terminal summary вне буфера; inactive delegation.
Ruff обоих файлов PASS. Это проверка wrappers, не реальных функций или GET.

Реальная subprocess-проверка сохранена через capture_output:
`/private/tmp/graf-t112-early-proof-selfcheck-20261117.log`, SHA-256
`bbc7c7fe07cbe000442520991b5303685e0e6277d88258060a0d81bf5a206561`;
receipt с тем же basename.json. Предварительный идентичный synthetic запуск
также завершился15PASS; реальные HTTP/PG не выполнялись.

## Следующий обязательный gate

Конкретная реализация **ещё не принята независимым статическим ревью**.
Поручение подготовлено в
`/private/tmp/graf-t112-early-proof-implementation-review-request-20261117.txt`;
файл не равен доставке, живому процессу или verified wait. Не объявлять,
что review уже идёт, пока не вызван existing reviewer. Следующий шаг — реально
передать поручение `/root/public_counter_readiness_review` и получить точное
PASS/HOLD по этим hashes. Новых агентов не создавать. До PASS не ставить
временный файл в apps/server и не запускать HTTP/PostgreSQL. Старый V4-допуск
уже использован и не переносится. Новый87 не назначен.

При конкретном будущем допуске — только один GET с cleanup, независимо от
исхода. Его успех не докажет влияние tracing, HTML proof или старую причину;
не запускать POST/V4/87 автоматически. При изменении источников допуск
потребует новой проверки.

Runtime/apps/server/tests/changes не изменены. Настоящий period остаётся
`yield None`; Postal — почта ГРАФ. Контент/вёрстка/production/службы/настройки
и внешние события не менялись. T112/T113/T098/restore/readiness/T0 и
unknown repeated HOLD остаются открытыми. Новый недельный отчёт Метрики
в этом проходе не прочитан; чтение документации CUA не является чтением отчёта
и не устанавливает неисправность кабинета. Трафик/продажи не подтверждены.
