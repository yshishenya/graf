# Clean-Room Krisp Observation

## Observation Method

Krisp is installed and running locally as `krisp.app` version `3.12.5`, bundle id `ai.krisp.krispMac`. Runtime metadata shows Electron renderer windows named `MAIN`, `WEB`, `WEB_OVERLAY`, `DESKTOP_REPORT_WINDOW`, `NOTIFICATION_INDICATOR`, `NOTIFICATION_REMINDER`, and `CONFIRMATION_WINDOW`, plus `KrispAudio.driver` in Core Audio.

The web cabinet reference URL was opened in the user's current browser:

`https://app.krisp.ai/meeting-notes?dates=&companies=&contains=&tags=&includeMeetingIds=&participatedContactIds=&access=&sort=desc&sortKey=created_at&page=1&limit=50&starred=null&type=&listen_later=null&isOwner=true`

The installed desktop app was also inspected visually through accessibility
state. It embeds `desktop.krisp.ai/meeting-notes` inside the desktop app.

The detailed pre-redesign navigation and interaction audit is recorded in
`krisp-full-navigation-audit.md`. That file is the current evidence source for
specific safe clicks, menus, settings sections, meeting review behavior, and
risky actions intentionally not clicked.

No screenshots, copy, icons, assets, or proprietary UI details were copied into this repo.

## Observed Web Cabinet Structure

- Persistent cabinet navigation includes meeting search, personal meetings,
  shared meetings, action items, activity, contacts, and settings.
- Account identity, email, plan/trial state, app/developer links, and teammate
  invitation are part of the cabinet shell.
- Meeting notes support a filtered query model: date, company, text/content,
  tags, meeting ids, participant contacts, access, sort, starred, type,
  listen-later, owner scope, page, and limit.
- The page includes an AI-style query area scoped to the user's meetings.
- Past meetings remain visible even when a trial/account state blocks new
  meeting creation.
- Meeting detail includes transcript, playback, language correction, quality
  feedback, tags, share/access, export/download/delete actions, and scoped AI.
- Account/workspace/settings routes are broad and include many browser-only
  administration, policy, billing, integration, and security actions.

## Observed Desktop Structure

- Desktop Krisp combines local audio controls with an embedded meeting cabinet.
- Local controls are compact and stay separate from the meeting list.
- The embedded cabinet has its own meeting navigation and list rows.
- Meeting rows are dense and scannable, with title, duration, date/status
  metadata, and per-row actions.
- A compact account/plan state remains visible in the desktop shell.

## Category-Level Lessons Allowed

- Keep audio controls compact and close to system/tray behavior.
- Separate always-visible local trust state from richer web/account surfaces.
- Use small notification/reminder surfaces for important state, not broad dashboards.
- Put report/review surfaces outside the critical capture controls.
- Treat driver/audio-device behavior as a risk boundary, not a decorative UI detail.
- Put the user's meeting library inside the desktop app instead of forcing
  every post-meeting task into a browser.
- Use dense rows and contextual search for meeting notes; avoid oversized cards
  for repeat-workflow lists.
- Make account/workspace state visible without letting account web UI own local
  recording controls.
- Keep the first MVP loop focused on record/upload, processing status,
  transcript review, notes/actions, provenance, and safe handoff. Team trial,
  billing, admin policy, integrations, public sharing, and deletion reports are
  browser-only or deferred.

## Forbidden Elements

- Krisp visual expression, icons, screenshots, copy, brand colors, proprietary flows, model behavior, or file assets.
- Imitating Krisp's exact navigation, empty states, setting names, or window structure.
- Using actual observed private meeting names or user account data in 2brain Rec
  examples or prototypes.

## 2brain Rec Direction

2brain Rec should use the category logic of compact capture controls,
desktop-embedded cabinet value, meeting-review separation, and dense meeting
lists. It must express those patterns through an original quiet work-focused
design system: light-first cabinet, restrained native macOS capture strip,
green/cobalt/amber/red status roles, meaningful source/deletion truth, and no
copied Krisp UI expression.
