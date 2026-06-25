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

## KRISP Clean-Room Reference

KRISP may guide interaction expectations for transcript-first review,
persistent playback, timestamp seek, speaker lanes, and speaker assignment.
No KRISP asset, screenshot, brand color, proprietary copy, icon, or private
content may be committed or copied.
