# AI Processing Requirements Checklist: transcript-export-recovery

**Purpose**: Проверить полноту требований к восстановлению outcome без
подмены provenance или candidate lifecycle.
**Feature**: [spec.md](../spec.md)

## Source integrity

- [x] Стабильный transcript segment ID определён как источник истины.
- [x] Canonical sequence для известного ID определён однозначно.
- [x] Unknown ID, malformed reference и invalid sequence имеют fail-closed результат.
- [x] Нормализация не разрешает ссылки вне pinned transcript.

## Publication lifecycle

- [x] Первый trusted deterministic baseline и последующий AI/manual candidate различены.
- [x] Accepted current outcome не заменяется автоматически.
- [x] Revision/result/source-hash fences сохраняются до публикации.
- [x] Повторная reconcile-операция идемпотентна и не создаёт скрытые варианты.

## Failure behavior

- [x] Ошибка AI validation не удаляет и не заменяет уже accepted result.
- [x] Требования не вводят новый provider, credential или unlimited retry loop.
- [x] Readiness использует imported result, а не неподходящее изменение lifecycle status.
