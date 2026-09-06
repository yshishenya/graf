# Clarifications: CI merge queue и provenance release train

Владелец продукта разрешил автономную проработку без интерактивных вопросов.
Ниже зафиксированы безопасные defaults, которые не расширяют scope.

## C1 — Какой SHA считать release target

`merge_group.head_sha` используется только для проверки synthetic merge queue.
После фактического merge создаётся новый candidate на SHA `master`. Synthetic
SHA никогда не подменяет production release SHA.

## C2 — Что делать при смене SHA во время CI

Старый run получает terminal `cancelled`/`superseded`; его receipt невалиден
для merge и release. Новый target требует новый run и новый receipt.

## C3 — Как часто запускать Full CI

Fast lane остаётся PR feedback; один authoritative Full CI разрешён только для
immutable release candidate. Исправление после stale/failed результата создаёт
новый candidate.

## C4 — Что делать, если GitHub enforcement ещё не включён

Workflow и receipts проверяются в режиме наблюдения, но не объявляются required
checks до появления workflow в `master` и отдельной проверки branch protection.

## C5 — Как получить список PR из merge group

`merge_group` payload может содержать идентификатор группы и SHA, но не полный
список PR. Mapping должен разрешаться через авторизованный GitHub API по
merge-group ID/target SHA. Если API недоступен или mapping неполный, run
завершается fail-closed и receipt не считается успешным.
