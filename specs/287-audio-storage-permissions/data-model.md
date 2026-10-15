# Data model

Новых сущностей/полей/миграций нет. Существующие финансовые записи и их сроки остаются источником истины.

| Таблица | Необходимые SELECT столбцы |
|---|---|
| time_credit_ledger_entries | workspace_id, state, applied_start, applied_end, capacity_snapshot_bytes |
| billing_storage_entitlement_grants | id, workspace_id, starts_at, ends_at, capacity_bytes |
| billing_entitlement_grants | invoice_id, workspace_id, starts_at, ends_at |
| billing_invoices | id, workspace_id, plan_snapshot |

Каждая таблица сохраняет FORCE RLS и фильтр текущего workspace. Роль остаётся без повышенных атрибутов и членства. Никаких финансовых INSERT/UPDATE/DELETE/REFERENCES.

Задачи аудио сохраняют состояния queued/running/publishing/ready и прежние retry/terminal/deletion ветки. Квота по-прежнему резервируется до публикации, проверяется целостность источника и результата. Различаем отсутствие бонусной строки и существующий NULL-снимок.
