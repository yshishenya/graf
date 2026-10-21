# F290: модель доказательств

Новых таблиц/API нет. Используются существующие модели и безопасные документы.

- Action selection: repository, release, full40hex commit, runtime=node24,
  affected workflows, compatibility source. blob SHA недопустим вместо commit.
- Stash disposition: immutable OID, base/index/untracked coverage, безопасные
  области, решение для каждой части, владелец, принятый PR/основание отказа.
  Состояния: unknown → inventoried → decision-reviewed → transferred/retained;
  deleted только после отдельного разрешения. Нет автоматического удаления.
- Post-deploy result: scenario из automatic_retry/backfill_inventory/
  range_playback/normalization_cleanup, full40hex source, условия/время,
  фактический статус pass/fail/not-run, причина и владелец остатка.
  not-run не превращается в pass. Модель deployment.py использует cleanup_result
  для normalization_cleanup. ready требует четырёх настоящих pass.
- PR proof: существующие source/base/run/attempt и ZIP authoritative/envelope
  receipts, без изменения схемы. Локальный PASS не hosted proof.

Все поля без meeting content, signed URL, secret paths или сырого stash diff.
