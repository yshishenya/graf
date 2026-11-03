# F292 — данные и состояния

## MeetingShareGrant (существующая модель)

Одна active link на workspace/meeting, nullable published_summary_id, content_scope строго summary_only/full_meeting. Старые строки не мигрируются в full_meeting. publication_version >=1; token hash и зашифрованный восстанавливаемый token изменяются атомарно только при rotate. Копирование не мутирует строку. expires_in_days строго 7/30/90. Создание/изменение под meeting fence; изменение требует grant_id + expected_version, иначе 409. full_meeting не требует готовых итогов, повышенные anonymous capabilities запрещены. Переход full→summary создаёт явную snapshot и немедленно закрывает следующие audio/transcript чтения. legacy writer не изменяет современную encrypted/versioned строку без проверки версии.

## Публикация итогов

PublishedMeetingSummary неизменна до явного update. Состав F286 сохранён. Полная встреча читает текущую принятую расшифровку effective_processing_result_query, фильтруя workspace_id/meeting_id/processing_result_id одновременно. В публичной DTO только label/time/duration/summary/protocol/transcript{speaker,text,start_ms,end_ms}; никаких private metadata/календарных адресов/provider IDs/storage keys/comments. Обновление принятого аудио инвалидирует неподходящие результаты, не подмешивает другую версию.

## Доказательство публичного доступа

Внутренний immutable объект grant/workspace/meeting/scope/version. Создаётся только resolver после блокировки и повторного чтения токена, политики, срока и удаления. Перед аудио revalidate под тем же fence. Не заменяет пользователя владельцем. Анонимный audit user/device=None; метаданные только разрешённые идентификаторы/класс/размер/диапазон.

## Контекст продолжения и приложение

Зашифрованный Fernet cookie, TTL 600s, HttpOnly/SameSite=Lax/Secure для HTTPS; только canonical relative public/share route + tab/position. Входу передаётся постоянный /shared-meeting/continue. Некорректный/просроченный cookie даёт безопасный возврат, никогда внешний redirect. Native intent version1 допускает только configured grafrec или grafrec-dev, canonical UUID, 32..128 ASCII символов A-Z/a-z/0-9/_/-, фиксированную вкладку и integer position_ms 0..86400000. Дубликаты/неизвестные поля, credentials/port/path/origin отвергаются. Одно ожидающее намерение поглощается после готовности окна; browser session не переносится.

## Приглашения и доставка

Переиспользуются MeetingShareInvitation/адресные grants и F286 SummaryDeliveryBatch. Нормализация адреса, подтверждение личности, CSRF, лимиты, immutable payload/idempotency и unknown delivery остаются. Открытие, поиск, выбор адресата и публичный просмотр не создают приглашение/письмо/membership. Командная audience не эмулируется workspace без ясной подписи «Участники пространства».


Общая аудитория: атомарные переходы invite_only/workspace/link описаны в contracts; fingerprint (SHA256/64hex) active общих grants сравнивается под fence. User/invitations вне набора и сохраняются. Публичный media_version (24hex SHA256 revision/result) не раскрывает исходные UUID; несовпадение на playback 409. Fragment grammar и token bound заданы FR-025.
