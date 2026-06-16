# Krisp App Reference Notes

Date: 2026-06-16
Source: user-provided Krisp macOS appshots from an authenticated account
Privacy note: the appshots included private meeting titles, account identity,
and transcript content. This note intentionally records structure and product
patterns only. Do not copy private meeting text, email addresses, tokens, or
share URLs into repo artifacts.

Addendum: authenticated Krisp web was also inspected in the user's already-open
Chrome session on 2026-06-16. Raw screenshots were saved in a private reference
directory outside git because they contain private account, contact, meeting,
and transcript data.

## Surfaces Observed

- Authenticated desktop app window with an embedded `desktop.krisp.ai` meeting
  product surface and a separate capture-control shell.
- Active meeting/recording header with visible elapsed time and
  `Audio Recording` / `Screen Recording` state.
- Persistent right-side `Meeting Controls` panel for live Krisp controls:
  note-taker mode, audio/screen recording mode, accent conversion, noise
  cancellation, and selected Krisp devices.
- Account/workspace left rail with plan, invite, search, meeting list, shared
  meetings, action items, activity, contacts, settings, apps/developer links,
  trial/reactivation, and account switcher.
- Meeting list with upcoming meetings, dense historical rows, status/type
  icons, row hover actions, tags, starred/save-later controls, private/shared
  indicators, row menu, sorting/filtering controls, and a `New` action.
- Meeting detail with meeting title/date, top action row, `Notes` and
  `Recording & Transcript` tabs, share/slack/comment/more actions, language
  control, and speaker assignment prompt.
- Notes view with structured key points and action items, timestamp links back
  to recording positions, editable rich-text blocks, block menu, and feedback
  chips.
- Transcript view with timestamped speaker turns, speaker color/emotion
  markers, inline segment hover actions, linked playback, bottom timeline,
  speaker distribution lanes, speed control, and `Assign speakers`.
- Meeting-scoped assistant panel with suggestions, context scope selector,
  input, and tag action.
- Summary/template menu with reusable meeting templates such as auto, outline,
  project sync, weekly team meeting, 1:1, client status update, training, sales
  call/demo, hiring, all hands, and meeting minutes.
- Share modal with invite-by-email, link access scope, permission role, owner
  row, link access dropdown, and copy-link action.
- Screen recording picker as a separate capture permission/selection flow with
  screen/window choices and `Record` / `Close`.
- Search command palette with a search input, `ESC`, recent meeting results,
  and `Search commands` shortcut hint.
- Meeting-list filters grouped by star, date, contains, company, type, and
  tags.
- Meeting-list sort menu grouped by sort key (`Date`, `Duration`,
  `Last modified`) and order (`Newest`, `Oldest`).
- `New` action menu with `Record live` and `Upload file`.
- In-progress meeting detail state that keeps meeting context and playback
  chrome visible while showing "transcript is on the way" instead of fake
  transcript/notes content.

## Authenticated Web Addendum

- The live web cabinet at `app.krisp.ai` matched the desktop-embedded product
  surface for meeting list, search, filters, sorting, processed detail, notes,
  transcript, share, template, action-items, contacts, and settings workflows.
- In the observed web account, `New` exposed upload only; the desktop appshots
  additionally exposed live recording. For 2brain Rec, treat `New` as a stable
  location while keeping live recording execution in capture/upload slices and
  native desktop shell flows.
- The role dropdown in share exposes several permission tiers, including
  edit/comment/view/summary-like access. This is useful information
  architecture, but 016 must not create public links or transmit share invites.
- AI Note Taker and Privacy/Consent settings are the real homes for auto-open,
  auto-summarize, templates, auto-share/default link permissions, consent,
  auto-delete, and app behavior. Meeting review should reserve or link to these
  concepts without changing policy.
- Contacts and Action Items are full secondary product areas. 016 should
  reserve action-item and speaker/contact affordances but avoid building a full
  task center or contact-management system inside the meeting review slice.

## Clean-Room Lessons For 2brain Rec

- The post-meeting product surface can be web-owned and embedded in desktop.
  Krisp appears to use a web cabinet route inside the macOS app while keeping
  live capture controls in a separate app shell.
- Meeting review should start from a useful meeting list, not a generic
  analytics dashboard. Upcoming meetings, processing/history rows, and row
  actions belong in one scanning surface.
- Detail needs a two-mode structure from the start: generated notes/outcomes and
  recording/transcript review. Even if 016 ships only read-only notes, the UI
  should reserve this tab model.
- Speaker assignment and speaker distribution need stable locations. 016 can
  initially display diarization labels and reserve correction actions without
  requiring full contact mapping.
- Share/export/delete controls should have stable positions but remain gated
  until 017/018 implement access, downloads, retention, deletion truth, and
  audit behavior.
- Meeting-scoped assistant and summary templates are future value surfaces.
  016 should reserve a compact location for them but must not introduce hidden
  transcript egress or untracked AI behavior.
- Search/filter/sort are lightweight list overlays, not separate destination
  pages. This keeps the meeting list as the default workspace while still
  making a large meeting archive navigable.
- `Record live` and `Upload file` can sit under a product `New` action, but in
  2brain Rec their execution belongs to accepted capture/upload slices. 016
  should reserve the entry point without implementing new capture behavior.
- Pending detail is a first-class state. Opening an in-progress meeting should
  be useful and honest even before transcript import completes.
- Desktop capture controls must not be implemented as ordinary web-dashboard
  buttons. Native capture state still needs visible local indicator and
  one-action stop, while the web surface owns post-meeting review.
- Screen recording is a separate permission/selection workflow. Do not fold it
  into 016 meeting review unless a future capture/screen-recording spec accepts
  that scope.

## Implications For 016

- Implement or reserve:
  - meeting list route;
  - meeting detail route;
  - processing/degraded/ready states;
  - pending meeting detail with "transcript not ready yet" truth;
  - list search, filter, and sort overlays;
  - notes/transcript tab model;
  - playback shell tied to timestamps;
  - speaker labels and speaker-correction entry point;
  - row-level future-action slots for star/tag/share/access;
  - meeting-scoped assistant/template slot as disabled or unavailable unless a
    later AI-notes/chat slice owns it;
  - share/export/delete entry points as stable gated actions.
- Do not implement in 016:
  - live recording controls in the web cabinet;
  - public link sharing;
  - real downloads/exports;
  - deletion execution;
  - summary-template generation;
  - meeting chat/assistant calls;
  - screen recording picker.
