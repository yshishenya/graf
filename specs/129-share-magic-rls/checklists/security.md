# Security Checklist: Надёжное принятие invitation magic-link

**Purpose**: Проверить полноту auth, RLS, audit, token и privacy требований до реализации

**Created**: 2026-07-26

**Feature**: [spec.md](../spec.md)

## Identity And Authorization

- [X] First-entry flow сохраняет exact verified recipient binding
- [X] Existing identity, wrong recipient, expiry, revoke и replay имеют явные acceptance scenarios
- [X] CSRF-bound POST остаётся единственной mutating continuation точкой
- [X] Исправление не добавляет workspace membership или broad authorization bypass

## Tenant And Audit Boundaries

- [X] Каждый pending row flushed только под соответствующим workspace context
- [X] RLS policy остаётся включённой и принудительной
- [X] Auth audit ownership и metadata-only evidence явно определены
- [X] Shared rate-limit/context callers проверяются на cross-workspace regression

## Privacy And Failure Handling

- [X] Tokens, email, meeting content, audio, transcript и credentials исключены из evidence/logs
- [X] Post-commit notification failure не ломает уже выданный доступ
- [X] Internal errors не превращаются в authorization success или раскрытие встречи
- [X] Deletion/revoke/expiry остаются authoritative на каждом результате/egress path

## Notes

- Policy weakening, maintenance-role bypass и глобальное отключение autoflush не
  допускаются как исправление.
