# Данные первого этапа F256

Проигрыватель использует существующие PlaybackReviewState и SpeakerReviewState.
Канонические turns с source_segment_ids задают навигацию, lane segments — речь.
Скорость, выбранные speaker_key, состояние меню, высота и collapse локальны
живой панели. Исходное медиа, результаты обработки и их версии не изменяются.

## Комментарии

MeetingComment: UUID, workspace_id, meeting_id, author_user_id, media_revision_id,
nullable processing_result_id/source_segment_id, start_ms/end_ms, nullable parent_id,
body, created_at/edited_at, version, resolved/resolved_at/resolved_by, request_id.
Ответ только на корень той же встречи; время и resolved принадлежат корню.
Текст1–10000 Unicode code points, не пустой после проверки strip, plain text, без HTML.
Хранится и возвращается исходный body без trim/нормализации; offsets относятся
к точно переданному body. До20 mentions.
start/end конечные, 0≤start≤end≤проверенная длительность; момент допускает end=null.
Ключ (author,meeting,request_id) уникален: такой же запрос возвращает тот же объект,
другое содержимое по тому же ключу —409. Edit/delete/resolution требуют expected_version. Реакция — исключение: PUT
задаёт selected конкретного пользователя и emoji, безопасный повтор без version.

MeetingCommentMention: workspace_id, meeting_id, comment_id, user_id, start/end
индексы Unicode code points; уникальный(comment_id,user_id). Проверяются диапазоны,
отсутствие пересечения и действующий полный доступ адресата. Обычный @текст без
структурированной связи не создаёт уведомления.

MeetingCommentReaction: workspace_id, meeting_id, comment_id, user_id, emoji;
уникальный(comment_id,user_id,emoji). Выбор — идемпотентное желаемое состояние.
Сервер принимает поддерживаемый Unicode emoji из клиентского набора, не HTML/URL.

Корень удаляется с ответами, mentions и реакциями. При смене media revision
старый комментарий недоступен и не переносится на новое аудио по близкому времени.
При перерасшифровке того же медиа временной якорь сохраняется; ссылка на точный
источник остаётся привязана к прежнему результату. Ножницы/remap отложены.

## Права и жизненный цикл

MeetingShareGrant и MeetingShareInvitation: can_comment/can_edit, default=false.
can_edit⇒can_comment; оба требуют full_meeting. Старые grants/invitations не
получают новых прав. Owner имеет все действия; existing can_share не даёт can_edit.
Viewer читает обсуждения; commenter создаёт/отвечает/реагирует/меняет свой текст
и разрешает свой тред; editor дополнительно делится и модерирует чужой тред,
но не переписывает чужой текст. summary_only/public link не видят комментариев.
Новые can_comment/can_edit выдаёт или повышает только owner либо пользователь
с действующим can_edit этой встречи. Старый can_share без can_edit может
делиться в прежних пределах просмотра, но не назначать себе/другому новые права.
Предел проверяется сервером на create/update/invite/accept/rotate; итоговое
право не выше явно выданного, смена audience/scope не усиливает его.
Поля проходят grant update, invitation acceptance/rotation и account merge.
Существующее право admin переименовывать спикера сохраняется отдельно; оно
не превращается в право выдавать новые роли или модерировать комментарии.

Все три таблицы имеют RLS и rec_maintenance_allowed для штатного account merge.
Meeting fence предшествует проверке актуальности и записи. Полное удаление
очищает comment notifications и новые таблицы до связанных source rows.
Account merge переносит author/mentions/reactions и объединяет уникальные связи
без повторного уведомления; preview fingerprint учитывает новые выданные права.

Notification family=comment, kind=mentioned, source_id=comment UUID: нейтральная
карточка без текста, requires_action=false. Создаётся с комментарием и mention
в одной транзакции только уже допущенному адресату, не себе. Producer RLS
проверяет действительную mention, не расширяет права записи result/share.
Удаление mention скрывает/очищает карточку; повтор того же сохранения не создаёт
нового внимания. Повторное добавление после удаления активирует новую revision
той же карточки. authorized_card заново проверяет ACL и существование mention.
Новых email, grant, AI-вызовов, Temporal workflows или внешних библиотек нет.
