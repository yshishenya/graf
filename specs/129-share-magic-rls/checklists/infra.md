# Infrastructure Checklist: Надёжное принятие invitation magic-link

**Purpose**: Проверить release, rollback, database и production evidence gates

**Created**: 2026-07-26

**Feature**: [spec.md](../spec.md)

## Validation And Release

- [X] Focused isolated-Postgres regression определена в quickstart
- [X] Полный local CI обязателен до PR/merge
- [X] Release uses immutable CalVer tag and exact deployed SHA
- [X] macOS update continuity and installed update smoke остаются в release gate

## Database And Runtime Safety

- [X] Existing migration head проверяется; новая migration не добавляется без необходимости
- [X] Backup-before-deploy и restore rehearsal входят в deploy gate
- [X] Disposable RLS probes и runtime role checks входят в evidence
- [X] API, Temporal, workers, production smoke и live/ready health проверяются

## Rollback And Observability

- [X] Guarded rollback target и previous signed app/update artifact определены
- [X] Post-deploy invitation logs проверяются sanitized и metadata-only
- [X] Production failure не объявляется исправленным по одному health endpoint
- [X] required post-deploy follow-ups фиксируются честно, если не выполнены

## Notes

- `cd-remote.sh --execute` выполняется только после explicit release approval и
  успешного local validation.
