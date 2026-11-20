# Security Checklist: F297

**Purpose**: Validate privacy/security requirements before implementation
**Created**: 2026-11-17
**Feature**: [spec.md](../spec.md)

- [x] CHK001 Использует ли retention существующие deletion fences, policy snapshot и metadata-only audit?
- [x] CHK002 Ограничен ли maintenance-контекст точной операцией `retention_scan` и не даёт ли широкого доступа?
- [x] CHK003 Исключены ли из retention-логов аудио, расшифровка, приватные пути и лишние идентификаторы?
- [x] CHK004 Проверяет ли backup prune symlink, `..`, чужие каталоги и выход за root до удаления?
- [x] CHK005 Остаётся ли backup prune dry-run по умолчанию и требует ли `--execute`?
- [x] CHK006 Не раскрывают ли referral-страницы токен, email или приватные пути в логах/ошибках?
- [x] CHK007 Не добавляет ли оферта/лендинг ложных обещаний о хранении, удалении или длительности?
- [x] CHK008 Сохраняется ли CSRF/доступ к checkout и автопродлению без ослабления?
- [x] CHK009 Определён ли явный disable/rollback для retention и prune?
- [x] CHK010 Определено ли, что публичная аналитика необязательна для рендера referral и её отсутствие не ломает страницу?
