# Validation Log: Real Playback Availability

This file records metadata-only validation for feature `048`.

## 2026-06-24

- Created isolated `048` worktree from `origin/master` at `895de8b` to avoid
  mixing dirty `045` and in-progress `047` changes.
- Feature branch created: `048-real-playback-availability`.
- Root cause from `046` inspection: playback was implemented for fixture-ready
  meetings only when tests manually enabled `audio_download="allowed"`. Normal
  real recordings keep artifact download policy disabled by default, so the
  review page does not render a player.
- Product decision for `048`: review playback must be separate from artifact
  download/export policy. A user may listen in review without gaining a file
  download/export action.
- Krisp reference review uses transcript-first layout, persistent bottom
  playback controls, seekable transcript timestamps, and speaker lanes on a
  timeline. This is used as clean-room UX reference only; no proprietary code,
  copy, icons, or assets are reused.
- Spec Kit prerequisites passed for `048` with available docs:
  `research.md`, `data-model.md`, `contracts/`, `quickstart.md`, and
  `tasks.md`.
- Checklist status: `requirements.md` 16/16 complete, `security.md` 15/15
  complete, `ux.md` 13/13 complete.
- Read-only pre-implementation consistency pass found no placeholders and task
  traceability for all `FR-001` through `FR-014` plus `SC-001` through
  `SC-007`.
- RED targeted playback validation ran before production changes:
  `PYTHONPATH=src uv run --extra dev pytest -q
  tests/contract/test_cabinet_playback_contract.py
  tests/integration/test_cabinet_meeting_detail.py
  tests/integration/test_cabinet_playback_route.py
  tests/unit/test_cabinet_web_shell.py`.
  Result: 15 failed, 14 passed. Expected failures covered default-policy
  playback invisibility, playback route download-policy coupling, missing
  byte-range semantics, and missing persistent bottom playback UI.
- Focused playback validation after implementation used the same command.
  Result: 29 passed, 1 warning. Verified review playback is available by
  default for ready dual-track meetings, audio download remains policy-blocked,
  `/playback` supports `206` byte ranges, and web plus desktop embedded shells
  render the persistent bottom player.
- Extended focused validation ran:
  `PYTHONPATH=src uv run --extra dev pytest -q
  tests/contract/test_cabinet_playback_contract.py
  tests/integration/test_cabinet_meeting_detail.py
  tests/integration/test_cabinet_playback_route.py
  tests/unit/test_cabinet_view_models.py
  tests/unit/test_cabinet_web_shell.py
  tests/unit/test_playback_audio.py
  tests/contract/test_cabinet_no_secret_content_egress.py
  tests/unit/test_artifact_egress_audit.py`.
  Result: 48 passed, 1 warning. The warning is the existing
  `pytest_asyncio` event loop policy deprecation.
- Browser runtime validation ran with bundled Node/Playwright and installed
  Google Chrome:
  `NODE_PATH=<bundled-node-modules> <bundled-node> specs/048-real-playback-availability/evidence/browser-runtime-check.cjs`.
  Result: `failures=[]` across web ready desktop/mobile, embedded ready
  desktop/mobile, and unavailable desktop/mobile. Ready pages had one playback
  audio element, one bottom playback shell, three seek targets,
  `seekCurrentTime=31`, `sourceMode=combined_review_stream`, three speaker
  timeline segments, `horizontalOverflow=0`, and bottom bar aligned to viewport
  bottom. Unavailable pages rendered no audio element and showed Russian
  unavailable copy.
- Forbidden-content scan over `specs/048-real-playback-availability` excluding
  `quickstart.md` returned no matches for local user paths, private key
  markers, API tokens, signed URL markers, storage object keys, transcript text
  markers, or raw audio markers.
- Full local CI ran with `infra/scripts/ci-local.sh`. Result:
  `ci_local_result=pass`. Server tests: `570 passed, 4 skipped, 90 warnings`;
  server lint: `All checks passed`; deployment evidence scan: `pass`. The RLS
  hardening boundary reported its expected local `postgres_test` blocker and
  did not attempt a live production probe.
- Deploy dry-run ran with `infra/scripts/cd-remote.sh --dry-run`. Result:
  `deploy_result=dry_run`, `remote_host=2brain.dev`,
  `remote_path=/opt/projects/2brain-rec`, and
  `branch=048-real-playback-availability`. Dry-run steps included clean
  worktree, branch sync, pinned sha, local CI, remote fetch, backup, restore
  rehearsal, compose config secret scan, deploy build/up, runtime secret/env
  scan, production smoke, and public health.
- macOS embedded review boundary: no files under `apps/macos` changed in 048.
  The installed app uses the server-owned `/desktop/meetings/{meeting_id}`
  review route for embedded playback. Server integration tests and browser
  runtime validation covered that embedded route across desktop and mobile
  viewport sizes, so focused Swift `DesktopCabinet` tests were not rerun for
  this server/web-only slice.
- Task reconciliation: all tasks `T001-T045` in
  `specs/048-real-playback-availability/tasks.md` are checked after validation
  evidence was recorded. A final `rg -- "- \\[ \\]"` over the task file returned
  no matches.
- GitHub issue sync: `speckit.github-issue-canon.ensure` completed and set
  active/default feature label `feature:048`. Issues were created from
  completed tasks `T001-T045`, closure comments were added with validation
  evidence, and all 45 issues were closed as completed. Mapping is recorded in
  `specs/048-real-playback-availability/issues.md`; GitHub list check returned
  `count=45` and `open=[]`. Canon validation returned `OK`. The forbidden
  content scan was rerun after issue mapping was added and again returned no
  matches.

## 2026-06-25

- Real local server/browser playback validation ran:
  `NODE_PATH=<bundled-node-modules> <bundled-node>
  specs/048-real-playback-availability/evidence/real-server-runtime-check.cjs`.
  The verifier started a temporary FastAPI/uvicorn server with SQLite and fake
  object storage, seeded a ready owner meeting, replaced retained mic/system
  sources with synthetic 40-second WAV fixtures, and opened the ordinary web
  meeting route plus the desktop embedded meeting route in Playwright/Chrome.
  Result: `failures=[]`.
- The same real-server validation confirmed server-mediated range playback:
  playback route returned `206`, `Accept-Ranges: bytes`, a valid
  `Content-Range`, `Content-Length: 16`, and no forbidden storage or signed URL
  marker in the range body or headers.
- The real-server browser checks confirmed review UI availability across web
  desktop, web mobile, and desktop embedded routes: one playback audio element,
  one fixed bottom playback shell, two playback seek controls, two transcript
  timestamp seek controls, `seekCurrentTime=12.5` after seeking, source mode
  `combined_review_stream`, two speaker timeline segments, no audio download
  link, no horizontal overflow, and the bottom bar aligned to the viewport
  bottom.
- Post-verifier safety checks were rerun after hardening the evidence script:
  incomplete task scan returned no matches, forbidden-content scan over
  `specs/048-real-playback-availability` excluding `quickstart.md` returned no
  matches, raw fixture transcript text scan over the feature directory returned
  no matches, and `git diff --check` passed.
- Full local CI was rerun on the current worktree with
  `infra/scripts/ci-local.sh`. Result: `ci_local_result=pass`; server tests:
  `570 passed, 4 skipped, 90 warnings`; server lint: `All checks passed`;
  Python compile and deployment evidence scan passed. The RLS hardening boundary
  again reported the expected local `postgres_test` blocker and did not attempt
  a live production probe.
- Deploy dry-run was rerun on the current worktree with
  `infra/scripts/cd-remote.sh --dry-run`. Result: `deploy_result=dry_run`,
  `remote_host=2brain.dev`, `remote_path=/opt/projects/2brain-rec`,
  `branch=048-real-playback-availability`, and planned release steps included
  clean worktree, branch sync, pinned sha, local CI, remote fetch, backup,
  restore rehearsal, compose config secret scan, deploy build/up, runtime
  secret/env scan, production smoke, and public health.
- GitHub tracker recheck returned `count=45`, `open=[]` for label
  `feature:048`, and issue canon validation returned `OK`.
- After visual inspection of temporary synthetic screenshots, the mobile player
  CSS was tightened to reduce height and use an opaque bottom bar on narrow
  screens. Web-shell validation then passed `17 passed, 1 warning`, synthetic
  browser runtime returned `failures=[]` with three timestamp seek targets, and
  real local server/browser validation with temporary screenshots again returned
  `failures=[]`. Screenshots were generated under a temporary local directory
  for visual QA only and are not committed.
- Full local CI was rerun after the mobile player CSS change:
  `ci_local_result=pass`; server tests: `570 passed, 4 skipped, 90 warnings`;
  server lint, Python compile, and deployment evidence scan passed.
- Deploy dry-run was rerun after the mobile player CSS change:
  `deploy_result=dry_run`, `remote_host=2brain.dev`,
  `remote_path=/opt/projects/2brain-rec`,
  `branch=048-real-playback-availability`.
- Approval closeout gate ran after explicit user approval to close out 048:
  Spec Kit prerequisites resolved this feature directory, deploy dry-run
  returned `deploy_result=dry_run`, and full local CI returned
  `ci_local_result=pass` with server tests
  `570 passed, 4 skipped, 90 warnings`, server lint, Python compile, and
  deployment evidence scan passing.
