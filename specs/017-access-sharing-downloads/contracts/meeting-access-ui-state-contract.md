# Contract: Meeting Access UI States

Feature: `017-access-sharing-downloads`
Date: 2026-06-16

## Information Architecture

017 keeps the 016 cabinet structure:

- `My Meetings` list.
- Meeting detail with `Notes` and `Recording & Transcript`.
- Detail governance area.
- Desktop embedded variants under `/desktop/meetings`.

The feature activates previously planned governance affordances:

- access state chips on list and detail;
- share modal/drawer for login-required grants;
- download menu or panel for allowed artifacts;
- export package action;
- metadata-only activity/audit surface or evidence slot.

Activity surfaces must show only metadata-safe events such as share granted,
share revoked, link opened, view denied, download completed, and export
completed. They must not show transcript text, private artifact names, raw
tokens, storage keys, signed URLs, local paths, or dependency identifiers.

## Meeting List States

Rows visible to a viewer must show one safe access label:

- `Owner`;
- `Team`;
- `Shared`;
- no row at all for unauthorized meetings.

The list must support access filtering when data supports it:

- owner;
- team;
- shared.

Unauthorized meetings must not appear as locked rows because that confirms
private meeting existence.

## Detail Access States

| State | Required UI Truth |
|---|---|
| `owner` | User can view and, when role allows, manage sharing/download/export policy. |
| `team` | User can view through workspace/team visibility; UI must not imply public access. |
| `shared` | User can view through an explicit login-required grant. |
| `denied` | Show bounded denied/not-found state without private title, transcript, summary, participants, or artifact details. |
| `unavailable` | Explain safe lifecycle/policy class without revealing private content to unauthorized users. |
| `deleted` | Show truthful deleted/unavailable state; no 017 deletion execution. |

## Share Modal Or Drawer

Required controls:

- add authenticated user by account identifier or selected known user;
- show active grants;
- revoke active grant;
- copy login-required link;
- show team visibility state;
- show public links disabled by default.
- show metadata-only share activity when activity is available.

Required copy:

- share links require login;
- public links are disabled by default;
- revoking a grant removes future access but does not recall files already
  downloaded or exported.

Failure states:

- grantee not found or inactive;
- grantee already has owner/team/shared access;
- viewer lacks share permission;
- audit unavailable, action failed closed;
- workspace policy blocks team visibility.

## Download And Export States

Each artifact class shows one state:

- available;
- policy blocked;
- owner only;
- processing;
- missing;
- failed;
- deleted;
- audit unavailable.

The UI must hide or disable unavailable actions and show safe reasons. Direct
download URLs must not be shown as raw storage or signed dependency URLs.

Export package UI must show:

- included artifact classes;
- excluded artifact classes with safe policy/lifecycle reason;
- package status: requested, ready, failed, expired;
- deletion/egress truth copy.

## Desktop Embedded Behavior

Embedded routes may show the same access/share/download/export UI if viewport
space allows, but browser/server still owns decisions. Embedded routes must not
add native recording controls, hide the native capture indicator, or implement
artifact policy locally.

When the embedded viewport is too narrow:

- keep primary meeting content and access state visible;
- move share/download/export controls into a compact menu/panel;
- preserve keyboard focus and accessible names.

## Accessibility And Localization

- Russian labels must not overflow chips, rows, buttons, modal headers, or
  compact side panels.
- State meaning must not rely on color alone.
- Icon-only buttons need accessible names or tooltips.
- Modal/drawer focus must be contained while open.
- Denied states must be understandable without exposing private content.

## Clean-Room And Evidence Rules

Allowed from Krisp/Crisp references:

- the idea of dense meeting lists;
- toolbar actions;
- share modal category coverage;
- filter/sort states;
- transcript/detail/action split.

Not allowed:

- copied text;
- copied icons/assets;
- copied visual treatment;
- copied proprietary behavior;
- private customer screenshots or transcript data in committed fixtures.

Tracked validation screenshots must use synthetic data and must not contain real
email addresses, private transcripts, credentials, tokens, object keys, signed
URLs, raw local paths, or dependency identifiers.
