# Data Model: полный egress внешнего приглашения

Миграции и новые таблицы не требуются.

Существующие сущности остаются источником истины:

- `MeetingShareGrant`: `content_scope`, download/export flags, expiry, status и
  recipient-bound metadata;
- `ShareRecipientAccessProof`: активность пользователя, workspace membership и
  verified recipient address hashes;
- `MeetingArtifactPolicy`: разрешение audio/transcript/summary/package;
- canonical playback artifact, processing result и outcome set;
- existing egress audit events.

Изменение только передаёт уже вычисленный proof через существующие функции.
Ни один proof, token, email или storage key не должен сохраняться в новой
колонке, URL или committed evidence.
