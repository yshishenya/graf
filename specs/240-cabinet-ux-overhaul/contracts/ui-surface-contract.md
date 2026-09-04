# UI Surface Contract

## Functional no-change boundary

The redesign may change presentation-only CSS rules, layout wrappers when their
semantics stay equivalent, and localized visual grouping. It MUST preserve:

- route paths, form actions, HTTP methods, CSRF fields and hidden functional
  inputs;
- HTMX `data-hx-*` targets, selects, swaps, triggers, sync and history behavior;
- `data-*` hooks consumed by `cabinet.js`, native WebKit bridge and tests;
- IDs and relationships used by tabs, dialogs, live regions and focus return;
- recording/upload/processing/delete/share/export/auth/privacy/deletion behavior.

## Surface matrix

| Surface | States | Reference comparison | Evidence |
|---|---|---|---|
| Meetings list | ready, empty, filtered, upload activity, error | toolbar, row density, primary upload action | screenshot + DOM + focused tests |
| Meeting detail | ready, processing, partial, failed, unavailable | header hierarchy, tabs, playback, recovery | screenshot + a11y + detail tests |
| Settings | overview, recording, calendar, summaries, workspace, account, notifications | section grouping and left navigation | screenshot + IA integration tests |
| Profile menu | closed, open, submenu, disabled actions | compact account/action grouping | screenshot + keyboard contract |
| Billing/shared | ready, empty, blocked, error | cards, hierarchy, safe notices | screenshot + existing contract tests |
| Auth | login, code, signup, referral, error | centered auth task and legal hierarchy | screenshot + auth tests |

## Review rules

- A deliberate deviation from Krisp must name the reason: accessibility,
  localization, privacy, deletion truth, GRAF product truth or known reference
  defect.
- A legacy deletion must cite search evidence and be presentation-only.
- A finding is closed only when the after-state screenshot/DOM/test evidence and
  no-change functional check agree.
