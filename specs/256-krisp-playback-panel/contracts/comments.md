# HTTP-контракт комментариев F256

Базовый путь: /api/v1/cabinet/meetings/{meeting_id}. Общий обработчик проверки
поддерживает owner и shared recipient с явным owner workspace и существующим
recipient proof. Параметр workspace не является разрешением доступа.

| Метод / окончание | Контракт |
|---|---|
| GET /comments | status=open/resolved/all, author_id?, limit≤100, cursor; корни и ограниченные ответы, next_cursor, capabilities |
| GET /comments/{id} | Явный корень (по ID ответа разрешается его корень), первая страница ответов, next_reply_cursor; текущая ACL |
| GET /comments/{root_id}/replies | limit≤100, cursor; ответы по(created_at,id), next_cursor, та же ACL |
| POST /comments | request_id, media_revision_id, start_ms, end_ms?, processing_result_id?, source_segment_id?, body, mentions |
| POST /comments/{root_id}/replies | request_id, body, mentions; якорь наследуется от корня |
| PATCH /comments/{id} | expected_version, body, mentions |
| DELETE /comments/{id} | expected_version; корень удаляет весь тред |
| PUT /comments/{root_id}/resolution | expected_version, resolved:boolean |
| PUT /comments/{id}/reaction | emoji, selected:boolean |
| GET /comment-mention-candidates | q≤100 символов; ≤20 активных людей, уже имеющих полный доступ |

Ответы не кешируются. Каждая mutation требует аутентификацию, существующий
CSRF/device контекст, meeting fence и повторную проверку ACL/версии.
404 — недоступный объект, 403 — запрещённое действие в видимой встрече,
409 — устаревшая версия/другое содержимое request_id, 422 — неверный ввод.
Сервер не доверяет parent/source/media UUID без проверки той же встречи/workspace.
Тела ошибок не содержат содержимого чужой встречи.

Поля и роли описаны в [data-model.md](../data-model.md). Пагинация по(created_at,id)
стабильна; прямой comment_id открывает тред через обычную проверку. Копирование
ссылки на страницу с comment_id не создаёт доступ, приглашение или email.

UI: форма фиксирует текущий момент либо выбранную реплику, отмена не сохраняет;
успех показывает тред, ошибки сохраняют введённый текст. До ответа submit disabled.
Reply/edit используют тот же редактор, plain text/Unicode emoji/mentions.
Escape возвращает фокус, вложенный emoji/mention picker закрывается первым.
Боковая панель360 px ограничена viewport; фильтры open/resolved/author/source,
источник только Transcript. Delete требует подтверждения; для корня ясно
сообщает об удалении ответов/реакций. Resolve/reopen сохраняют обсуждение.
Реакции показывают счётчик и собственный выбор. Ссылки на недоступную версию
показывают причину, а не переадресуют на случайное новое время.

Новые роли выдаёт только owner/editor по правилу data-model.md; отрицательные
проверки включают self-escalation через старый can_share и подмену invitation.
Mentions offsets считаются в Unicode code points исходного body без нормализации.
Version требуется для edit/delete/resolution; reaction PUT идемпотентен по
(comment,user,emoji,selected) и не требует expected_version. Пагинация replies
поддерживает последовательную загрузку всех ответов без усечения.

## Фактическая JSON-проекция первого этапа

GET list: `{items,next_cursor,media_revision_id,capabilities}`; capabilities содержит
`can_comment,can_edit,can_manage_roles,emoji_options`. GET root и mutation возвращают
сам объект комментария, без дополнительной оболочки. Поля: `id,parent_id,author_user_id,
author_label,media_revision_id,processing_result_id,source_segment_id,start_ms,end_ms,
body,version,resolved,created_at,edited_at,mentions,reactions,can_edit,can_delete,can_resolve`.
Корень дополнительно содержит `replies,next_reply_cursor`. Реакции: `{emoji,count,selected}`.
GET mention candidates: `{items:[{user_id,display_label}]}`. GET replies: та же
страничная оболочка `{items,next_cursor,media_revision_id,capabilities}`.
PATCH `/shares/{grant_id}/permissions` принимает `{can_comment,can_edit}`;
доступен только owner/editor, обновляет существующее право без email/rotation.
UI селекторы: `data-share-comment-role`, `data-share-existing-role`,
`data-share-permissions-url`; сервер показывает их только при `share.can_manage_roles`.

The root list additionally returns `total_count` and `source_counts` entries
`{source_segment_id, count}`. Counts cover all roots on the accepted immutable
media revision, independently of status, author, source filters and pagination;
replies do not increment these counts. Repeated query parameter
`source_segment_ids=<UUID>` filters roots for a canonical speaker turn containing
multiple source segments (maximum 100 IDs). `source_counts` omits unanchored roots,
while `total_count` includes them.

Cross-workspace share create/search/invite/permissions/rotate/revoke and share
fragments accept `workspace_id` for the meeting owner workspace. The authenticated
actor remains in the validated recipient scope; every operation rebuilds recipient
proof and checks the effective meeting permissions. Speaker rename uses the same
boundary. Pending or rejected media revisions never replace the accepted immutable
revision used by playback comments or mention notification links.

`source_segment_id` identifies the canonical turn's original `TranscriptSegment`
or `DiarizationSegment`. It is validated against the supplied processing result,
meeting and workspace; that result must belong to the accepted immutable media
revision. It is a polymorphic UUID, so there is no foreign key to only one source
table. A foreign source or mismatched result is rejected with 422.
