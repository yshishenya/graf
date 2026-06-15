# Reference Audit: Meeting Dashboard Review

Feature: `016-meeting-dashboard-review`
Created: 2026-06-16

This file records design and product references used before planning and
implementation. Evidence must stay metadata-only. Do not store secrets,
credentials, raw customer transcript text, signed URLs, tokens, passwords,
live local paths from real users, or private meeting content.

## Sources To Inspect

- V8 final candidate in `specs/030-mvp-experience-design-system/design/`.
- Active Figma file `ylPz3AxOOfVoLJEG4dF9Yr`, page `030 MVP Experience v8 - Clean RU`.
- Existing saved Krisp reference screenshots under
  `specs/030-mvp-experience-design-system/design/reviews/v8-clean-ru-2026-06-15/krisp-reference-pass/`.
- Live Crisp/Krisp web surfaces where accessible without transmitting
  sensitive data.
- Installed Crisp/Krisp desktop app surfaces where accessible without account
  creation, purchase, permission changes, or sensitive-data transmission.
- Current 2brain Rec macOS app and server capabilities.

## Capture Directory

Screenshots and generated contact sheets for this feature should be saved under:

```text
specs/016-meeting-dashboard-review/research/reference-captures/
```

## Audit Log

| Time | Source | Surface | Actions clicked / inspected | Screenshot(s) | Notes |
|---|---|---|---|---|---|
| 2026-06-16 | repo | kickoff | Created audit log and capture directory | n/a | Awaiting V8, Figma, and live reference captures |
| 2026-06-16 | Krisp public web | AI Note Taker landing and mobile/product menu | Opened landing, hamburger menu, AI Meeting Assistant submenu | `live-krisp-ai-note-taker-viewport.png`, `live-krisp-ai-note-taker-menu-open.png`, `live-krisp-ai-note-taker-ai-submenu-open.png` | Public IA separates meeting assistant, note-taking, transcription, recording, summary, and realtime voice features; useful for scope boundaries, not a product UI substitute |
| 2026-06-16 | user-provided Krisp appshots | Authenticated macOS app and embedded meeting cabinet | Reviewed meeting list, row actions, notes/detail, transcript, playback timeline, share modal, template menu, meeting controls, and screen-recording picker from appshots | appshot PNGs provided in chat; files not found on disk during capture search | Sanitized structural notes saved in `research/notes/krisp-app-reference-2026-06-16.md`; private meeting text and account identity intentionally omitted |
| 2026-06-16 | repo | desktop capture planning | Added remaining desktop screenshot checklist and raw-appshot handling note | `research/desktop-screenshot-checklist.md` | Raw authenticated screenshots should be redacted before saving into tracked `specs/` artifacts |
| 2026-06-16 | user-provided Krisp appshots | Meeting-list utility overlays and pending detail | Reviewed search command palette, filter menu, sort menu, `New` menu, and in-progress meeting detail state from appshots | appshot PNGs provided in chat; files not found on disk during capture search | Checklist updated; product lessons added to `research/notes/krisp-app-reference-2026-06-16.md` |
| 2026-06-16 | authenticated Krisp web in Chrome | Web cabinet list, detail, transcript, settings, and governance surfaces | Claimed the already-open `app.krisp.ai` tab, clicked list `New`, filters, sort, row hover/more, search, processing detail, processed notes, share/role controls, template menu, language control, transcript, speed menu, shared list, action items, contacts, settings account, AI Note Taker, privacy/consent, and invite teammates | Private raw captures only: `/Users/yshishenya/.codex/private-reference-captures/2brain-rec/016-meeting-dashboard-review/2026-06-16/manifest.json` | Authenticated web confirms the desktop-embedded cabinet structure. Raw screenshots include private account, contact, transcript, and meeting data and must not be committed. |

## Authenticated Web Findings

- The authenticated web cabinet is structurally the same product surface as the
  desktop-embedded cabinet for meeting list, meeting detail, notes, transcript,
  search, filters, sorting, sharing, templates, action items, contacts, and
  settings. This supports a web-owned post-meeting surface embedded by desktop.
- The web `New` action in the observed account exposed `Upload file`; the
  desktop appshots also exposed `Record live`. For 2brain Rec, 016 should
  reserve a `New` entry point but keep live capture execution in accepted
  capture/upload slices and native desktop shell behavior.
- Processing detail showed an honest waiting state for a newly recorded meeting
  instead of fake transcript or notes content. This must be represented as a
  first-class 016 state.
- Processed meeting detail used a stable `Notes` / `Recording & Transcript`
  information architecture with timestamp links, action items, speaker labels,
  transcript feedback, playback transport, timeline lanes, speed selection, and
  speaker talk-time percentages.
- Share and invite controls are present but policy-sensitive. Role options
  include edit/comment/view/summary-like access; account/team invite in the
  observed trial state opens a team-trial boundary. 016 may reserve these
  locations, but must not execute external sharing or team/billing workflows.
- Settings contain the real governance homes for AI note-taking behavior,
  templates, auto-share/default link permissions, privacy/consent, auto-delete,
  integrations, tags, language, action items, and app behavior. 016 should
  link or reserve these concepts only when needed, not reimplement settings.
