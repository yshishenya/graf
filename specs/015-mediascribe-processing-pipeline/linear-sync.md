# Заметка по синхронизации Linear: 015 MediaScribe Processing Pipeline

**Дата**: 2026-06-11
**Фича**: `015-mediascribe-processing-pipeline`
**Проект Linear**: `2brain Rec / 015 Mediascribe Processing Pipeline`

## Текущее состояние

- Синхронизация GitHub issues завершена для всех задач реализации: T001-T087
  связаны с GitHub issues #550-#636 в `yshishenya/crisp`.
- Синхронизация Linear началась после создания GitHub issues и создала Linear
  issues для T001-T079: с YSH-274 по YSH-352.
- Синхронизация Linear остановилась до T080-T087, потому что workspace вернул
  ошибку лимита активных issues.

## Задачи, не созданные в Linear

У этих задач есть GitHub issues, но во время этого прохода они не были созданы
в Linear:

- T080 -> GitHub #629
- T081 -> GitHub #630
- T082 -> GitHub #631
- T083 -> GitHub #632
- T084 -> GitHub #633
- T085 -> GitHub #634
- T086 -> GitHub #635
- T087 -> GitHub #636

## Как восстановить синхронизацию

После увеличения лимита Linear workspace или после закрытия/архивации старых
активных Linear issues повторно выполнить:

```sh
. ./.env
python3 .specify/extensions/linear-sync/scripts/linear_sync.py sync --feature 015 --apply
```

После этого повторно выполнить проверки validation/import перед закрытием
sync-checkpoint.

## Влияние на реализацию

Это ограничение синхронизации трекера, а не блокер проектирования реализации.
`tasks.md` остается источником правды по порядку реализации, а traceability
через GitHub issues уже полная.
