# V6 Screen Redesign Matrix

V5 remains a coverage inventory. V6 has rebuilt the visual hierarchy and
interaction contract screen by screen and is now the QA-clean review candidate.

## Screen Decisions

| V5 frame | V6 verdict | Required redesign |
|---|---|---|
| V5 00 Cover | Keep as coverage board only | Rename to v6 acceptance map; remove "accepted v5" language. |
| V5 01 Auth | Rework | Russian dark sign-in with plain value, account safety, local recording allowed only when policy permits. No technical setup prose. |
| V5 02 Server connection | Rework | Replace setup dashboard with compact account/sync state. Detailed API/storage/worker checks move to diagnostics. |
| V5 03 Permissions | Rework | Native permission recovery should be short, sequential, and task-based. No driver-first framing. |
| V5 04 Desktop ready | Rebuild | First screen: native capture strip + embedded meetings library. Diagnostics hidden. Buttons equal height. |
| V5 05 Active recording | Rebuild | Stop stays primary and pinned. Library remains visible behind/under native recording strip. |
| V5 06 Menu bar | Rework | Compact states: Ready, Recording, Saving, Uploading, Failed, Offline. Stop first while recording. |
| V5 07 Upload queue | Rework | Show local truth and server truth separately but in user language. No local path dump in main row. |
| V5 08 Embedded upload | Rebuild | Same server-owned upload route as web, compact inside desktop, with native capture strip above. |
| V5 09 Meetings list | Rebuild using Krisp IA lesson | Dense rows, status tabs, upload action, upcoming block, scoped search/ask bar. No oversized cards. |
| V5 10 Search/filters | Rework | Browser owns full filters; desktop embedded gets saved views and small search. |
| V5 11 Upload metadata | Rework | Audio-first upload with validation, consent/source provenance, language, participants optional. |
| V5 12 Upload errors | Rework | Errors must name fix: unsupported, too large, no audio, offline, access denied. |
| V5 13 Processing | Rebuild | Stage timeline: uploaded, extracting, transcribing, transcript ready, notes ready. Status visible everywhere. |
| V5 14 Degraded processing | Rework | Partial result first; failed parts and retry/support second. Never show blank transcript as generic failure. |
| V5 15 Meeting review | Rebuild | Remove duplicate toolbar controls; transcript/playback/notes/speakers need a clean review IA. |
| V5 16 Speaker assignment | Rebuild as contract | One lane per speaker, talk time, segments, evidence snippets, rename/merge, conflict states. |
| V5 17 Notes/actions | Rework | Meeting-local outcomes: summary, decisions, action items, source links. Global action center deferred. |
| V5 18 Action edit drawer | Rework | Keep compact; source turn and assignee/status controls clear. |
| V5 19 AI drawer | Rework/defer | Meeting-scoped only for MVP unless backend/privacy scope is ready. No generic novelty assistant. |
| V5 20 Share | Browser-owned | Desktop shows handoff; browser owns permission changes and confirmation. |
| V5 21 Export | Browser-owned | Desktop can show availability; browser owns generation/download. |
| V5 22 Delete | Browser-owned with truth | Keep bounded deletion copy; internal system names only in expanded/audit details. |
| V5 23 Account/settings | Rework | Split account, app appearance, security, workspace. Browser owns admin depth. |
| V5 24 Browser-only handoff | Keep/rework | Needs friendly user copy, not route/debug terminology. |
| V5 25 Empty states | Rework | Compact reasons and next actions for no meetings, filtered empty, offline, signed out. |
| V5 26-29 Light proofs | Defer | Primary launch is dark Russian; light theme should be token proof after v6 dark is accepted. |
| V5 30-33 Boards | Keep as internal boards | Update tokens, route matrix, click map, and critics board after v6 screen rebuild. |
| V5 34 Desktop speakers | Rebuild | Remove visible "native/server route" labels; speaker assignment must feel like product UI embedded in desktop. |
| V5 35 Active + embedded review | Rebuild | Native Stop/policy pinned above web review; no visible technical explanation in user viewport. |

## Minimum V6 Screen Set

Fourteen screens are not enough for the full MVP design. V6 now keeps 29
production-relevant screens:

1. Auth/sign-in.
2. Account/session expired.
3. Desktop ready with embedded meetings.
4. Desktop active recording.
5. Desktop saved/uploading.
6. Desktop upload failed/retry.
7. Desktop permission recovery.
8. Menu bar ready.
9. Menu bar active recording.
10. Web meetings list.
11. Web search/filter.
12. Manual upload.
13. Upload validation errors.
14. Processing in progress.
15. Processing degraded.
16. Review: transcript/playback.
17. Review: notes/actions.
18. Review: speaker assignment lanes.
19. Speaker conflict/save failure.
20. Meeting-local AI drawer if backend scope is approved.
21. Share/access browser modal.
22. Export/download browser menu.
23. Delete/retention truth.
24. Account/settings.
25. Browser-only handoff.
26. Empty/offline/signed-out states.
27. Design tokens/components.
28. Route ownership matrix.

## Pixel QA Gates

V6 QA pass on 2026-06-13:

- [x] No same-row adjacent button cluster has mixed height/radius.
- [x] No product first viewport exposes route names, backend service names, or
  native/web implementation labels.
- [x] All primary controls have stable height and do not resize on state
  change.
- [x] Speaker assignment has one lane per speaker in browser and embedded
  desktop.
- [x] Active recording Stop is visible above embedded desktop routes.
- [x] Every status appears in Russian and maps to the cross-surface status
  matrix.
- [x] Desktop and browser variants show the same meeting status after
  record/upload.
- [x] Screenshots were reviewed after code/node audit.

Final node audit: 29 frames, 70 buttons, 183 valid click reactions, no invalid
prototype destinations, no technical-copy hits, no overflow, and speaker review
frames with 4 tracks, 10 segments, and 4 talk-time percentages each.
