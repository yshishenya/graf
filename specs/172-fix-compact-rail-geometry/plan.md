# Implementation Plan: Цельная геометрия compact rail

**Branch**: `codex/172-fix-compact-rail-geometry` | **Date**: 2026-08-19 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/172-fix-compact-rail-geometry/spec.md`

## Summary

Восстановить исторически цельный инвариант compact rail: одна ширина rail, одна
внутренняя ось и один квадратный размер для toggle, navigation active/hover/focus
и profile action. Сохранить текущие widths `64px / 176px`, state semantics и
markup. Финальный JS-ready collapsed CSS-блок станет полным владельцем compact
geometry; старые embedded media-блоки перестанут задавать конкурирующие размеры.

## Technical Context

**Language/Version**: CSS; Python 3.13 test contracts; server-rendered HTML and
vanilla JavaScript остаются без behavioral changes

**Primary Dependencies**: Existing cabinet design tokens, CSS grid/flex layout,
pytest static contracts and current browser/native visual tools; no new dependency

**Storage**: N/A

**Testing**: Focused pytest source/static contract, `git diff --check`, computed
geometry inspection in the in-app Browser and Computer Use in `GRAF Dev`

**Risk / Validation Lane**: `high-risk-feature` — shared user-facing navigation,
responsive geometry, accessibility and brand-distance UX; no auth, data,
capture, permissions or native-shell behavior changes

**Release Gate**: `no deploy`; this regression slice prepares a later release
train and does not authorize production or public macOS publication

**Target Platform**: Modern browser and embedded macOS WKWebView cabinet shell

**Project Type**: Server-rendered web cabinet embedded in a macOS desktop shell

**Performance Goals**: Pure CSS layout; no new request, listener, script,
animation or runtime layout loop

**Constraints**: Preserve 64px/176px shell widths, top toggle slot, current
breakpoint and state logic, profile menu, accessible names, focus and no overflow

**Scale/Scope**: One CSS geometry owner, one focused regression contract, one
wide/narrow × web/embedded visual matrix

## Constitution Check

*GATE: Passed before Phase 0 research and re-checked after Phase 1 design.*

- Capture-First MVP Integrity: PASS — no capture, audio or recording path.
- Visible Consent and User Control: PASS — no recording indicators or controls.
- Privacy/secret discipline: PASS — no meeting content, telemetry, network,
  storage or credentials.
- Deletion lifecycle: PASS — no persisted artifact.
- Public macOS distribution: PASS — no signing, package, updater or appcast.
- Spec-driven delivery: PASS — feature 172 includes specify, clarify, plan,
  UX checklist, tasks, analyze, implementation, review and focused evidence.
- UI/accessibility/brand-distance: PASS — one-axis geometry, stable focus,
  original GRAF controls and visual review are explicit gates.

## Validation Plan

1. Extend the existing static contract to require one complete final collapsed
   geometry owner: 40×40 controls, centered placement, centered icons and hidden
   compact header; reject the old 52×36 active item pattern.
2. Run focused cabinet rail/server-shell pytest selections and `git diff --check`.
3. In the in-app Browser inspect computed bounding boxes for wide manual collapse
   and narrow responsive collapse. Require the rail/control/icon centers to
   match within 1px and all active/hover/focus targets to be 40×40px.
4. In `GRAF Dev` use Computer Use to check compact and expanded rail, top toggle
   same-slot behavior, profile bottom inset, titlebar separation and no overlap.
5. Perform correctness, accessibility/visual and Ponytail review. Run
   `infra/scripts/ci-local.sh --fast` once at closeout, not after each edit.

Full CI, deploy, notarization and release checks are outside this isolated CSS
regression and remain owned by the later release train.

## Project Structure

### Documentation (this feature)

```text
specs/172-fix-compact-rail-geometry/
├── spec.md
├── clarify.md
├── plan.md
├── research.md
├── data-model.md
├── contracts/
│   └── compact-rail-geometry.md
├── checklists/
│   ├── requirements.md
│   └── ux.md
├── quickstart.md
├── analysis.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css
apps/server/tests/contract/test_cabinet_static_assets_contract.py
CHANGELOG.md
```

**Structure Decision**: CSS remains the single geometry owner. JavaScript and
Jinja are unchanged because analysis proved the defect is cascade-only. Reuse
the existing contract file rather than adding a browser-test dependency.

## Complexity Tracking

No constitution violations. Ponytail ceiling: delete/narrow conflicting
geometry and complete one existing collapsed selector; no helper, token,
component, script, state or dependency is introduced.
