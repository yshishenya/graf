# Research: Feature 228 legacy retirement process

Дата: 2026-08-31

## Решение

Feature 228 остаётся planning-only контуром. Реестр будет metadata-only и
versioned; обнаружение создаёт только `candidate` или `blocked` записи. Поля
решения (`classification`) появляются только после owner/reviewer decision.
Каждый approved `remove` contour получает отдельный bounded retirement slice с
полным набором rollback, validation, protected-domain и traceability gates.

## Проверенные источники

- `spec.md` Feature 228 — требования FR-001–FR-018 и запрет runtime deletion.
- `plan.md` — audit baseline, protected-domain matrix и release-train boundary.
- `contracts/retirement-slice.md` — обязательные границы и evidence links.
- Feature 216/227 governance and release guidance — reviewer-owned checklists,
  exact-SHA fast CI и один authoritative Full CI после freeze.

## Рассмотренные альтернативы

1. Автоматически считать найденный legacy удаляемым — отклонено: discovery не
   доказывает отсутствие поддерживаемых клиентов или исторических данных.
2. Хранить активный реестр и feature pointer в `AGENTS.md` — отклонено: это
   создаёт shared mutable context и конфликты между worktrees.
3. Делать Full CI на каждый commit feature — отклонено: release evidence должна
   относиться к frozen candidate, а не к промежуточным SHA.

## Открытые решения

- Owner/reviewer должны классифицировать реальные observed contours после
  inventory; до этого они остаются `candidate` или `blocked`.
- Реализация registry, validators и protected-domain fixtures выполняется
  отдельными task-backed slices после прохождения planning gates.

## Ограничения исследования

Исследование не читает production data, Temporal history, MediaScribe payloads,
raw audio/transcripts, credentials или signed URLs и не разрешает их удаление.
