# Надёжный allocator свежих Feature ID

**Feature ID**: `F225`

**Feature Branch**: `codex/225-feature-id-allocator`

**Created**: 2026-08-31

**Status**: Реализация проверяется в общем PR F225/F259

**Input**: Исправить ложное занятие Feature ID служебными Codex turn-diff refs.

## Actors and Goals

- Feature owner получает номер, который не конфликтует с реальными feature specs, refs, issues и PRs.
- Agent может запускать allocator из worktree, не разбирая внутренние служебные refs Codex.
- Reviewer видит воспроизводимое доказательство свежей нумерации.

## User Scenarios & Testing

### User Story 1 - Получить следующий свежий номер (Priority: P1)

Владелец запускает allocator и получает ближайший свободный Feature ID с учётом локальных specs, git refs и GitHub истории.

**Independent Test**: Synthetic repository с реальными ветками и служебными refs возвращает ожидаемый номер.

**Acceptance Scenarios**:

1. **Given** служебный ref `codex/turn-diffs/captures/.../27656752-uuid/base`, **When** allocator сканирует refs, **Then** он не добавляет `27656752` в occupied Feature IDs.
2. **Given** реальная ветка `codex/225-feature-id-allocator`, **When** allocator сканирует refs, **Then** Feature ID `225` остаётся занятым.

### User Story 2 - Сохранить collision safety (Priority: P1)

Allocator продолжает учитывать specs, обычные local/remote branches и явные GitHub feature markers.

**Independent Test**: Self-test проверяет занятый номер, повторный claim и GitHub umbrella validation.

**Acceptance Scenarios**:

1. **Given** номер занят spec или branch, **When** запрашивается claim, **Then** операция fail-closed.
2. **Given** GitHub issue/PR содержит canonical `[NNN]` или `feature:NNN`, **When** allocator строит occupied set, **Then** номер не предлагается повторно.

## Edge Cases and Failure States

- Внутренний ref содержит UUID/timestamp перед сегментом с дефисом: он игнорируется полностью.
- Служебный namespace изменился: неизвестные refs не должны автоматически считаться feature без canonical branch shape.
- Remote API недоступен: strict claim завершается ошибкой, offline draft остаётся явно помеченным.
- Недействительный или конфликтующий umbrella issue не резервирует номер.

## Requirements

### Functional Requirements

- **FR-001**: Allocator MUST ignore refs under known Codex service namespace `codex/turn-diffs/captures/` when extracting Feature IDs.
- **FR-002**: Allocator MUST continue scanning real specs, local/remote feature branches, GitHub issue titles, labels and explicit Feature ID body markers.
- **FR-003**: Internal refs MUST NOT affect `next_available` or collision decisions.
- **FR-004**: Self-test MUST include a regression fixture for a high numeric Codex capture ref and a normal feature branch.
- **FR-005**: Strict GitHub claim MUST remain fail-closed and offline mode MUST remain explicitly labelled draft.
- **FR-006**: Documentation or test comments MUST explain the service-ref boundary without exposing machine/private paths in evidence.
- **FR-007**: Online GitHub inspection MUST fail closed within a bounded timeout and MUST NOT label an incomplete result as `github-checked`.

## Success Criteria

- **SC-001**: In a synthetic repository containing Features 222–224 but not Feature 225, allocator returns `225` after excluding the observed internal `27656752` ref; the historical expected number `226` applied to the 2026-08-31 snapshot only. In a current checkout the exact expected number is recomputed from all occupied sources using the shared F259 numbering policy.
- **SC-002**: Regression self-test fails if a service ref is reintroduced into occupied IDs.
- **SC-003**: Existing claim/collision/GitHub umbrella tests remain green.
- **SC-004**: Fast CI passes on exact feature SHA with metadata-only evidence.
- **SC-005**: A timed-out or malformed online GitHub response exits non-zero and never emits `mode=github-checked`.

## Assumptions and Dependencies

- `codex/turn-diffs/captures/` is an internal non-product namespace and is safe to ignore.
- Canonical product branches contain a numeric segment followed by `-slug`.
- GitHub issue/PR scanning remains authoritative for public repository reservations.

## Scope

### In Scope

- `_ids_from_refs` filtering and allocator regression tests.
- Feature 225 Spec Kit artifacts and changelog fragment.

### Out of Scope

- Deleting internal refs or changing Codex storage.
- Changing already reserved feature metadata.
- Dev runtime, release deployment or legacy deletion.

## Legacy Impact

**Classification**: `untouched`

Allocator behavior is governance-only; no compatibility alias, fallback flag or
legacy runtime path is introduced.
