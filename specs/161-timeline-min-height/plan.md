# Implementation Plan: Адаптивная высота таймлайна спикеров

**Branch**: `codex/168-cabinet-layout-polish` | **Date**: 2026-08-19 | **Spec**: [spec.md](spec.md)

## Summary

Оставить существующий безопасный размер 120px для встреч, где нужно показать
три дорожки, но перед начальным применением высоты измерять естественный размер
контейнера. Для 1–3 дорожек оставить естественный размер, для больших наборов
сохранить bounded keyboard/pointer resize.

## Technical Context

**Language/Version**: Python 3.13, vanilla JavaScript, CSS, Jinja2

**Primary Dependencies**: Existing FastAPI cabinet rendering, `cabinet.js`,
`cabinet.css`, pytest and Node; no new dependency

**Storage**: N/A; no persistence

**Testing**: Focused pytest unit/contract checks, Node resize harness,
`node --check`, synthetic Browser and embedded visual review

**Risk / Validation Lane**: `high-risk-feature` — shared meeting UX,
accessibility and playback-adjacent layout; capture and audio semantics remain
unchanged

**Release Gate**: `no deploy`; production release belongs to the later release
candidate

**Target Platform**: Modern browser and embedded macOS WebView cabinet

**Project Type**: Server-rendered web cabinet

**Performance Goals**: One existing viewport listener; no polling, storage,
network call or second resize controller

**Constraints**: Measure without retaining inline height, clamp against content
and viewport, preserve playback state and partial-update idempotency

**Scale/Scope**: One existing speaker timeline shell plus rendering/static/unit
and contract tests

## Constitution Check

- Capture-First MVP Integrity: PASS — no recording, audio route or playback
  source changes.
- Visible Consent and User Control: PASS — capture controls are untouched.
- Privacy and secret discipline: PASS — only synthetic metadata is used.
- UI/accessibility/clean-room: PASS — separator ARIA, focus and original shell
  contract remain explicit.
- Spec-driven delivery: PASS — clarify, research, checklist, tasks, analyze,
  focused implementation and review are recorded.

## Validation Plan

1. Run speaker timeline unit and static contract checks.
2. Run the Node harness for 2-row fit, 3-row fit, 4+/12-row overflow and
   viewport-limited cases; verify one listener after partial update.
3. Run `node --check` and `git diff --check`.
4. Review synthetic browser and embedded screenshots for 1/2/3/12 speakers,
   wide/narrow layout and no gap before playback.
5. Run `infra/scripts/ci-local.sh --fast` once after the combined UX slices.

## Project Structure

```text
specs/161-timeline-min-height/
├── spec.md
├── clarify.md
├── plan.md
├── research.md
├── data-model.md
├── contracts/timeline-min-height.md
├── checklists/requirements.md
├── checklists/ux.md
├── quickstart.md
└── tasks.md

apps/server/src/twobrain_rec_server/cabinet/
├── rendering.py
├── static/cabinet/cabinet.css
└── static/cabinet/cabinet.js

apps/server/tests/
├── unit/test_cabinet_web_shell.py
└── contract/test_cabinet_static_assets_contract.py
```

**Structure Decision**: Reuse the existing shell and common `applyHeight` path;
do not add a component, model, store or resize abstraction.

## Complexity Tracking

No constitution violations. Ponytail ceiling: temporarily clear inline height,
measure once, then reuse the existing clamp; no observer, persistence or new
layout service.
