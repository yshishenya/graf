# Infrastructure Requirements Checklist: transcript-export-recovery

**Purpose**: Проверить эксплуатационную полноту изменения в PostgreSQL/
processing/maintenance потоке.
**Feature**: [spec.md](../spec.md)

## Runtime boundaries

- [x] Решение совместимо с существующими PostgreSQL entities; migration не требуется.
- [x] Processing import использует существующий fenced outcome service.
- [x] Maintenance path использует существующий RLS maintenance context.
- [x] Никаких новых network calls или direct desktop-to-provider paths не требуется.

## Validation and rollout

- [x] Есть focused pytest matrix для egress, outcome, AI validation и readiness.
- [x] Есть `git diff --check` и fast local CI gate.
- [x] Production dry-run и execute разделены явным approval boundary.
- [x] Repair output ограничен идентификаторами, состояниями и counts.

## Recovery and compatibility

- [x] Existing explicit policy rows retain their meaning.
- [x] Existing candidate review and accepted-history behavior remain compatible.
- [x] Legacy no-revision baseline behavior remains covered.
- [x] Known limitation — historical rows need an approved bounded reconcile after rollout.
