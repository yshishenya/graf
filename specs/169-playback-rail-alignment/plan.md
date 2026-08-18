# Implementation Plan: Выравнивание нижнего playback относительно rail

**Branch**: `codex/168-cabinet-layout-polish` | **Date**: 2026-08-19 | **Spec**: [spec.md](spec.md)

## Summary

Свести поздний CSS слой grid и `--playback-inline-start` к одной state-based
ветке. Playback remains fixed and audio-owned; only its horizontal origin
changes with the visible rail.

## Technical Context

**Language/Version**: CSS, pytest, Node

**Primary Dependencies**: Existing cabinet CSS and playback shell; no new dependency

**Storage**: N/A

**Testing**: Static contract checks, existing Node rail/playback harness,
`node --check`, synthetic Browser/embedded visual review

**Risk / Validation Lane**: `high-risk-feature` — shared fixed playback surface

**Release Gate**: `no deploy`

**Target Platform**: Browser and embedded macOS WebView

**Project Type**: Server-rendered web cabinet

**Performance Goals**: CSS-only state switch, no layout polling

**Constraints**: Preserve playback DOM, currentTime, source and vertical sizing

**Scale/Scope**: Existing late cabinet CSS layer and focused tests

## Constitution Check

PASS: playback semantics and capture controls are untouched; only presentation
offsets change. Privacy, accessibility, clean-room and Spec Kit gates remain
covered by the parent UX batch.

## Validation Plan

1. Run focused static playback/rail tests and Node harness.
2. Run `node --check` and `git diff --check`.
3. Review available/preparing/unavailable playback at compact and expanded rail.
4. Run the combined `ci-local.sh --fast` once at batch closeout.

## Project Structure

```text
specs/169-playback-rail-alignment/{spec,clarify,plan,research,data-model,quickstart,tasks}.md
specs/169-playback-rail-alignment/contracts/playback-rail-alignment.md
specs/169-playback-rail-alignment/checklists/{requirements,ux}.md
apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css
apps/server/tests/contract/test_cabinet_static_assets_contract.py
```

**Structure Decision**: Reuse the CSS variable and grid state already owned by
the cabinet shell; do not duplicate the playback component.

## Complexity Tracking

No violations. One paired CSS selector is the smallest root-cause fix.
