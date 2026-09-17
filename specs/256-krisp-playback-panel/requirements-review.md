# Независимая проверка требований F256

Дата: 2026-09-08. Reviewer: отдельный агент `requirements_review`, не исполнитель
продуктового кода. Режим: `high-risk-product`, reviewer-owned checklist и
согласованность spec/plan/data-model/contracts/tasks/quickstart.

Объём: US1–US3; комментарии независимы от ножниц и входят сейчас. Ножницы,
Share highlight и изменение аудио отложены пользователем. Проверка Dev обязательна
после завершения; браузер не заменяет её. Исторический полный эталон не расширяет
текущий этап.

**Актуальный итог повторного прохода: CRITICAL0 · HIGH0 · MEDIUM0.
Checklist infra4/4, security5/5, ux5/5. Переход к реализации US1–US3 разрешён
после фактически завершённой синхронизации задач с GitHub.** Это проверка
достаточности требований, не implementation PASS. Результат исходного прохода
ниже сохранён для истории исправлений.

## Решение первого прохода

**Пока нельзя переходить к реализации US1–US3 только на основании issue sync.**
Открыты два HIGH и три MEDIUM ниже. Конституционных противоречий первого этапа
не выявлено: захват/AI не изменяются, комментарии остаются в GRAF, lifecycle
и независимые ассеты предусмотрены. Но высокорисковые checklists должны быть
завершены, а HIGH устранены до кода по spec-kit-flow.md. Это не implementation
PASS и не разрешение коммита/выпуска.

## Замечания

| ID | Уровень | Источник | Пробел и требуемое исправление |
|---|---|---|---|
| RQ-01 | HIGH | data-model.md «Права и жизненный цикл»; FR-011; T006 | Роли и запрет миграционного повышения заданы, но не задано, кто может выдавать новые can_comment/can_edit и предел делегирования через grants/invitations. Существующий can_share явно не даёт can_edit, однако прежние share write paths проверяют can_share. Нужен однозначный запрет повышения собственных/чужих новых полномочий через старое право делиться и тест на это, включая invitation acceptance/rotation. |
| RQ-02 | HIGH | contracts/comments.md GET /comments и GET /comments/{id}; T005/T009 | Ограниченные ответы заявлены, но продолжение ответов не имеет cursor/маршрута. В длинном обсуждении пользователь либо теряет ответы, либо реализация вынуждена выдавать неограниченное тело. Указать отдельную ограниченную пагинацию ответов, порядок и доступ к корню; проверить границу страницы и дочитывание. |
| RQ-03 | MEDIUM | data-model.md текст/mentions; T005/T009 | Текст trim-ится, но не указано, относительно какой строки вычисляются индексы mentions. До/после trim меняет адресуемую подстроку; JavaScript UTF-16 отличается от code points. Явно закрепить каноническую строку и преобразование индексов, проверить ведущие пробелы и составной emoji. |
| RQ-04 | MEDIUM | data-model.md «Изменения требуют expected_version»; contracts/comments.md mutation paragraph/table | Общее требование версии конфликтует с PUT reaction без expected_version и POST с request_id. Перечислить операции с optimistic version и исключения с идемпотентным желаемым состоянием; определить, увеличивает ли реакция версию текста/треда. |
| RQ-05 | MEDIUM | tasks.md T006/T009 | Часть путей задана как «existing share projections/fragments» и «подключив ... к общей панели». По правилу tasks требуются точные пути и владельцы общих изменений. Назвать files для проекции/формы роли и точки подключения комментариев; сохранить отсутствие конфликтующих параллельных владельцев. |

## Что уже достаточно определено

- Проигрыватель: один audio, play-event truth, play rejection, ±15, скорость,
  текущие канонические реплики, отсутствие двойного keyboard шага, конец записи.
- Listen: пустой выбор означает всех, объединение перекрытий, пропуск пауз,
  остановка после последнего выбранного интервала, палитра до сортировки.
- Доступность: Escape/focus, native range keys, reduced motion, обе темы,
  размеры/200%, измеримые допуски; контроль единственного GRAF Dev отдельно.
- Комментарии: parent/source/media проверяются в одной встрече/workspace,
  повторная ACL и CSRF, нейтральные mentions без email/выдачи доступа,
  producer RLS связан с настоящей mention и не расширяет result/share.
- Lifecycle: удаление корня с ответами/связями, meeting purge до source rows,
  account merge, повторное упоминание через revision карточки, отсутствие
  текстов в обычных логах/AI, stale media без молчаливого переноса якоря.
- Миграция: одна0090 после0089, false для новых прав, full_meeting constraint,
  maintenance RLS для штатного слияния; прежняя наблюдаемость не удаляется.

## Источники и дальнейший gate

Прочитаны constitution7.0.0, guidance README/spec-kit-flow/product-gates/
release-and-validation, связанные разделы PRD и current-product-status,
spec.md, plan.md, data-model.md, оба contracts, tasks.md, quickstart.md,
checklists, backend-research, handoff/reference-contract. Сопоставлены
существующие cabinet/access.py и модели grants/invitations, merge head0089.

После исправлений reviewer повторно проверяет RQ-01–05, закрывает затронутые
checkboxes и записывает итог. Затем обязательны актуальный analyze и issue sync;
разрешение реализации не заменяет будущие runtime/Dev/PR/release gates.

## Повторный проход после исправлений

Повторно прочитаны изменённые spec.md, data-model.md, contracts/comments.md,
tasks.md и существующий quickstart.md. Продуктовый код reviewer не менял.

| ID | Итог | Evidence исправления |
|---|---|---|
| RQ-01 | Закрыто | data-model.md44–51: owner/editor, явный запрет повышения через прежний can_share, create/update/invite/accept/rotate и неизменность admin-прав на спикера; contracts/comments.md41–42, T005/T006 включают отрицательный сценарий. |
| RQ-02 | Закрыто | contracts/comments.md10–11: корень/первая страница/next_reply_cursor и GET replies с limit≤100/cursor по(created_at,id); T005 включает пагинацию, T009 — интерфейс ответов. |
| RQ-03 | Закрыто | data-model.md14–25: непустота проверяется strip, хранится исходный body без нормализации, offsets Unicode code points той же строки; contracts/comments.md43 и T009 требуют тот же контракт. Преобразование UTF-16 в code points является реализацией заданного контракта, не новой продуктовой неопределённостью. |
| RQ-04 | Закрыто | data-model.md18–20 и contracts/comments.md44–46 явно отличают optimistic edit/delete/resolution от создания с request_id и идемпотентного reaction PUT. Общее упоминание проверки версии применяется с этим перечисленным исключением. |
| RQ-05 | Закрыто | T006 именует cabinet/queries.py и cabinet/templates/cabinet/fragments/meeting_share.html; T009 — base.html и hook при повторной инициализации detail. Владение общим cabinet.js остаётся у T003/T004 и согласуется с T009 в dependencies. |

Конституционный post-design gate пройден на уровне требований. Новых критических,
высоких или средних противоречий между US1–US3, моделью, HTTP/панельным контрактом
и задачами не выявлено. Полнота реализации, producer RLS, миграция и конкурентные
проверки пока НЕ подтверждены — это задачи T002–T012. Проверка issue sync этому
reviewer не поручалась и не объявляется завершённой. После sync разрешён код;
коммит, Dev promotion и release сохраняют собственные проектные границы.
