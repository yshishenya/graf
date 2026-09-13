# Infra requirements review

Reviewer-owned; результат качества требований, не приёмка реализации.

- [x] CHK009 Ограничены ли изменения только двумя существующими датированными образами MinIO, без изменения production/Postgres/Temporal?
- [x] CHK010 Явно ли запрещено продолжать build при отсутствии образа и неуспешном pull, сохранены ли exact SHA, image ID, архив, подпись и lock?
- [x] CHK011 Определены ли focused pytest, независимый review и exact-SHA CI для переноса исправления?
