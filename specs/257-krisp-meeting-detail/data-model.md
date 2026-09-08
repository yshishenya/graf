# Data Model

Новых таблиц, API или постоянных пользовательских настроек нет.

| Существующая сущность | Использование | Ограничение |
|---|---|---|
| Meeting + title_version | заголовок и переименование | expected_version, серверная авторизация, CSRF |
| MeetingReviewResponse | дата, состояние, доступное содержимое | данные только из существующей авторизованной проекции |
| MeetingSummarySlot / OutcomeSet | текущий формат и результат | pinned revision; проверенная автоматическая публикация |
| Transcript / source refs | реплики и переходы | точная редакция/сегмент, никакой эвристики имён |
| Export form | доступные scope, format, revision ids, endpoint | one source of truth для нового trigger |
| DOM state | tab, pending copy, focus | очищается вместе с main; не сохранять приватный текст |

Переходы просмотра: outcomes ↔ recording; closed ↔ format list/catalog; idle → copy pending → success/error. Async copy захватывает scope и исходную форму; при её отсоединении прекращает запись в буфер. Изменение доступа использует существующий recovery; новая шапка удаляется вместе со всем содержимым.

Перед clipboard недостаточно одной isConnected: также требуются подключённый trigger, отсутствие replacement-active и разрешённый захваченный option[value] из select[data-export-scope]. Pending общий для copy/export; finally не восстанавливает запрещённое действие. Обычная смена вкладки сохраняет захваченный состав.
