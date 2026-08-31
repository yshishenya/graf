# Specification Quality Checklist: Восстановить воспроизводимое состояние локальной Dev-базы

**Purpose**: Проверить безопасность и полноту migration repair требований.
**Created**: 2026-08-31
**Feature**: [spec.md](../spec.md)

**Review Ownership**: reviewer-owned; implementation agent не меняет checkbox state.

## Scope and Safety

- [ ] Read-only diagnosis отделена от repair.
- [ ] Production, volume deletion и manual pointer edits явно запрещены.
- [ ] Backup/restore rehearsal обязателен до изменения existing volume.

## Requirements

- [ ] Все FR тестируемы и имеют failure behavior.
- [ ] Repair decision содержит owner, boundary, approval и rollback.
- [ ] Idempotency и expected migration head измеримы.
- [ ] Exact SHA и component identity входят в smoke evidence.

## Traceability

- [ ] User stories имеют независимые acceptance scenarios.
- [ ] Edge cases покрывают unknown revision, partial upgrade, production boundary и stale SHA.
- [ ] Legacy Impact согласован с Feature 216 и Feature 220.
