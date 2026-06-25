# 052 UI Reference Review

All notes are clean-room and metadata-only. Do not commit KRISP screenshots,
private account details, private meeting content, transcript text, audio, or
copied brand assets.

## KRISP Reference Observations

- Opened the existing KRISP meeting detail tab in Chrome and inspected the
  `Recording & Transcript` surface without copying private meeting content.
- Reference shape:
  - left navigation stays visible beside the meeting detail;
  - transcript rows show timestamp, speaker label/avatar/color, and text;
  - bottom playback shell stays persistent while transcript scrolls;
  - bottom timeline shows one lane per speaker with colored segments and
    percentage share;
  - player has skip/play/speed/progress controls separate from native browser
    audio controls;
  - `Assign speakers` is colocated with speaker colors in the bottom shell.
- Playback behavior:
  - page has one hidden/custom-controlled `<audio>` element;
  - media source kind observed as `cross-origin-url`;
  - ready state was loaded and duration was known;
  - clicking the visible play control changed audio `paused=false`, and a
    second click returned `paused=true`.
- Product implication for 2brain:
  - keep custom bottom review player and speaker lanes visible;
  - do not rely on browser-native audio controls as the main UX;
  - streaming/range-backed playback is enough for review; a separate compressed
    share/download file can remain post-MVP.

## 2brain Web Cabinet Observations

- 052 browser runtime verifier passed for fixture-backed web, mobile web,
  embedded desktop, and embedded mobile review:
  - `failures=[]`;
  - one audio player;
  - `combined_review_stream`;
  - timestamp seek works;
  - three speaker timeline rows;
  - eight stored outcome rows;
  - no horizontal overflow.
- Live production `/meetings` initially rendered a meeting list, but opening a
  meeting detail redirected to `/login?error=missing_auth_context`.
- Current web production owner-review proof therefore remains blocked by auth
  context, not by local fixture UI layout.

## 2brain macOS Embedded Cabinet Observations

- Installed app window was captured by window id after restart.
- Native shell state:
  - app version evidence remains in `installed-app-check.md`;
  - local meetings/actions/sidebar are visible;
  - cabinet subtitle says `Нужен вход`;
  - embedded cabinet panel says `Нужен вход в кабинет`;
  - `Войти в кабинет` recovery action is visible;
  - local recording/upload truth remains in the native shell instead of a false
    green cabinet state.
- Runtime log shows embedded navigation finishing as `expiredSession` on the
  production login route, matching the visible state.

## P1 Findings

- status: `blocked`
- findings:
  - production owner review detail is blocked by `missing_auth_context`;
  - production processing dispatch is blocked before the 052 Compose fix is
    deployed;
  - production stored outcomes are not materialized yet (`0` sets/items);
  - representative one-hour timing remains unproven.

## Brand-Distance Notes

- KRISP is used only as interaction reference. 2brain keeps its own visual
  system, Russian copy, server-owned review surface, and native capture shell.
