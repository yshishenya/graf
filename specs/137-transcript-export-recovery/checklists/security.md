# Security Requirements Checklist: transcript-export-recovery

**Purpose**: Проверить, что требования к content egress и repair path не
ослабляют privacy/access/deletion gates.
**Feature**: [spec.md](../spec.md)

## Access and egress

- [x] Owner, permitted non-owner и viewer без доступа различены.
- [x] Отсутствующая policy и явный `meeting_override=disabled` различены.
- [x] Один effective decision используется capability, UI и direct route.
- [x] Shared viewer никогда не получает owner-only transcript/summary/package.

## Provenance and deletion

- [x] Export требует matching processing result, revision и source hash.
- [x] Unknown source IDs, stale candidates и deleted meetings остаются fail-closed.
- [x] Reconcile не меняет policy, deletion state/epoch или immutable meeting lifecycle.
- [x] В spec, plan, tasks, logs и evidence не требуется raw transcript/audio/content.

## Operational safety

- [x] Repair command имеет metadata-only dry-run и явный execute switch.
- [x] Ремонт ограничен текущим результатом и отсутствием accepted outcome.
- [x] Production deploy/reconcile вынесены за отдельное approval gate.
