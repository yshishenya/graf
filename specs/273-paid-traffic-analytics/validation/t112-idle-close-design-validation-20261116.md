# T112 — проверка проекта раннего закрытия idle поколения

16.11.2026, основа `c420927a7633596ca392799b61e46022ae7234d2`.
Существующая F273/T112, high-risk-product, speckit-implement.
Это законченный отрицательный результат реализации проекта, не GREEN.

## Независимый исходный разбор принят

Проверяющий дополнил [preflight](t112-pool-return-preflight-20261116.md),
SHA-256 `b3d65ee4365f506fd66da3ad0a35aae0e20eba3abcee3657606273acd83afd96`.
Весь addendum прочитан до зависимого кода. Baseline1PASS/1FAIL независимо
принят как P1-R1; поздние fault cleanup/F-P/ledger/reuse не приняты.
Отдельный runtime DESIGN разрешал public Pool.close до native graceful close
только для уже выбранного пулом точного idle поколения без lease/init/root
keys, при единственном текущем exact Session root/task/Context. Recycle-specific
reservation через это событие не доказан и оставлен HOLD.

Применимые оригинальные разделы восстановлены в том же диалоге;18 прежних
хешей совпали, основные checklist124/0, scoped analyze без новых требований
сохранён. Карта чтения `/private/tmp/graf-t112-idle-close-reading-20261116.json`
не является новым полным чтением исторического корпуса. Before/after implement
hooks выключены. Issue7698/T112/T113 не закрывались и не дублировались.

## Пробная реализация и её предел

Добавлялся отдельный31-строчный Pool.close callback, буквально следовавший
проекту, включая `transaction.is_active=True`.30 узких unit-случаев проверяли
public event dispatch, identities/root/Context/no-TX/no-leases и no-op для
противоречий. До кода:3FAIL/27PASS/198deselected,0.35s; после:30PASS/
198deselected,0.07s. В обоих запусках один прежний fixture warning.
Ожидания native normal/fault адаптировались к предупреждению ожидания;
EOF target вооружался до POST, оба ответа должны были accepted.
Ruff прошёл. Эти unit использовали моделированный root и не доказали его
действительное состояние при получении соединения.

Одна native-попытка не закончила ни одного случая: после2.83s подготовки
normal завис до ручной остановки своего pytest PID28444 сигналом SIGINT.
Живой PTY60422 подтверждён перед остановкой; затем terminalEXIT2,
pytest90.92s/runner94s, `isolated_container_removed`. Это не прошедший набор,
не причинный RED первоначального guard и не новый fault baseline.
Точное место зависания из имеющегося журнала не установлено; Python указал
asyncio/runners.py:123 после прерывания. Предположение об assertion до фиксации
target и его повторе при dispose остаётся непроверенной гипотезой. Нового
запуска без исправленного проекта/наблюдения не было.

## Конкретное противоречие проекта

Дочитаны установленные SQLAlchemy `orm/session.py:1012–1035,1151–1207,
1235–1268,4838–4884`. `SessionTransaction._connection_for_bind()` переводит
root в `PROVISIONING_CONNECTION` **до** bind.connect(), а восстанавливает ACTIVE
в finally. Public `transaction.is_active` проверяет именно ACTIVE.
Public `Session.is_active` при существующем root делегирует ту же проверку.
Поэтому оба свойства False в нужной фазе; простая замена одного другим не
исправляет проект. Private состояние в runtime использовать запрещено.

Отдельная законченная проверка настоящего SQLAlchemy Session с in-memory
SQLite и public `Engine.do_connect` подтвердила эту фазу без подмены методов:

| Публичное наблюдение внутри do_connect | Результат |
| --- | --- |
| root существует, parent=None, root.session — exact Session | True |
| Session.in_transaction(), get_transaction() — текущий root | True |
| root.is_active, Session.is_active | False, False |
| get_nested_transaction() отсутствует | True |
| После SELECT1 root.is_active и Session.is_active | True, True |

SELECT1 и rollback закончены, engine.dispose выполнен, SQLite только в памяти.
Вывод `real_public_provisioning_probe=PASS; sqlite_memory_closed`, terminalEXIT0.
Это подтверждение расхождения public-предиката проекта, не native GREEN,
не доказательство точной причины зависания попытки и не допуск удалить
защитный предикат. Потребуется отдельно определить публичное основание,
отличающее допустимый текущий root от чужого/законченного/ошибочного состояния.

## Сохранение и возврат только своих пробных изменений

Полный diff трёх собственных файлов guard/unit/contract сохранён вне Git:
`/private/tmp/graf-t112-idle-close-draft-20261116.patch`. После проверки
`git apply --reverse --check` отменён ровно этот diff; чужие изменения и
reviewer addendum сохранены. Три файла вновь побайтово совпадают с исходной
основой. Непригодный runtime callback в текущем дереве отсутствует.
Исходный baseline test/log/SHA сохранены. Общий233 не повторялся, новый общий
профиль не запускался. Это docs-only checkpoint отрицательного опыта.

| Материал | SHA-256 |
| --- | --- |
| Сохранённый пробный patch | `16d1f5ad2ab0854e5654fd0342cee9d6837efc8e0fcf819b37014f12d45913bd` |
| Unit RED log | `bcf9f6dd3223ef6bfeedf7f9e8d414bf0bfce9d045801786019c581ff368faaa` |
| Unit GREEN log моделированного решения | `78fdfb1f7bacfa245e07608b45fc06824575a28ad5fbe6d3507a4a6836929720` |
| Незаконченный native log после остановки | `6f8dd6786d0530e7557a42228323ff3570b2af209809946bc8f124cd508f5627` |
| SQLAlchemy orm/session.py | `b75a4e427f453c2eaf19f04d87f66c2da644698a14f3b11880f56a73e2a0760d` |
| Возвращённый guard | `eda3d18801b09b742ac3c21ac7bae6f68665dee7252f7074e100baa06e94ef14` |
| Возвращённый unit | `7dbb443ab4f8ea2dc9211b98b742b5f7db778c4c6823f2285b52a3f3aa26aa57` |
| Возвращённый contract | `7b0c4bb447cc66aa828be731c1c61c64fde0e1b8fcecd9987d49f553a4139269` |

Журналы: `/private/tmp/graf-t112-idle-close-{unit-red,unit-green,native}-20261116.log`.
Перед стендом147719684KiB свободно, выше80ГБ. Архивы и зависимости не копировались.

## Следующий допуск

Подготовлено понятное новое поручение
`/private/tmp/graf-t112-idle-close-design-correction-20261116.txt`.
Отправка этого уточнения существующему reviewer и новое заключение ещё
не подтверждены; это не verified wait. Ошибочные wait с cell_id=none не
являлись отправкой или проверкой среды. Их не повторять.

Нужен независимо исправленный public runtime DESIGN после этого конкретного
факта. До него новый callback не писать и30 unit GREEN не использовать как
доказательство применимости к настоящему root. Затем адресное native
наблюдение должно сохранить диагностику даже при раннем callback assertion
и гарантировать законченный собственный teardown. C1/I1/DB-first/private API/
no-retry ограничения сохраняются. T112/T113, restore/runtime/измерение/T0,
PR/CI/merge/выпуск и трафик/регистрации/продажи открыты. Рабочий сервер, почта,
контент и вёрстка не менялись.
