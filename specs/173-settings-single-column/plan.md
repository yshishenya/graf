# Implementation Plan: Одна колонка настроек без legacy gutter

**Branch**: `codex/173-settings-single-column` | **Date**: 2026-08-19 | **Spec**: [spec.md](spec.md)

## Summary

Завершить начатую Feature 159 миграцию к одной основной навигации: когда
cabinet shell уже показывает settings links во внешнем sidebar, не создавать
скрытый внутренний nav и не резервировать под него grid-column. Сохранить
поддерживаемый fallback macro для surfaces без outer settings mode. Исправление
ограничено существующими Jinja/CSS owners и focused contracts.

## Technical Context

**Language/Version**: Jinja templates, CSS, Python 3.13 pytest contracts

**Primary Dependencies**: Existing cabinet shell, `settings_mode`, settings
navigation macro and current CSS grid; no new dependency

**Storage**: N/A

**Testing**: Focused settings UI contract, cabinet web-shell test, template
render tests, `git diff --check`, in-app Browser and GRAF Dev visual review

**Risk / Validation Lane**: `high-risk-feature` — shared settings IA,
responsive composition and accessibility; auth/billing/capture behavior is
preserved rather than changed

**Release Gate**: `no deploy`; separate PR and later release train

**Target Platform**: Standalone web and embedded macOS cabinet settings

**Performance Goals**: Presentation-only; no request, script, listener or
runtime measurement added

**Constraints**: One navigation landmark in settings mode, standard main
padding, no reserved legacy gutter, existing routes/forms/fallback preserved

**Scale/Scope**: Settings overview, regular forms, calendar/provider fragments
and billing templates through one shared macro and two shared layout selectors

## Constitution Check

*GATE: Passed before Phase 0 and re-checked after Phase 1.*

- Capture-First MVP Integrity: PASS — no capture/audio path changes.
- Visible Consent and User Control: PASS — recording settings content and native
  handoff remain reachable and unchanged.
- Privacy/secret discipline: PASS — no data, network, logging or credentials.
- Deletion lifecycle: PASS — no persisted artifacts.
- Public macOS distribution: PASS — no package/signing/update work.
- Spec-driven delivery: PASS — full 173 sequence and focused evidence.
- UI/accessibility/brand-distance: PASS — one navigation landmark, predictable
  reading order, existing GRAF design and current screenshot evidence.

## Validation Plan

1. Change the current contracts so settings mode requires no hidden legacy nav,
   single-column content and preserved fallback navigation.
2. Make the shared navigation macro emit nothing only for `legacy_hidden=True`;
   keep ordinary rendering unchanged.
3. Collapse `.settings-page` and `.calendar-settings` to one content column in
   settings mode and remove explicit column-2 placement.
4. Run focused settings/shell/template checks and `git diff --check`.
5. Reload the existing settings flow in the in-app Browser; compare metrics
   against the measured before state (content x≈469, 220px+32px legacy offset).
6. Check one embedded settings surface in GRAF Dev, then correctness,
   accessibility, Product Design and Ponytail review.
7. Run `infra/scripts/ci-local.sh --fast` once at closeout because this changes a
   shared user-facing layout; no full CI until an exact release candidate.

## Project Structure

### Documentation

```text
specs/173-settings-single-column/
├── spec.md
├── clarify.md
├── plan.md
├── research.md
├── data-model.md
├── contracts/settings-single-column.md
├── checklists/requirements.md
├── checklists/ux.md
├── quickstart.md
└── tasks.md
```

### Source Code

```text
apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/settings_navigation.html
apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css
apps/server/tests/unit/test_cabinet_web_shell.py
apps/server/tests/contract/test_settings_ui_contract.py
apps/server/tests/integration/test_settings_ia_flow.py
apps/server/tests/integration/test_cabinet_meeting_list.py
CHANGELOG.md
```

**Structure Decision**: Reuse the shared macro and shared layout selectors.
Do not edit 21 callers, add another mode class or add JavaScript.

## Complexity Tracking

No constitution violation. Ponytail ceiling: one conditional at the existing
macro boundary plus one single-column CSS owner and focused contract updates.
