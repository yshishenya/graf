# Contract: Interface Proof

## Web Cabinet Review

The ready review screen must expose:

- active `Запись и расшифровка` review content without showing stale outcomes
  first;
- transcript rows with seekable timestamps when playback is available;
- persistent bottom playback controls;
- visible speaker activity lanes with intervals for when speakers talked;
- stored outcome sections or truthful unavailable/processing states;
- no horizontal overflow or incoherent overlap at desktop and mobile widths.

## macOS Embedded Cabinet

The embedded review must:

- use the same server-owned route family as web review;
- preserve native Record/Stop/Pause/Resume/upload truth outside WebKit;
- show auth-required and server-unavailable truth instead of cached ready
  state;
- match web review status for the same meeting.

## Native macOS Shell

The native shell must:

- keep active capture visible locally;
- keep one-action stop available during recording;
- not show a green cabinet state until an authenticated allowed meeting
  list/detail route succeeds;
- not hide local capture/upload truth when the server or session is unhealthy.

## Clean-Room Rule

Krisp can guide interaction patterns only. No Krisp asset, screenshot, brand
color, proprietary copy, icon, or private content may be committed or copied.
