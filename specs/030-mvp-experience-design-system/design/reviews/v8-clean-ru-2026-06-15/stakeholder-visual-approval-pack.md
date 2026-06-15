# V8 Stakeholder Visual Approval Pack

Date: 2026-06-15
Feature: `030-mvp-experience-design-system`
Figma file: <https://www.figma.com/design/ylPz3AxOOfVoLJEG4dF9Yr>
Active page: `030 MVP Experience v8 - Clean RU` (`341:2`)

## Approval Scope

This pack is the human visual review script for V8. It does not replace the
machine QA, five-critic audit, or Spec Kit artifacts. It turns them into a
screen-by-screen acceptance checklist for stakeholder review.

Approve V8 only if these gates hold while viewing the actual Figma canvas and
prototype:

- Controls feel consistently sized in context: primary actions `40px`, compact
  row actions `36px`, chips `28px`.
- The owner value loop is understandable without explanation: sign in, grant
  permissions, record or upload, watch processing, open transcript, correct
  speakers, share/export/delete in the web cabinet.
- Technical implementation language is absent from user-facing UI.
- The desktop app feels like a native capture shell; variable review/account UI
  feels cabinet/web-owned and portable across future platforms.
- The design feels calm, modern, dense enough for daily work, and not like a
  marketing page or test-data board.

## Click-Through Script

Use the Figma prototype on the active V8 page and follow this route:

1. `V8 01` sign in with any provider.
2. `V8 02` click `Проверить снова`.
3. `V8 03` click `Начать запись`.
4. `V8 05` click any `Остановить`.
5. `V8 06` click a ready row `Открыть`.
6. `V8 07` click `Назначить спикеров`.
7. `V8 08` click `Сохранить`.
8. `V8 07` click the more/share path to governance.
9. `V8 12` click `Оставить встречу`.
10. `V8 11` click `Уточнить спикеров`.
11. Return to `V8 10`, click search or the search field, and verify `V8 16`.
12. In `V8 16`, click a result `Открыть` and verify it opens meeting detail.
13. Return to `V8 10`, click `Загрузить медиа`, and verify `V8 15`.
14. In `V8 15`, click `Начать загрузку` and verify `V8 06`.
15. Return to settings through desktop/web navigation and click `Светлая`.
16. `V8 13` verify that the light theme keeps the same product semantics.

Expected result: all transitions stay inside visible V8 frames, no dead ends,
no self-links, and no jump to superseded pages.

## Screen Review Table

| Frame | Direct link | Must approve | Reject if |
|---|---|---|---|
| `V8 00` flow map | <https://www.figma.com/design/ylPz3AxOOfVoLJEG4dF9Yr?node-id=341-3> | MVP flow and surface boundaries are understandable | It feels like internal architecture instead of product rules |
| `V8 01` sign in | <https://www.figma.com/design/ylPz3AxOOfVoLJEG4dF9Yr?node-id=341-6> | Window is compact, provider-first, and does not promote local bypass | Login still feels oversized, vague, or missing expected providers |
| `V8 02` permissions | <https://www.figma.com/design/ylPz3AxOOfVoLJEG4dF9Yr?node-id=341-9> | First-open path explains what to allow and where | User would not know why this screen appears or what to click |
| `V8 03` desktop workspace | <https://www.figma.com/design/ylPz3AxOOfVoLJEG4dF9Yr?node-id=341-12> | Daily cockpit shows meetings, dates, status, recording, upload | It feels sparse, dashboard-like, or missing meeting context |
| `V8 04` detected prompt | <https://www.figma.com/design/ylPz3AxOOfVoLJEG4dF9Yr?node-id=341-15> | Meeting detection asks clearly and references the policy | Prompt feels intrusive, unclear, or disconnected from settings |
| `V8 05` active recording | <https://www.figma.com/design/ylPz3AxOOfVoLJEG4dF9Yr?node-id=341-18> | Recording lives in menu/header chrome with one-action Stop | It still feels like a separate destination or hides Stop |
| `V8 06` upload/processing | <https://www.figma.com/design/ylPz3AxOOfVoLJEG4dF9Yr?node-id=341-21> | Upload and transcription are concrete row/status states | It feels like a standalone upload product area |
| `V8 07` transcript review | <https://www.figma.com/design/ylPz3AxOOfVoLJEG4dF9Yr?node-id=341-24> | Transcript, playback, outcomes, and speaker action coexist cleanly | Review feels cramped, empty, or action hierarchy is confusing |
| `V8 08` speaker lanes | <https://www.figma.com/design/ylPz3AxOOfVoLJEG4dF9Yr?node-id=341-27> | Each speaker has a separate lane and correction action | Speaker assignment feels secondary or merged into one track |
| `V8 09` settings | <https://www.figma.com/design/ylPz3AxOOfVoLJEG4dF9Yr?node-id=341-30> | Recording policy, app detection, sources, theme, language, and handoff are clear | Settings feel shallow, technical, or missing dark/light controls |
| `V8 10` web list | <https://www.figma.com/design/ylPz3AxOOfVoLJEG4dF9Yr?node-id=341-33> | Search/filter/upload/status/date/action live on one useful list | It feels like separate search/filter screens are still needed |
| `V8 11` web detail | <https://www.figma.com/design/ylPz3AxOOfVoLJEG4dF9Yr?node-id=341-36> | Web review supports transcript, outcomes, speaker action, share/export | Detail feels less capable than desktop review |
| `V8 12` governance | <https://www.figma.com/design/ylPz3AxOOfVoLJEG4dF9Yr?node-id=341-39> | Share/export/delete are understandable and deletion copy is bounded | It overpromises deletion or hides risky actions |
| `V8 13` light proof | <https://www.figma.com/design/ylPz3AxOOfVoLJEG4dF9Yr?node-id=341-42> | Light theme preserves density, hierarchy, and statuses | Theme switch changes the product model or hurts readability |
| `V8 14` QA rules | <https://www.figma.com/design/ylPz3AxOOfVoLJEG4dF9Yr?node-id=341-45> | Component/ownership rules are clear enough for implementation | Rules are too abstract to guide frontend/native work |
| `V8 15` shared upload sheet | <https://www.figma.com/design/ylPz3AxOOfVoLJEG4dF9Yr?node-id=462-2> | Upload feels like one shared desktop/web meeting action with metadata, validation, and processing handoff | It feels native-only, file-dump-like, or detached from the meeting list |
| `V8 16` search/filter overlay | <https://www.figma.com/design/ylPz3AxOOfVoLJEG4dF9Yr?node-id=463-2> | Search and filters feel like a fast contextual layer over `Встречи` | It feels like a separate route, cramped modal, or unclear command surface |

## Review Decision Template

Use this exact outcome when review is done:

```text
V8 stakeholder visual approval: approved / changes required
Date:
Reviewer:

Approved screens:

Screens needing changes:

Blocking issues:

Non-blocking polish:

Decision:
```

## Current Evidence

- Machine QA: `figma-v8-qa.md`.
- Five-critic screen audit: `five-critic-screen-audit.md`.
- Clickable path evidence: `../../prototype/clickable-paths.md`.
- Readiness scorecard: `../../reviewer-readiness-scorecard.md`.

## Current Open Gate

Stakeholder visual approval is still pending. Do not mark feature `030` ready
for implementation handoff until the decision template above is filled with an
approved result or the requested changes are addressed and rechecked.
