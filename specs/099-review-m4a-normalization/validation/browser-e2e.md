# Feature 099 Browser And Embedded E2E Receipt

**Date**: 2026-07-14
**Task**: T100
**Status**: complete for the local synthetic Chrome and embedded acceptance
gate. Production proof remains T115.

## Scope and recovery

The requested Chrome surface was selected through the project Chrome-control
workflow. Diagnostics proved Chrome, the enabled extension and its native host
were available. Programmatic top-level navigation to the isolated loopback
harness initially returned `ERR_BLOCKED_BY_CLIENT`, including for a two-byte
plain-text `OK` server. That isolated the failure to the control-channel
navigation boundary rather than GRAF, authentication, playback or media bytes.

Recovery used the documented handoff path: the user entered the local URL once
in fresh Chrome tabs, after which the same Chrome-control client claimed and
operated those tabs. Standalone Playwright, AppleScript and Computer Use were
not substituted for the explicitly requested Chrome surface. No public
listener, production endpoint or production data was used.

The local cabinet and media subrequests used a test-only reverse proxy bound to
`127.0.0.1:8100`. It injected the synthetic owner identity into every request
and forwarded to the unchanged feature harness on `127.0.0.1:8099`. This
changed only isolated test authentication; product code and the playback route
were unchanged.

## Real Chrome functional proof

Two simultaneously controlled Chrome tabs loaded the same four synthetic
records and projected identical durable truth:

- preparing: `Аудио готовится автоматически`;
- available: `Аудио готово`;
- terminal: `Файл повреждён и не может быть воспроизведён`;
- transcript/playback independence: `Частично готово` plus `Аудио готово`.

Both tabs opened the same available record. In the first tab:

- Play changed `Воспроизвести` to `Приостановить` and advanced the real media
  position;
- Pause returned the control to `Воспроизвести` and held the position at
  `10.9s` across a further `1.6s` observation;
- forward seek changed the position from `10.9s` to `25.9s`.

The second tab continued to show the same record and ready status at `0:00`.
This proves durable record/status parity across two tabs while each tab keeps
independent playback position.

A fresh final run then exercised automatic recovery in Chrome. The preparing
detail contained no audio element, range input or repair/retry/reprocess
control. The harness scheduled publication after `2.5s`; its durable state
became `ready`, and an ordinary page reload projected the player without any
user repair action. Play advanced the position from `0` to `1.5s`; Pause later
held `9.5s`; forward seek moved it to `24.5s`.

The proxy recorded two matching browser media responses:

```text
status=206 range=bytes=0- content-range=bytes 0-35620/35621 length=35621
status=206 range=bytes=0- content-range=bytes 0-35620/35621 length=35621
```

The terminal detail likewise contained no audio element, range input or repair
control. Chrome console error/warning receipts were empty in both the two-tab
run and the final visual run.

## Chrome accessibility and layout proof

The final Chrome run used only synthetic titles. Temporary viewport and media
emulation were reset before cleanup.

- Wide `1440x900`: `scrollWidth=clientWidth=1440`; the sidebar, filters and all
  four rows remained visible.
- Narrow `740x900`: `scrollWidth=clientWidth=740`; rows reflowed without
  horizontal overflow and controls remained visible.
- Keyboard: the first Tab focused `К содержимому`; the next focused
  `Мои встречи`. Both matched `:focus-visible` with a solid `2px` outline.
- Light system preference: the media query changed to light while GRAF's
  intentional root `color-scheme: dark` remained readable with background
  `rgb(25, 26, 28)` and text `rgb(232, 234, 238)`.
- Dark system preference: the dark query was active and the same intentional
  dark palette remained stable.
- Reduced motion: the query was active; row animation and transition durations
  resolved to `1e-06s`, iteration count to `1`, and scroll behavior to `auto`.
- After reset, Chrome returned to its ordinary `1800x860` viewport, dark system
  preference and `reducedMotion=false`.

Safe screenshots were inspected in-memory for the wide, narrow, light, dark
and reduced-motion states. They were not persisted as repository artifacts.

## Embedded macOS proof

The project-owned release build completed and its staged application signature
verified. The final retest used a separate ad-hoc signed derived QA bundle with
test-only version `2026.07.14.99` and bundle identifier
`pro.2brain.graf.feature099`. Its isolated home prevented the installed app's
real upload queue from entering the test. The installed `/Applications/GRAF.app`
was not replaced or restarted.

The real embedded WKWebView proved:

- the same preparing, available, unavailable and transcript-independent list
  projections as Chrome;
- preparing detail showed `Аудио готовится автоматически` with no player or
  repair control;
- available detail exposed back 15 seconds, Play/Pause, forward 15 seconds,
  speed, a position slider and `00:00`/`00:40` labels;
- Play/Pause advanced then held the position at `2.3s`;
- forward seek changed `2.3s` to `17.3s`, then `32.3s`;
- a post-seek Play/Pause cycle held `33.7s`, proving the seek affected real
  playback rather than presentation only;
- transcript and speaker projections stayed visible independently from the
  playback controls.

For reconnect proof, the transition was scheduled and the QA app was stopped
before publication. The server reached `ready` while the app was absent.
Relaunching the same isolated app showed the record as `Аудио готово`. App/page
closure therefore did not cancel work, and reconnect read durable server truth.

The embedded activity ledger also recorded authorized Range responses for
bytes `0-1` and `0-35620`, matching real Play behavior. Deletion precedence is
owned by the T101 lifecycle receipt and the final current-master Chrome
deletion run below. The desktop and browser routes render the same cabinet
fragment and terminal `404/410` polling contract; the destructive confirmation
itself was exercised only against synthetic data in Chrome, not against the
installed desktop app.

## Post-`v2026.07.14.7` current-master retest

After the uncommitted 099 working copy was reapplied on current `master` at
`98d57f7431d302b0d2060fb020fc2b320f854753`, the real Chrome gate was repeated
against the new cabinet shell rather than relying on the earlier UI receipt.

- All four synthetic list states remained visible in the compact current
  meeting list.
- Wide `1440x900` and narrow `740x900` both reported
  `scrollWidth == clientWidth`; all four rows remained present.
- At the narrow breakpoint, keyboard focus reached `К содержимому` and then
  `Поиск встреч`, both focus-visible with a solid `2px` outline.
- Reduced motion remained active at `1e-06s` animation/transition duration and
  `scroll-behavior: auto`.
- Preparing detail exposed no audio/range/repair control, then automatic poll
  projected a real `readyState=4`, 40-second player after publication.
- Play advanced to `1.935s`; Pause held `10.532s` for a further `1.2s`; forward
  seek moved `10.532s -> 25.532s` while paused.
- Chrome received `206` for `Range: bytes=0-` with
  `Content-Range: bytes 0-35620/35621`.
- Corrupt detail retained the exact safe terminal copy and exposed no
  audio/range/repair control.
- Chrome warning/error logs were empty.

The final candidate was then repeated after the independent review fixes:

- synthetic `503`, login redirect/HTML and socket-disconnect poll failures kept
  the preparing state non-terminal, displayed the live recovery notice
  `Не удалось обновить статус. GRAF попробует снова автоматически.` and kept
  automatic polling active;
- the next valid response cleared the notice without a user action;
- automatic publication produced one `readyState=4`, 40-second player without
  reload; Play advanced, Pause held, the slider reached `00:20` and `00:40`,
  back 15 seconds returned to `00:25`, and reload retained exactly one player;
- a real synthetic delete confirmation was submitted while another Chrome tab
  was polling the preparing detail; that tab changed to
  `Запись больше недоступна`, exposed `0` audio and `0` range controls, and
  stayed terminal after the harness later attempted publication;
- the deleted detail returned `404`, the player did not resurrect, and Chrome
  warning/error logs remained empty.

The current-base derived macOS QA bundle also loaded the same preparing detail
and projected the player automatically after publication without reload. Its
WebKit accessibility tree exposed Play, back/forward 15 seconds, speed, slider
and `00:39` duration controls. The Play action was accepted; the next stable
accessibility state showed the slider at `39.9` seconds and the control returned
to Play after reaching the end, proving current-base media progression rather
than a static player projection. A later attempt to collect an additional
destructive desktop screenshot failed in macOS ScreenCaptureKit and closed only
the disposable QA process; it did not change product state or weaken the
already-recorded embedded Play/Pause/seek/reconnect proof. The installed
`/Applications/GRAF.app` remained separate and running.

Temporary viewport and media emulation were reset. The new agent-created tab,
proxy, harness, ports, state file and runtime directory were cleaned with zero
residue. Full integration details are in `master-sync.md`.

## Cleanup and conclusion

- Chrome test tabs were closed; viewport and media emulation were reset.
- The QA process, proxy and harness stopped.
- Ports `8099`, `8100` and disposable PostgreSQL port `55499` closed.
- The derived QA app, isolated home, state file and harness runtime directory
  were removed; temporary runtime residue was `0`.
- Feature-owned pytest temp directories and bundle saved-state paths were
  removed; Docker feature residue was `0`.
- The installed GRAF application remained running and untouched.
- Feature 097 and its resumable Codex Security scan remained deferred and were
  not used as acceptance evidence.

T100 is complete. The local synthetic receipt proves real Chrome and embedded
preparing/available/unavailable parity, automatic recovery, Play/Pause/seek,
Range delivery, two-tab durability, reconnect, keyboard focus, responsive
layout and reduced-motion behavior, including a repeat against the current
`v2026.07.14.7` cabinet shell. It is not production proof; that remains T115
after merge, release and deploy.
