# Contract: Interface Proof

## Web Cabinet Review

The ready review screen must expose:

- active review content without hiding transcript behind unrelated panels;
- transcript rows with seekable timestamps when playback is available;
- persistent bottom playback controls;
- visible speaker activity lanes for when speakers talked;
- stored outcome sections or truthful unavailable/processing/blocked states;
- no incoherent overlap, clipped primary text, or horizontal overflow at
  desktop and compact widths.

## macOS Embedded Cabinet

The embedded review must:

- use the same server-owned meeting review state as web review;
- preserve native Record/Stop/Pause/Resume/upload truth outside WebKit;
- show auth-required and server-unavailable truth instead of cached ready
  state;
- match web review status for the same meeting;
- keep native controls readable and unscaled by embedded review zoom.

## Native macOS Shell

The native shell must:

- keep active capture visible locally;
- keep one-action stop available during recording;
- not show a green cabinet state until an authenticated allowed meeting
  list/detail route succeeds;
- not hide local capture/upload truth when the server or session is unhealthy.

## Approved Observable Krisp Reference

Observe transcript-first review, persistent playback, timestamp seek, speaker
lanes, speaker assignment affordances and multi-speaker interaction patterns.
Record whether assignment is offered, how the selected speaker is associated
with transcript rows and activity lanes, and the visible unavailable state when
it is not offered. For multiple speakers, record how labels and lanes remain
distinguishable. These are reference observations, not an instruction to add a
speaker editor or mutate real meeting data. Compare only existing permitted
GRAF interactions; absent editing stays an explicit scope boundary, not a
claimed implemented capability. Metadata counts do not prove these interactions.

Review fidelity to the approved observable UX/UI/IA, including layout,
interaction states and literal functional wording under Constitution VII and
PRD §§29–30. Record deviations required for accessibility, localization,
privacy, security, deletion truth or known defects. Code must be independent.
Do not reuse source, extracted assets, binaries, private APIs, secrets or private
content. Private screenshots stay outside git and never ship as assets.
Third-party assets, logos and trademarks require documented usage rights;
GRAF consent/legal/marketing claims remain independently true.
