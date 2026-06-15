# Route Visibility Matrix

Source of truth: `mvp-experience-blueprint.md`.

## Route Classes

- `native`: rendered only by the macOS app.
- `embedded`: server-rendered web cabinet route allowed inside the desktop app.
- `browser`: full browser web cabinet route.
- `handoff`: shown in desktop only as an "open in browser" marker.
- `hidden`: not visible in desktop navigation.
- `deferred`: not part of MVP implementation, but route slot is reserved.

## Desktop Native Routes

| Route | Class | Owner | First-launch requirement |
|---|---|---|---|
| Native capture strip | native | macOS | Required in every desktop window state. |
| Native active recording | native | macOS | Required; pinned above all server content. |
| Native stop control | native | macOS | Required; one-action and never web-owned. |
| Native permission recovery | native | macOS | Required. |
| Native upload queue truth | native | macOS | Required; mirrors server only after confirmed. |
| Native tray/menu mini controller | native | macOS | Required for active capture and latest status. |
| Native diagnostics | native | macOS | Secondary/recovery route, not first viewport. |

## Embedded Desktop Cabinet Routes

| Route | Desktop | Browser | Notes |
|---|---|---|---|
| `/desktop/meetings` | embedded | browser equivalent `/meetings` | Default desktop home; shows cabinet list. |
| `/desktop/meetings/:id` | embedded | browser equivalent `/meetings/:id` | Meeting review allowed, capture strip remains native. |
| `/desktop/meetings/:id/speakers` | embedded | browser equivalent `/meetings/:id/speakers` | Speaker naming, merge, and assignment are server-owned web UI loaded inside desktop; capture strip remains native. |
| `/desktop/upload` | embedded | browser equivalent `/upload` | Manual upload allowed; desktop-safe copy. |
| `/desktop/processing/:id` | embedded | browser equivalent `/meetings/:id/status` | Same stage names as browser. |
| `/desktop/account` | embedded | browser equivalent `/settings/account` | Basic account/session only. |
| `/desktop/workspace-policy` | embedded | browser equivalent `/workspace/policy` | Summary only; editing is browser handoff. |
| `/desktop/settings/basic` | embedded | browser equivalent `/settings` | Theme/language/session basics. |
| `/desktop/deletion/:id` | embedded | browser equivalent `/meetings/:id/delete` | Entry and truth summary; full reports browser-only. |

## Browser-Only Routes

| Route | Desktop behavior | Browser behavior | Reason |
|---|---|---|---|
| `/workspace/team` | handoff | browser | Team admin not needed in recorder app. |
| `/workspace/billing` | handoff | browser | Billing is not capture workflow. |
| `/workspace/audit` | handoff | browser | Detailed audit is broad governance. |
| `/activity` | hidden/handoff | browser/deferred | Notification center is not launch-critical desktop UI. |
| `/contacts` | hidden/handoff | browser/deferred | Contacts management is not recorder-first. |
| `/action-items` | hidden/handoff | browser/deferred | Global action-items center is later; meeting-level action items stay in review. |
| `/sharing` | handoff/deferred | browser/deferred | Public sharing is later than owner value loop. |
| `/downloads` | handoff/deferred | browser/deferred | Export management is later refinement. |
| `/deletion-reports` | handoff | browser | Full reports are browser governance. |
| `/integrations` | hidden/handoff | browser/deferred | Marketplace/external integrations are not MVP desktop. |
| `/help` | handoff | browser | Browser documentation. |
| `/legal` | hidden/handoff | browser | Browser documentation. |
| `/developers` | hidden/handoff | browser | Not part of owner MVP loop. |

## Navigation Visibility

### Desktop Embedded Sidebar

Visible:

- `Встречи`
- `Обзор`
- `Настройки`
- `Помощь`

Desktop sidebar must stay short and stable. Upload, processing, speaker
assignment, account, policy, access, export, and deletion are not first-level
desktop destinations. They appear as meeting-row actions, status tabs, sheets,
detail routes, settings sections, or browser handoffs.

Footer:

- `Открыть веб-кабинет`
- Sync/account state in user language. Do not show backend/service/debug labels
  such as API, worker, route, native layer, server route, or raw hostnames in
  normal product navigation.

Allowed in desktop meeting detail:

- Transcript read.
- Playback if audio is available and policy allows it.
- Source/status provenance.
- Meeting-level summary/actions when ready.
- Speaker assignment, naming, merge, and talk-time review as an embedded
  server-owned web panel. The desktop app hosts it but does not implement
  diarization or speaker editing natively.
- Handoff to browser for share/export/delete.

Desktop saved views:

- `Все`
- `Нужна проверка`
- `В работе`
- `Только на этом Mac`
- `Ошибка`

Hidden or handoff:

- Team
- Billing
- Audit
- Sharing
- Downloads
- Global action items
- Contacts
- Activity
- Integrations
- Help
- Legal
- Developers
- Transcript find/replace
- Transcript language regeneration
- Public-link access changes

### Browser Sidebar

Visible:

- `Встречи`
- `Обзор`
- `Доступ`
- `Рабочее пространство`
- `Журнал`
- `Настройки`

Browser upload is available from the meetings header, empty state, row action,
and drag/drop sheet. Processing is visible as meeting-row/detail status and
filter state, not as a separate primary navigation item.

Secondary or later:

- Team
- Billing
- Sharing
- Downloads
- Deletion reports
- Help
- Legal
- Developers
- Integrations
- Global activity center
- Global action-items center
- Contacts management

Browser-only review actions:

- Public-link or workspace/team access changes.
- Export transcript and download audio when policy allows.
- Delete meeting and deletion reports.
- Transcript find/replace.
- Language regeneration.
- AI across all meetings.

## Boundary Tests

- Active recording remains visible after navigating to every embedded route.
- Desktop deep links to browser-only routes show a handoff state, not an error
  page and not a hidden full admin UI.
- A server-rendered route cannot show a primary stop button.
- The desktop app remains usable when the embedded cabinet is slow, signed out,
  or unavailable.
- Empty filter chips are not visible in desktop or browser.
- Desktop can change speaker names/merges/assignment only through the
  allowlisted embedded web route backed by server state. Native macOS code must
  not own this logic.
- Desktop cannot change share access level, public link policy, billing,
  workspace admin policy, language regeneration, or delete without browser
  handoff or explicit future spec.
- Upload and processing must remain visible in desktop and browser as meeting
  states/actions, not as permanent top-level desktop navigation.
- Embedded product UI must not expose implementation labels such as `native`,
  `server route`, backend service names, or internal URLs in the first
  viewport. Those details belong in diagnostics, audit, or developer docs.
