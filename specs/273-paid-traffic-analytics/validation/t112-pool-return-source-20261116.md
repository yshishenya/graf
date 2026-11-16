# T112 — исходные пути обычного закрытия и возврата в пул

16.11.2026. Основной агент, checkpoint
`b573c49e050bff010f95ce91a1fed674103f99aa`.
Полоса текущего исследования: read-only investigation, существующая
high-risk-product F273/T112. Это сверка исходников до проекта опыта,
не независимый допуск новых тестов или исправления и не приёмка T112.

## Что меняет следующий опыт

Прочитаны реальные вызывающие пути авторизации/продления, guard и
установленные SQLAlchemy2.0.51/asyncpg0.31.0. Ordinary close нельзя подменять
уже принятым hard invalidate(None): это разные операции и доказательства.

| Путь | Фактическое действие и нужное различие |
| --- | --- |
| `AsyncConnection.close()` | Через greenlet вызывает обычный `Connection.close()`, а не invalidate. |
| `Connection.close()` с transaction | Закрывает transaction с rollback, затем возвращает connection с `transaction_reset=True`; дополнительный rollback-on-return не нужен. |
| `Connection.close()` без transaction | Вызывает checkin через `_ConnectionFairy.close()`; обычный reset-on-return проходит отдельно. |
| `AsyncConnection.__aexit__` | Создаёт отдельную close-task и ждёт её через shield. Завершение тела context не доказывает окончание этой задачи. |
| Default rollback-on-return | `_ConnectionFairy._reset()` пропускает повторный rollback при `transaction_was_reset`; иначе вызывает dialect rollback. Asyncpg adapter ждёт rollback только при своём `_started=True`. |
| Checkout recycle | `get_connection()` может закрыть старый driver до нового connect/checkout. Возраст, pool invalidation и local soft invalidation — отдельные причины, не обычный checkin. |

Исправный checked-in idle driver и его открытый pooled socket не являются
утечкой запроса. Для успешного обычного возврата нужны законченные request/close
задачи, очищенные owner/transaction ссылки, отсутствие открытой транзакции и
locks и доступность slot. Нельзя требовать уничтожения каждого исправного
соединения или пустоты всех relay-задач постоянного пула ради PASS. Для
прерванного/уничтоженного поколения освобождение сокета доказывается отдельно,
до fault teardown, в исходном двухсекундном бюджете.

## Связь с продуктовым кодом

`db/session.py:create_engine()` задаёт только `pool_pre_ping=True`.
`pool_recycle` и `pool_reset_on_return` приложением не задаются. В установленном
Pool default recycle=-1, reset_on_return='rollback'. Это не доказательство
отсутствия иных recycle-причин: pool/local invalidation в библиотеке остаются.
Искусственно включённый таймер recycle нельзя выдавать за текущую конфигурацию.

Штатная авторизация использует AsyncSession context и commit перед возвратом
успешного principal. Продление также использует AsyncSession context с commit;
ошибки SQLAlchemy оставляют уже завершённую продуктовую операцию в прежнем
состоянии. Будущий result admission использует общую account transaction,
но ещё не подключён HTTP и не разрешает рабочее измерение. Отдельный raw-driver
rollback вне обычной SQLAlchemy transaction нельзя добавлять как будто это
уже существующий продуктовый caller.

До следующего кода нужно независимое заключение: какие distinct ordinary-close/
reset/recycle случаи ещё необходимы сверх принятого Session.close rollback,
startup/I1/pre-ping/C1 и какого наблюдения достаточно в каждом. Затем причинный
baseline с настоящим native driver, без подмены методов или новых runtime hooks.
Настоящий неизменённый полный233 уже закончен; повторять его без правки/находки
не нужно. Будущий неизвестный commit не допускает автоматического retry.

## Источники и границы

18 исходных хешей требований совпали с прежней квитанцией чтения; применимые
целые оригинальные разделы восстановлены в том же диалоге по разрешённому
владельцем порядку F273. Это не новое полное чтение исторического корпуса.
Прочитаны result-visibility целиком, T112/113 spec/plan/tasks/quickstart и
связанные data-model/research/activation-milestones, конституционные принципы и
guidance. Live issue7698 OPEN с явными T112/T113, дубль не создавался.

| Исходник | SHA-256 |
| --- | --- |
| `db/session.py` | `a01c5ab2a45888fedc387dc6656defc92512707e3a485c1c5e2c8f83e616a529` |
| `auth/dependencies.py` | `559bcc1c46cdf49cd283d8a199e089fc7047401b669c0ab17ae9b6d98c94d311` |
| `auth/session_renewal.py` | `0fea864d2aeb6028666e9ba8befe5c351871f5fd095328d7bc8e3b36beb81fd1` |
| `product_analytics/ingest.py` | `b718fd0c23c08c1b51cfe2062254c1433b026f4bc68c1f37a2b79b2c5f31095a` |
| SQLAlchemy `engine/base.py` | `53f38e544004d329ac38e243104bf4bbbaf7d0f0cecabd112b1923b78dde5614` |
| SQLAlchemy `pool/base.py` | `5dbe91e32ec424f1e4cfee5db84896b96cfb23c601020e291d0a6644ff50883f` |
| SQLAlchemy `dialects/postgresql/asyncpg.py` | `c5784dd0e262892cbd0ba6cae2daf69b3152037152ada95619a9fb10f6f12bda` |
| SQLAlchemy `ext/asyncio/engine.py` | `d7db66ce683ee95c30982103c7c9f2c27ccff6a53ee630e31d334c3af4e22528` |

Новых тестов, контейнеров, сборок и сетевых fault-опытов не было. Исходники
приложения/библиотек и настройки не менялись. Не приняты ordinary-close/reset/
recycle/TLS и прочие commit исходы, весь T112/T113/restore/runtime/T0,
PR/CI/merge/release, визиты, регистрации или продажи.
