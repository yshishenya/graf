# Spec Kit analysis: Адаптивное стартовое состояние боковой панели

**Date**: 2026-08-18
**Feature**: [spec.md](spec.md)
**Plan**: [plan.md](plan.md)
**Tasks**: [tasks.md](tasks.md)
**Lane**: `high-risk-feature`

## Inputs and gate

- `spec.md`, `clarify.md`, `plan.md`, `research.md`, `data-model.md`,
  `contracts/sidebar-responsive-default.md`, `quickstart.md` прочитаны.
- Constitution 4.2.0 проверена до Phase 0 и после Phase 1 design.
- Critical clarification gaps: 0.
- Unresolved placeholders in feature artifacts: 0.

## Requirement coverage

| Requirement | Covered by | Status |
|---|---|---|
| FR-001 / FR-002 responsive defaults | T002, T003, T004, T006 | Covered |
| FR-003 explicit state priority | T002, T003, T004, T006 | Covered |
| FR-004 one-time initialization/no resize overwrite | T002, T003, T004, T008 | Covered |
| FR-005 toggle accessibility contract | T003, T004, T006, T008 | Covered |
| FR-006 shared browser/embedded path and boundaries | T002, T004, T005, T006 | Covered |
| SC-001 boundary matrix | T002, T006 | Covered |
| SC-002 visual labels/overflow | T005, T006, T008 | Covered |
| SC-003 pointer/keyboard parity | T002, T003, T006, T008 | Covered |
| SC-004 resize/manual-state rule | T002, T004, T008 | Covered |
| SC-005 existing shell regression | T006, T009 | Covered |

## Findings

No critical, high or blocking findings remain.

The apparent difference between `is-rail-pinned` (expanded-only explicit
marker) and a collapsed user choice is intentional and bounded by the spec:
the choice is ephemeral for the current page lifetime, while cross-session
persistence is out of scope. The existing `railReady` guard covers partial
initialization; a resize listener would be a regression, not a missing feature.

## Boundary evidence correction

Первичная гипотеза `721/720` для embedded не совпала с effective CSS: правило
`@media (max-width: 1120px)` уже переводит embedded shell в compact grid, а
`is-rail-pinned` на 981–1120 px оставлял раскрытую sidebar поверх compact
колонки. Поэтому спецификация и harness используют CSS-aligned границу
`1121/1120`; нижняя граница 720 остаётся в матрице как проверка compact
подрежима.

## Checklist status

| Checklist | Result |
|---|---|
| `checklists/requirements.md` | 9/9 requirement-quality items pass |
| `checklists/ux.md` | 6/6 requirement-quality items pass |

## Task quality

- T001–T009 are dependency ordered.
- Every task has checkbox, unique ID, required story marker where applicable,
  and an exact project-relative file path.
- The only parallel tasks are documentation/test setup or independent
  changelog work; shared JS implementation remains ordered.
- No task introduces storage, auth, capture, AI, permissions, routing or
  release behavior.

## Validation evidence — 2026-08-18

- Focused unit selection: `76 passed`, `2 warnings`.
- Focused static/contract selection: `4 passed`, `44 deselected`, `2 warnings`.
- `node --check apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`:
  pass.
- `git diff --check`: pass.
- `infra/scripts/ci-local.sh --fast`: `1102 passed`, lint pass, Python compile
  pass, `ci_local_result=pass mode=fast`.
- Node VM boundary harness: browser `1280/981/980`, embedded `1121/1120/720`,
  explicit pinned state, two toggles, one listener and resize preservation all
  pass inside the focused contract selection.

## Review and visual limits

Correctness, accessibility, clean-room and Ponytail review оставили один
известный validation gap: authenticated cabinet surface не удалось подтвердить
визуально. Встроенный Browser после запуска local server открыл login и показал
рабочую форму, но synthetic local code `000000` был отклонён; embedded GRAF Dev
показал штатное `Встречи временно недоступны` из-за отсутствующего auth context.
До изменения порога ранее была визуально подтверждена причина регрессии:
embedded shell на 981–1120 px получал expanded class поверх compact CSS grid.
После изменения этот сценарий покрыт source/VM contract, но authenticated
Browser/Computer Use pass остаётся открытым и не подменяется статическим
доказательством. Meeting content, credentials и screenshots в репозиторий не
записывались.

## Decision

Implementation slice validated for code, contract and fast lane. Commit SHA is
recorded in the closeout issue comments; T006 остаётся
открытой до доступного authenticated browser/embedded visual pass; остальные
подтверждённые задачи можно закрыть с issue evidence. Full CI, deploy и release
не входят в этот isolated slice.
