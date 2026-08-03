# Implementation Plan: meeting-summary-ux

**Branch**: `codex/138-meeting-summary-ux` | **Date**: 2026-08-03 | **Spec**:
[spec.md](./spec.md)

## Summary

Упростить существующий server-rendered блок итогов до спокойного Notes-документа:
«Кратко», затем «Действия» и «Решения», затем один закрытый по умолчанию блок
«Дополнительные разделы». Выводить только сохранённые owner/due, оставить простые
source seek links и синхронизацию выбранной вкладки с URL hash.

## Technical Context

**Language/Version**: Python 3.11+, vanilla JavaScript, CSS, Jinja/server-rendered HTML

**Primary Dependencies**: FastAPI, existing cabinet rendering/view-models, local JS/CSS

**Storage**: без изменений; существующие MeetingOutcomeSet/MeetingOutcomeItem

**Testing**: focused pytest, synthetic browser runtime check, `git diff --check`,
`infra/scripts/ci-local.sh --fast`

**Risk / Validation Lane**: `high-risk-feature`; меняется user-facing AI/transcript
review UX и accessibility, но не меняются capture, auth, egress или schema.

**Release Gate**: `no deploy`; public macOS release и production deployment не
входят в slice.

**Constraints**: сохранить web/embedded parity, truth states, access/privacy
gates, candidate acceptance, bounded deletion copy и отсутствие private content
в committed evidence.

## Constitution Check

- PASS — macOS system-audio-first capture boundary не меняется.
- PASS — desktop/web summary не отправляет audio в MediaScribe и не хранит
  credentials; feature только отображает server-side view model.
- PASS — stored plaintext observability policy не меняется; evidence остаётся
  synthetic и metadata-only.
- PASS — blocked/partial states не подменяются optimistic content; deletion copy
  и access gates переиспользуются.
- PASS — clean-room GRAF styling переиспользует текущие tokens/components, без
  новой библиотеки или копирования competitor UI.

## Design and Implementation

1. `rendering.py`: единый outcome renderer с простой последовательностью primary
   sections и native `<details>` для пяти вторичных категорий. Conditional
   owner/due, semantic timestamp buttons и bounded state copy сохраняются.
   Сохраняются все восемь data attributes и source-basis contract.
2. `cabinet.css`: документная иерархия с разделителями вместо сетки карточек;
   повторяющиеся chips, пустые placeholders и inline export CTA не добавляются.
   Длинный текст переносится, fixed player получает безопасный content spacing.
3. `cabinet.js`: detail tab activation обновляет `#outcomes`/`#recording`; source
   buttons reuse `data-seek-seconds`; существующий meeting export flow не меняется.
4. Focused tests: markup/metadata/state safety, web/embedded parity, source
   controls, URL/tab runtime, mobile overflow. Existing outcome tests remain
   regression anchors.

## Project Structure

```text
specs/138-meeting-summary-ux/
├── spec.md
├── clarifications.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/meeting-summary-ui.md
├── checklists/ux.md
├── checklists/security.md
└── evidence/summary-runtime-check.cjs

apps/server/src/twobrain_rec_server/cabinet/
├── rendering.py
└── static/cabinet/{cabinet.css,cabinet.js}

apps/server/tests/
├── unit/test_cabinet_web_shell.py
└── integration/test_cabinet_meeting_outcomes.py
```

## Complexity Tracking

No constitution violations. Skipped new data model, API, dependency, task
integration, client-side framework and redesign of transcript/player because the
existing primitives cover this P0.
