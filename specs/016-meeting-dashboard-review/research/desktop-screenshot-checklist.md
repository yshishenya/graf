# Desktop Reference Screenshot Checklist

Feature: `016-meeting-dashboard-review`
Date: 2026-06-16

This checklist tracks remaining Krisp desktop/web-cabinet screenshots needed
for clean-room product analysis. Before saving screenshots in the repository,
redact private meeting titles, participant names, email addresses, transcript
content, share links, and account identifiers.

## Already Covered By User Appshots

- [x] Active Krisp desktop shell with embedded meeting cabinet.
- [x] Active audio recording state.
- [x] Active screen recording state.
- [x] Screen/window picker for screen recording.
- [x] Meeting list with upcoming meetings and dense history rows.
- [x] Row hover actions: star, save later, collaborative/private marker, tag,
  and more menu.
- [x] Row more menu with mark-unread/delete meeting actions.
- [x] Meeting detail with `Notes` and `Recording & Transcript` tabs.
- [x] Notes view with key points/action items and timestamp links.
- [x] Transcript view with speaker labels, timestamps, playback, and bottom
  speaker lanes.
- [x] Summary/template menu.
- [x] Share modal with invite, link access, role, owner row, and copy link.
- [x] Meeting-scoped assistant panel and scope selector.
- [x] Right-side meeting controls panel: note taker, recording mode, accent,
  noise, and Krisp devices.
- [x] Search screen/overlay after clicking `Search`.
- [x] Filter popover from the meeting list.
- [x] Sort menu from the meeting list.
- [x] `New` meeting/recording/upload action menu.
- [x] Processing/in-progress meeting detail state.

## Highest-Value Missing Screens

- [x] Authenticated web version in browser at `app.krisp.ai`, especially
  whether it matches the embedded desktop cabinet for post-meeting surfaces.
- [ ] `Shared with me` list and one shared meeting detail.
- [x] `Shared with me` list state.
- [x] `Action Items` list, due-date control, assignee control, and completion
  state.
- [x] `Contacts` page table state.
- [ ] Speaker/contact mapping flow.
- [x] `Settings` sections, especially account, AI note taker, privacy/consent,
  recording/transcription policy, integrations, language, and devices.
- [x] Invite teammates modal / team-trial boundary.
- [ ] User/account/workspace switcher menu.
- [ ] Meeting detail `more` menu and delete confirmation boundary copy.
- [x] Share modal role dropdown options.
- [ ] Share modal link-access dropdown options.
- [ ] Speaker assignment flow after clicking `Assign speakers`.
- [ ] Language selector menu, especially RU/transcript-language behavior
  (button captured; option list was not confirmed).
- [ ] Locked/trial/upgrade state for unavailable features if available.
- [ ] Empty state if a filter/search returns no meetings.
- [ ] Error/offline state if visible without disrupting the account.

## Private Authenticated Chrome Captures

Raw authenticated web screenshots were saved outside git at:

```text
/Users/yshishenya/.codex/private-reference-captures/2brain-rec/016-meeting-dashboard-review/2026-06-16/
```

The private folder contains `manifest.json` and 23 PNG captures for the list,
menus, row actions, search, processing detail, processed notes, share controls,
templates, transcript/timeline, speed menu, shared list, action items,
contacts, settings, privacy/consent, and invite/team-trial boundary. These raw
files contain private account/contact/transcript data and must not be committed.

## Why Raw Appshots Are Not Saved Here Yet

The user-provided appshots arrived in chat as appshot attachments. A local
filesystem search for the referenced filenames did not find corresponding PNG
files under `/Users/yshishenya`. The raw screenshots also contain private
meeting content and account identity, so they should not be committed under
`specs/`.

Preferred options:

- Save redacted screenshots into
  `specs/016-meeting-dashboard-review/research/reference-captures/`.
- Keep raw private screenshots outside git and reference them only in local
  notes.
- Use sanitized structural notes in tracked Spec Kit artifacts.
