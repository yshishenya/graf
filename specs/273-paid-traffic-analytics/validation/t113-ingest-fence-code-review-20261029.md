# F273/T113: независимое ревью lifetime SH в ingest — 29.10.2026

**SCOPED PASS.** В проверенном diff не найдено блокирующих дефектов или замечаний P1/P2. Файловый SH теперь охватывает одну задачу, владеющую всей DB-сессией, и не освобождается раньше завершения __aexit__ при обычной/повторной отмене родителя. Это локальная приёмка описанного механизма, не разрешение включить рабочую аналитику и не закрытие T113.

## Версия и выполненная проверка

Reviewer `/root/f273_release_boundary`; основа `ca42eeae655d61d8c0a7a0af8950103abfb9da21`, ветка `codex/f273-local-period-20261029`, незакоммиченный diff. Точное поручение `.dev/growth/t113-ingest-fence-code-assignment-20261029.md`, докодовое основание `.dev/growth/t113-ingest-fence-design-review-20261029.md`. Полоса high-risk-product, существующая F273/T113. Просмотрены весь diff ingest/test ingress, два уточняющих абзаца activation-milestones и одна limitation F273; целиком текущий ingest, его три рабочих caller и неизменные SQL/helper/fence границы из предшествующего чтения.

Тесты/сборки/контейнеры/приложения/рабочие подключения reviewer не запускал. Код, spec/plan/tasks, чек-листы, Git/GitHub/runtime и чужие изменения не менялись. Создан только этот отчёт. Применялось уже разрешённое исключение повторного чтения F273; нынешняя проверка не заявляет полного повторного чтения всей исторической документации.

## Причина и исправление

Установленный SQLAlchemy AsyncSession.__aexit__ создаёт отдельную task(self.close()) и ожидает shield. Если caller прекращает ожидание по CancelledError, сама close task может ещё работать. Простой внешний sync with вокруг async with потому не доказывает lifetime файлового замка.

Исправление соответствует принятому узкому проекту:

1. Прежние auth/telemetry/catalog/workspace/operating проверки сохраняются до открытия fence. GRAF_PRODUCT_ACTIVATION_STATE_FILE и OWNER_UID обязательны; UID берётся из операторской среды и преобразуется в int, не выводится из UID контейнера или HTTP. Ошибки значения/отсутствия/open/lock дают admission_blocked до вызова sessionmaker.
2. Вызов activation_fence сохраняет readonly=True по умолчанию и не создаёт файлов. Проверки operator-owned каталога/inode/mount и неблокирующий SH остаются в существующем модуле. ExitStack удерживает lock context на всём пути ожидания и извлечения результата.
3. Вложенная save_decision содержит вызов sessionmaker, весь async with, tenant setup, SQL, COMMIT и выход из сессии; возврат результата находится после __aexit__. Прежние fresh callback и local_only/no-provider ветви сохранены. SQL SH273,3 и identity-lock остаются внутри этой сессии после filesystem SH.
4. Создаётся одна operation task с сильной локальной ссылкой. Каждый await проходит через shield(operation). Первая CancelledError сохраняется; следующая отмена снова перехватывается и не отменяет operation. Цикл не выходит из-за одной лишь отмены, пока task не done.
5. Исключение operation из shield лишь завершает цикл; operation.result() обязательно извлекает результат/исключение. Finally передаёт именно первую сохранённую CancelledError, поэтому поздняя ошибка COMMIT или успех не маскируют отмену. Никакой второй сессии/повторного INSERT/uncancel или раннего unlock по timeout нет.
6. OSError классифицируется как ошибка fence только в узком блоке открытия. OSError/прочие ошибки внутри сессии идут к прежнему database_unavailable. PermissionError сохраняет admission_blocked. В HTTP/журналы не добавлены paths/SQL/secrets/exception text.

Три рабочих caller общего ingest — /events, /posthog-desktop-capture и record_account_connected_milestone — проходят эту общую границу. Legacy validate-only ingest не получил DB или передачи. Сбой измерения продолжает быть изолирован от продуктовой транзакции входа/записи.

## Причинные тесты и ограничения доказательств

Журналы предоставлены родительским агентом, reviewer проверил их контрольные суммы, итоговые строки и код тестов. Собственного запуска не было.

- RED:15 новых случаев упали на прежнем ingest, `15 failed,22deselected,2warnings,4.93s`, учебный контейнер удалён. Восемь lifetime случаев прежде всего ловят отсутствие SH уже до sessionmaker; этот RED сам по себе не выделяет дефект наивной реализации with при cancellation. Этот отдельный механизм установлен по исходнику SQLAlchemy и проверяется наблюдениями новых тестов на текущем коде.
- GREEN: выбранный профиль собрал89проверок, **89passed,2warnings,22.32s**, `postgres_test_result=pass`, `postgres_test_cleanup=isolated_container_removed`. Ruff: **All checks passed!**
- Восемь сценариев phase(commit/close) × fail_commit × cancel_twice используют настоящий flock и PostgreSQL. Фабрика сессии наблюдает уже удержанный SH. До release EX недоступен; после двух отмен родитель ещё не done, close не завершён, EX по-прежнему недоступен. После release проверены закрытие, доступность EX, исходная first cancellation и отдельный durable count(1 при успехе/0 при отказе COMMIT). Таким образом cancellation не выдана за обязательный rollback уже успешного COMMIT.
- Fail_commit + cancellation заставляет operation завершиться исключением; код извлекает его через result() до восстановления исходной отмены. Отдельного глобального счётчика detached exceptions тест не устанавливает; отсутствие этой проблемы здесь подтверждается явным result() и структурой единственного owner task, не заявлением о полном event-loop shutdown.
- Семь отказов до DB покрывают отсутствующие env path/UID, invalid/wrong UID, missing lock, занятый EX и writable mount. Каждый проверяет ноль вызовов sessionmaker. Только тестовый opener на Mac явно подставляет readonly=False; рабочий source такого исключения не содержит. Настоящий owner/inode/flock продолжают проверяться.
- Старые HTTP/server-auth/повторы/local_only/no-provider/реальный unconditional HOLD входят в выбранный профиль. Положительные admission fixtures заменяют operating gate только внутри теста и используют собственный каталог/DB. Без этой подмены рабочий recovery blocker остаётся безусловным.

Контракт корректно называет границу: прямая отмена owner task, остановка всего event loop и SIGKILL этим механизмом не доказаны. Late server-side COMMIT после смерти процесса требует DB EX drain. Проверка read_ready/binding/verifier, полный product drain/actual restore, история и T112 не реализованы этим diff; их отсутствие не представлено как результат PASS. Обычные product/account/category удаления не получили нового admission gate.

Уточнения activation-milestones закрепляют operator UID и повторную отмену уже принятого lifetime. Limitation F273 говорит о подключённой блокировке и отдельно сохраняет непроверенную готовность/закрытый рабочий допуск; рабочая установка и release не заявлены.

## Контрольные суммы

Все7хешей после чтения совпали с manifest; перед записью отчёта совпадение проверено повторно.

| Путь | SHA256 |
| --- | --- |
| `apps/server/src/twobrain_rec_server/product_analytics/ingest.py` | `00e6da6837812595968d9f0030e0691d6bbeb6ca72da5f482db15c850570808d` |
| `apps/server/tests/contract/test_activation_milestone_ingress.py` | `ded6b09f1119e146c7ff9af71f6bb793d00042749ca849ad7a7dbb99acf0a2e4` |
| `.dev/growth/t113-ingest-fence-red-20261029.log` | `87121bf8be24444287a82d0814a5b7f330ccdb5496b89d2a45f72d3b9b9ad830` |
| `.dev/growth/t113-ingest-fence-green-20261029.log` | `c5cf697302b9b0fc5c596f830a869e1a07ffd5931da6a14c0c5d1a5692090975` |
| `.dev/growth/t113-ingest-fence-lint-20261029.log` | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| `specs/273-paid-traffic-analytics/contracts/activation-milestones.md` | `4134ab99f1ef650cc2aaa9d744402b5672b8a3ee3ca1b91a8f45ef8d8192de33` |
| `changes/unreleased/F273.yaml` | `f5a1bd90350291e0afbfc7cd4ce257c69f9c20a81e6b1ae2de703331d0d71c7c` |
| `.dev/growth/t113-ingest-fence-tested-hashes-20261029.json` | `b7e36d7c0fe7011e8021d98b723d8cb37736190a8e8e0f69b20ec72ab64e8364` |

## Повторное чтение checklist

Перечитан текст каждого117действующего вопроса, включая infra026–029/security026–027. Они проверены на изменение/противоречие этому diff; счётчики не заменяли чтение. Новой отметки нет. Требования/зависимости из докодового отчёта сохраняются: consent/категории/получатели не меняются; until_decision/delete/restore/resource guards не снимаются; общий ingress/IP-срез и соседние release gates не пересматриваются. Текущий report не выдаёт соседнюю реализацию за заново принятую.

| Список | Отмечено / не отмечено | SHA256 |
| --- | --- | --- |
| `infra.md` | 29 / 0 | `998175e297553cedac7f4d7b2829459fcb3f1b650b3b3b6d072e9065437bfa94` |
| `privacy-measurement.md` | 45 / 0 | `8c390000a2da12cf719348d56c08dcb21d886aac98ba1a90ad3d5c41e141cb4f` |
| `requirements.md` | 16 / 0 | `6755318d0b7a76a9f6439446ad42362272d43859cc6f4b3c045b5c36ad1ed9a2` |
| `security.md` | 27 / 0 | `57f082b0b90faf7a3302db0aa1b9aacd29948641e824578ca4f86eee4dee9cb8` |

Итог117/0 — PASS качества требований. Чек-листы после составления отчёта перечитаны/сверены без изменений. Остаток полного T113 и коммерческие критерии остаются открытыми. Любое изменение проверенных source/test файлов требует актуализации привязанных доказательств; новый PR/Full/CD/release этим отчётом не подтверждён.
