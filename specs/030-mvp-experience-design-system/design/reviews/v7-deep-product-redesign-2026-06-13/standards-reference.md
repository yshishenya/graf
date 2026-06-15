# V7/V8 Standards Reference

This file records the design standards used for the v7 rebuild. These are
constraints for the prototype and later implementation, not decorative
inspiration. Source links were rechecked on 2026-06-13.

V8 addendum source links were rechecked on 2026-06-15 after the stakeholder
requested another pixel-level pass against modern desktop/web UI conventions.

## macOS Native Shell

Sources:

- Apple HIG, Toolbars:
  <https://developer.apple.com/design/human-interface-guidelines/toolbars>
- Apple HIG, Menu bar:
  <https://developer.apple.com/design/Human-Interface-Guidelines/the-menu-bar>
- Apple HIG, Search fields:
  <https://developer.apple.com/design/human-interface-guidelines/search-fields>
- Apple HIG, Buttons:
  <https://developer.apple.com/design/human-interface-guidelines/buttons>
- Apple HIG, Segmented controls:
  <https://developer.apple.com/design/human-interface-guidelines/segmented-controls>
- Apple HIG, Toggles:
  <https://developer.apple.com/design/human-interface-guidelines/toggles>

Rules for v7:

- Toolbar controls are grouped by task: capture, workspace navigation,
  account/sync, and view actions. Do not scatter unrelated CTAs across the top.
- Search uses a real search-field pattern with placeholder, clear affordance,
  keyboard focus, and results in the current workspace.
- Menu bar exposes persistent state and fast actions, not a duplicate full
  product UI.
- Active recording is a shell state: menu bar item + toolbar strip + popover,
  with Stop always visible.
- Buttons must represent commands, not status labels. Status belongs in badges,
  rows, tooltips, or helper text.
- Segmented controls are used only for mutually exclusive choices such as
  theme or recording policy; they are not used as page navigation.
- Toggles represent immediate on/off preferences. High-risk policy choices use
  radio/segmented options plus explanatory text.

## Web Cabinet / Data Workspace

Sources:

- NN/g, Data Tables: Four Major User Tasks:
  <https://www.nngroup.com/articles/data-tables/>
- NN/g, Defining Helpful Filter Categories and Values:
  <https://www.nngroup.com/articles/filter-categories-values/>
- NN/g, User Intent Affects Filter Design:
  <https://www.nngroup.com/articles/applying-filters/>
- Material 3, Top app bar:
  <https://m3.material.io/components/app-bars/overview>
- Material 3, Navigation drawer:
  <https://m3.material.io/components/navigation-drawer/overview>
- Fluent 2, Layout:
  <https://fluent2.microsoft.design/layout>
- Fluent 2, Navigation:
  <https://fluent2.microsoft.design/components/web/react/nav/usage>
- Fluent 2, Button:
  <https://fluent2.microsoft.design/components/web/react/button/usage>
- Fluent 2, Input:
  <https://fluent2.microsoft.design/components/web/react/input/usage>

Rules for v7:

- Meeting list must support finding records, comparing records, opening one
  record, and acting on records.
- Prefer dense list/table structure over card grids for the main meeting
  library because the user must compare title, date/time, duration, source,
  status, and next action across many meetings.
- The first meaningful column must be a human-readable meeting title/source,
  not an internal id or hidden implementation key.
- Adjacent columns must follow task relevance: title/source, date/time,
  duration, status, owner/participants, next action.
- Search and filters remain on the meeting-list surface; they are not separate
  primary navigation destinations.
- Filter categories must be predictable and user-language first: status, date,
  source, participant, tag, access, owner.
- Active filter chips appear only when a value exists.
- Primary upload action belongs in the top bar/list context and opens a drawer
  or sheet; it should not become an unrelated app section.
- Settings use a list-detail structure with a stable left rail and focused
  detail pane. Account/admin/security routes hand off to browser when they
  require broad policy, credentials, billing, team, or destructive actions.
- Meeting list row actions must stay aligned to the same column grid across
  ready, uploading, processing, failed, and deleted states.
- Empty space in the first viewport must be explained by information hierarchy,
  not by decorative cards. Dense operational tools should prioritize scan,
  compare, and act.

## Accessibility And Status Truth

Sources:

- WCAG 2.2 target size minimum:
  <https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html>
- WCAG 2.2:
  <https://www.w3.org/TR/WCAG22/>

Rules for v7:

- Pointer targets must be at least 24 x 24 px; product controls should use
  32 px compact, 36 px standard, and 40 px primary/action heights.
- Keyboard focus must be visible and not hidden by sticky strips, drawers, or
  menu-bar popovers.
- Status messages such as upload accepted, transcription started, transcript
  ready, save failed, or offline queue updated must be exposed as status
  messages in implementation.
- Color is never the only status cue: status text plus icon/shape is required.

## V7 Token Rules

- Icon-only toolbar controls: 32 x 32.
- Compact table row actions: 32 px high.
- Standard buttons: 36 px high.
- Primary/destructive form actions: 40 px high.
- Corner radius: 6 px for buttons/chips/fields, 8 px max for panels unless a
  native macOS component dictates otherwise.
- Page gutters: 24 px desktop web, 20 px embedded desktop.
- Dense meeting rows: 56-64 px depending on secondary metadata.
- Empty-state cards are only allowed when there is genuinely no data; normal
  dashboard white space must be filled with useful list/status/review content.
