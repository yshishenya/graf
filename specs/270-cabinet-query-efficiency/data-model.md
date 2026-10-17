# Модель чтения F270: продолжение T032/T033

Схема и жизненный цикл сущностей не меняются. Источник — существующие модели.

| Сущность/группа | Ключ и условия | Назначение |
|---|---|---|
| Meeting | workspace + meeting; прежняя проверка удаления и доступа | Начальная и повторная календарная авторизация |
| MediaRevision | workspace + meeting; accepted/immutable и прежний порядок | Текущий текст; отдельно accepted playback fallback и pinned revision |
| ProcessingWorkflow/Result | точная revision, прежняя lineage и разные порядки latest/effective | Текст и доступность выгрузки |
| SummarySlot/OutcomeSet/Result | workspace + meeting + template + pinned ID; прежняя проверка публикации/lineage | Default/selected resolver раздельны; прежний fallback отображения selected→default сохраняется |
| ArtifactPolicy/Normalization/Upload | workspace + meeting + exact accepted revision; прежние статусы | Воспроизведение и выгрузка |
| CalendarLink/Dependency/Workspace | прежние ключи и ограничения | Одиночные поля read model |
| Transcript/Diarization/Speaker names | workspace + meeting + exact result; прежний порядок | Полные коллекции; presence только для той же lineage |

`CabinetReadPrefetch` хранит только строки одного вызова и точных ключей.
Проверенный None означает отсутствие; непрочитанный ключ оставляет прежний SQL.
Карты membership/grants для детали пусты: решения доступа не кэшируются.
При выходе, исключении и вложенном вызове прежнее db.info восстанавливается.
Переходов состояния, новых полей, миграций и новых внешних контрактов нет.
