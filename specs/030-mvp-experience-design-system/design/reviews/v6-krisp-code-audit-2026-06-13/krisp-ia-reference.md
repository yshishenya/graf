# Krisp IA Reference For V6

This is clean-room category learning only. Do not copy Krisp branding, exact
visual layout, text, icons, assets, colors, proprietary behavior, or private
meeting content.

## Web Cabinet Patterns

Krisp web is organized around a persistent meeting cabinet rather than a
diagnostic dashboard.

Observed route groups:

| Area | Product lesson for 2brain Rec |
|---|---|
| Meeting notes/list | Dense rows, status-rich history, upcoming section, search/filter/sort controls, and a bottom AI prompt can coexist without card bloat. |
| Meeting detail | The transcript is the primary document. Playback, language/source controls, share, comments, more menu, and AI stay close to the review context. |
| Speaker assignment | The bottom review timeline uses separate horizontal lanes per speaker with colored segments and talk-time percentages. Assignment is a review control, not a detached admin form. |
| Action items | A global action-item center can be plan-gated/later; meeting-local actions still matter inside review. |
| Settings | Account, AI note-taker behavior, app appearance, notifications, personalization, integrations, and users are separate sections. They should not crowd the desktop first viewport. |
| Integrations | Marketplace/grid belongs to full browser web, not launch desktop. |

## Desktop Patterns

Krisp desktop still opens on the user's meeting library. Local audio controls
are compact and secondary to the recorder/library loop.

Observed desktop regions:

| Region | Product lesson for 2brain Rec |
|---|---|
| Left navigation | Stable cabinet IA works in desktop too: meetings, shared, action items, activity, contacts, settings. 2brain Rec should launch with a smaller subset. |
| Center content | Meeting list and status remain the main workspace, not diagnostics. |
| Right local controls | Device/audio controls can be compact rails. 2brain Rec should map this to capture trust: source, meters, Record/Stop, upload state, policy. |
| Account/trial state | Account status can be visible without becoming the main UI. |

## Required 2brain Rec Interpretation

The MVP must satisfy individuals and SMBs:

- Individuals need immediate clarity: record, upload, see processing, open the
  transcript, fix speakers, export/share safely later.
- SMB users need trust and consistency: same statuses in app and web, account
  state, deletion truth, permissions, and browser-owned admin/settings.
- Both audiences benefit from dense, readable lists and review workspaces.
  Oversized marketing cards and raw diagnostics are wrong for the daily loop.

## V6 IA Shape

Desktop first viewport:

1. Native capture strip: status, source, elapsed time when active, Record/Stop,
   local save/upload truth.
2. Embedded server cabinet: meetings list by default, with upload and review
   routes allowed.
3. Compact account/policy status in toolbar, not a large setup card.
4. Diagnostics and driver details hidden behind recovery/settings.

Browser first viewport:

1. Meeting library with dense rows, status filters, upcoming, upload action,
   and scoped search.
2. Manual upload with metadata and validation.
3. Processing status with staged progress.
4. Review workspace: transcript, playback, notes/actions, speaker lanes,
   source/provenance, safe handoffs for share/export/delete.
