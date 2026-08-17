# Quickstart: Meeting Review Continuity

## Prerequisites

- Run from `/Users/yshishenya/Documents/crisp`.
- Use synthetic fixtures only; do not save real audio, transcript text, or private screenshots.
- For server tests, use the prescribed isolated PostgreSQL runner so the test database URL is configured.

## Focused checks

```sh
node --check apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js

bash apps/server/scripts/run_local_postgres_tests.sh --focused -q \
  tests/unit/test_cabinet_web_shell.py \
  tests/contract/test_recording_workflow_accessibility.py \
  tests/contract/test_cabinet_static_assets_contract.py \
  -k 'speaker or timeline or detail_tab or detail_fetch_actions'
```

The focused selection must cover:

1. one/fitting/overflowing/large speaker sets;
2. pointer and keyboard resize bounds and no-op behavior when rows fit;
3. playing/paused rename success and failure without audio replacement/reload;
4. visible lane hint and action-oriented accessible names;
5. sticky tab semantics, hash preservation, source jump, embedded parity, narrow and reduced-motion CSS contracts.

## Slice gate

```sh
bash infra/scripts/ci-local.sh --fast
```

Record the exact command, commit SHA, pass/fail result, and any environment
limitation. A direct `pytest` invocation without the prescribed runner is not
evidence because this repository requires its isolated database environment.

## Manual visual checks

Using the in-app browser and native computer-use surface with synthetic data:

- available audio with one, fitting, overflowing, and many speaker lanes;
- unavailable audio and missing diarization;
- playing and paused rename in browser and embedded app;
- keyboard focus/Enter/Space/Arrow/Home/End and reduced-motion;
- long transcript/outcome scroll, source jump, `#recording`, and `#outcomes`;
- narrow embedded width, light/dark theme, and no duplicate sticky strips.

Confirm metadata-only evidence: do not capture or retain private meeting content.

## Recorded validation

2026-08-17, base SHA `e6472b40` plus the uncommitted slice:

- `node --check apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js` — PASS.
- The prescribed focused PostgreSQL runner — PASS, 13 passed, 108 deselected.
- `infra/scripts/ci-local.sh --fast` — PASS, 1100 passed; lint and Python compile passed.
- Synthetic browser/desktop-embedded checks — PASS for resize focus and bounds,
  playing/paused rename continuity, narrow viewport scrolling, sticky tabs,
  source jumps, keyboard activation, and reduced-motion CSS contracts.
- Visual frames used only synthetic meeting content; they were inspected and
  moved out of the worktree after review. No private meeting data was retained.
- No deploy, release, commit, or production mutation is part of this slice.
- Native computer-use smoke after manual unlock — PARTIAL PASS: the local
  login/code flow opened the synthetic meeting list and detail, Reload kept the
  first-party route, Back/Forward moved between the list and detail, and Home
  from detail/settings returned to `/desktop/meetings`. The installed Dev
  permission sheet was also observed without changing TCC. The native
  timeline/audio matrix remains open because the local synthetic meeting stayed
  in processing and exposed no playable speaker lanes; no private content was
  retained. T021 remains open.

2026-08-17 follow-up after the Dev packaging fix:

- `infra/scripts/ci-local.sh --fast` — PASS, 1100 passed; lint and Python
  compile passed.
- Native navigation evidence was collected from the installed-compatible
  synthetic local shell; production GRAF remained running separately.

2026-08-17 manual synthetic visual follow-up:

- The local synthetic ready meeting used an ephemeral silent 16-second audio
  object, 8 speaker lanes, and 32 synthetic transcript turns. No private
  meeting content was used or retained.
- In the in-app browser, pointer resize moved the splitter from 96 to the
  natural 221-pixel ceiling, keyboard Home returned it to 96, and a lane click
  moved playback to 8 seconds. The long transcript kept the compact tabs
  visible while scrolling; `Итоги` preserved `#outcomes`. The 700x700 narrow
  viewport retained the hint, controls, and tab semantics without horizontal
  overflow.
- In the in-app browser, a playing rename advanced playback from 0.5 to 1.5
  seconds and remained playing; a paused rename preserved 13.7 seconds and
  remained paused. Both saved synthetic labels were visible without a reload.
- In native `GRAF Dev`, the ready-audio surface showed the same hint and
  accessible lane names. Pointer resize reached 222 pixels, keyboard Home
  returned 96 pixels, and playback position remained unchanged during resize;
  native scrolling kept the compact tabs visible. The ready-audio portion of
  T021 is now PASS.
- The native matrix for unavailable audio, missing diarization, reduced motion,
  and narrow embedded width still needs a separate manual pass; T021 remains
  open until that matrix is complete.

2026-08-17 final synthetic availability and motion matrix:

- Browser fixture `Synthetic unavailable audio` rendered the truthful terminal
  copy «Исходный файл больше не хранится в GRAF» with no player, speaker hint,
  resize separator, or interactive lane. Browser fixture `Synthetic missing
  diarization` retained the transcript and player, used `UNKNOWN` labels, and
  exposed neither the hint nor speaker lanes. Both frames were inspected in the
  in-app browser and contained only synthetic text.
- The installed `GRAF Dev` reproduced both states with the same accessibility
  contract: unavailable audio exposed only the terminal copy; missing
  diarization exposed transcript, player, and the safe playback error without
  advertising speaker interaction. Native screenshots contained only synthetic
  text and were not retained in the worktree.
- The 700×700 narrow embedded browser pass kept the compact tab strip, player,
  and interaction hint usable with no horizontal overflow. The reduced-motion
  CSS contract and keyboard focus states were rechecked through the existing
  static-asset harness; no motion-only affordance is required for lane access.
- Final validation: focused runner 13 passed; Swift focused tests 31 passed;
  `infra/scripts/ci-local.sh --fast` 1100 passed, lint and Python compile
  passed. The final Dev bundle was rebuilt, installed, quit, and relaunched as
  `GRAF Dev`; production `GRAF` remained a separate running app.
- All fixtures and storage objects above are synthetic local validation data;
  no real audio, transcript, private screenshot, credential, or production
  mutation was used. T021 is PASS.

2026-08-18 clean-worktree implementation evidence:

- Implementation commit `97fd3467725632e0a18f81f588a07400a11c22d9` contains only
  Feature 158 timeline, rename and sticky-tab paths plus their Spec Kit docs;
  Feature 159 sidebar/profile/settings paths were intentionally excluded.
- `node --check apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js` — PASS.
- Prescribed focused PostgreSQL runner — PASS, 13 passed, 108 deselected.
- `infra/scripts/ci-local.sh --fast` on the exact implementation SHA — PASS:
  1097 server tests, legacy audio architecture guard, lint and Python compile.
- This entry is metadata-only evidence. No private meeting data, production
  mutation, deploy or release action was performed.
