# Figma V6 QA Evidence

File: <https://www.figma.com/design/ylPz3AxOOfVoLJEG4dF9Yr>
Page: `030 MVP Experience v6 - Krisp-grounded RU`
Page id: `118:2`
Status: mechanically QA-clean but rejected by stakeholder product/design review;
not an implementation handoff target. Use v6 as evidence for the v7 rebuild.

## Screen Coverage

- Total frames: 29.
- Primary language: Russian.
- Primary theme: dark.
- Core surfaces covered: auth, account/session, desktop ready, desktop active
  recording, local queue/upload retry, permission recovery, menu bar states,
  web meeting library, search/filter, manual upload, validation errors,
  processing, degraded processing, transcript review, notes/actions, speaker
  lanes, speaker conflict, meeting-scoped AI, share, export, delete, settings,
  browser-only handoff, empty states, token board, route matrix.

## Programmatic QA

Final Figma Plugin API audit:

| Check | Result |
|---|---:|
| Frame count | 29 |
| Button candidates | 70 |
| Valid clickable prototype reactions | 183 |
| Prototype destination issues | 0 |
| Adjacent button cluster height/radius issues | 0 |
| Technical-copy leaks | 0 |
| Overflow count | 0 |

Speaker-lane contract:

| Frame | Tracks | Segments | Talk-time percentages |
|---|---:|---:|---:|
| `V6 16 - Review transcript and playback` | 4 | 10 | 4 |
| `V6 18 - Speaker assignment lanes` | 4 | 10 | 4 |
| `V6 19 - Speaker conflict and save failure` | 4 | 10 | 4 |

## Visual Screenshot QA

Saved screenshots:

- `screenshots/v6-desktop-ready.png`
- `screenshots/v6-web-meetings.png`
- `screenshots/v6-review-transcript.png`
- `screenshots/v6-speaker-lanes.png`
- `screenshots/v6-empty-states.png`
- `screenshots/v6-full-contact-sheet.png`

Manual visual fixes after first screenshot pass:

- expanded and repositioned the review playback lane area so the fourth speaker
  row is not clipped;
- clamped speaker segments so they cannot overlap the talk-time percentage
  column;
- normalized the component-board button row to avoid false visual
  inconsistency.
- added a full-page contact sheet after the final prototype pass to review all
  29 frames together.

Prototype QA after final pass:

- wired the owner value loop from auth/sign-in through desktop recording,
  upload, processing, transcript review, notes, speaker assignment, share,
  export, delete, settings, browser handoff, and empty states;
- skipped same-frame filter/self-navigation controls instead of creating fake
  prototype movement;
- verified all 183 reactions navigate to different top-level frames on the same
  page.

## Rejection Note

The 2026-06-13 stakeholder review found that v6 still has weak IA, settings,
auth, active-recording, upload/processing, density, and product-flow issues.
The mechanical checks above remain useful, but they were too narrow to prove
handoff readiness. Continue in
`../v7-deep-product-redesign-2026-06-13/`.
