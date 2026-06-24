# Runtime UI Check: Web Cabinet

**Feature**: `045-transcription-results-pipeline`
**Date**: 2026-06-24

## Scope

This check validates local web cabinet runtime behavior with synthetic
metadata-safe fixture meetings. It does not prove production owner auth,
production deployment, live MediaScribe latency, or private meeting content.

## Fixture Server

- Temporary command:
  `PYTHONPATH=src:. uv run --extra dev python /tmp/serve_045_cabinet_fixture.py`
- Local URL: `http://127.0.0.1:8765`
- Storage: fake local test storage.
- Database: temporary sqlite fixture database.
- Fixture meetings: ready, processing, partial, failed, and unauthorized
  foreign meeting.
- Auth: local fixture headers equivalent to the existing server integration
  tests.

## HTTP Checks

- `/api/v1/health/live`: returned `200`.
- `/meetings` without auth context: returned `401 missing_auth_context`.
- `/meetings` with fixture auth context: returned `200` web cabinet HTML.
- Recheck on 2026-06-24: fixture server returned `200` for
  `/api/v1/health/live` and `401 missing_auth_context` for `/meetings` without
  auth context.

## Browser Runtime Checks

Browser runtime was checked with Playwright using the installed local Chrome
binary and fixture auth headers.

Recheck on 2026-06-24 used the bundled workspace Playwright package and the
same fixture auth headers. Result: `pass`; output directory:
`/tmp/2brain-rec-045-web-cabinet`.

Russian-first UI polish recheck on 2026-06-24 used the bundled workspace
Playwright package, installed local Chrome, and the same fixture auth headers.
Result: `pass`; output directory:
`/tmp/2brain-rec-045-web-cabinet-ru-20260624c`.

Post-evidence-sync Russian-first UI recheck on 2026-06-24 used the bundled
workspace Playwright package, installed local Chrome, and the same fixture auth
headers. Result: `pass`; output directory:
`/tmp/2brain-rec-045-web-cabinet-ru-20260624d`. The fixture server was stopped
after the check.

Continuation runtime recheck on 2026-06-24 used the same temporary fixture
server, bundled workspace Playwright package, installed local Chrome, and
fixture auth headers. Result: `pass`; 9 pages checked; `failures=[]`; output
directory: `/tmp/2brain-rec-045-web-cabinet-ru-20260624f`. The check used
desktop, embedded desktop, and real mobile viewport contexts, verified
`health=200` and unauthenticated `/meetings=401`, then stopped the fixture
server and confirmed port `8765` was free.

MVP closeout continuation runtime recheck on 2026-06-24 used the same temporary
fixture server, bundled workspace Playwright package, installed local Chrome, and
fixture auth headers. Result: `pass`; 9 pages checked; `failures=[]`; output
directory: `/tmp/2brain-rec-045-web-cabinet-ru-20260624g`. The check verified
`health=200` and unauthenticated `/meetings=401`, then stopped the fixture server
and confirmed port `8765` was free.

Runtime continuation recheck on 2026-06-24 used the same temporary fixture
server, bundled workspace Playwright package, installed local Chrome, and fixture
auth headers. Result: `pass`; 9 pages checked; `failures=[]`; output directory:
`/tmp/2brain-rec-045-web-cabinet-ru-20260624h`. The check verified `health=200`
and unauthenticated `/meetings=401`, then stopped the fixture server and
confirmed port `8765` was free.

Goal-continuation runtime recheck on 2026-06-24 used the same temporary fixture
server, bundled workspace Playwright package, installed local Chrome, and
fixture auth headers. Result: `pass`; 9 pages checked; `failures=[]`; output
directory: `/tmp/2brain-rec-045-web-cabinet-ru-20260624j`. The check verified
desktop, embedded desktop, and mobile contexts, no horizontal overflow, no
clipped chip/provider-pill elements, no visible legacy English launch labels,
and then stopped the fixture server and confirmed port `8765` was free.

Continuation web runtime recheck on 2026-06-24 used the same temporary fixture
server, bundled workspace Playwright package, installed local Chrome, and
fixture auth headers. Result: `pass`; 9 pages checked; `health=200`;
unauthenticated `/meetings=401`; `failures=[]`; no horizontal overflow; no
clipped chip/provider-pill elements; no visible legacy English launch labels.
The fixture server was stopped after the check.

Passed pages:

- `/meetings`
- `/meetings/{ready}`
- `/meetings/{processing}`
- `/meetings/{partial}`
- `/meetings/{failed}`
- `/desktop/meetings`
- `/desktop/meetings/{ready}`
- mobile viewport `/meetings`
- mobile viewport `/meetings/{ready}`

Validated behavior:

- Meeting list shows ready, processing, partial, and failed fixture meetings.
- Ready detail shows transcript review, diarization/provenance speaker state,
  notes truth, access governance, artifact policy, and deletion boundary copy.
- Processing detail shows truthful processing state without exposing ready
  transcript content.
- Partial detail shows partial/deferred truth.
- Failed detail shows safe failed import/operator-review copy.
- Desktop embedded list/detail keep review context and hide native creation
  controls.
- Desktop and mobile viewports had no horizontal overflow in the checked pages.
- The Russian-first recheck found no visible legacy English launch labels in
  `innerText`, no `Политика workspace` copy, no horizontal overflow, and no
  clipped status chips on the checked desktop, embedded, and mobile pages.
- The post-evidence-sync Russian-first recheck passed all 9 checked pages with
  `health=200`, unauthenticated `/meetings=401`, no missing required Russian
  launch/result labels, no visible forbidden legacy copy, no horizontal
  overflow, and no clipped chips.
- The continuation runtime recheck passed all 9 checked pages with
  `failures=[]`, no missing required Russian labels, no visible forbidden
  legacy copy, no horizontal overflow, and no clipped `.chip` or provider pill
  elements.
- The MVP closeout continuation runtime recheck repeated the 9-page fixture pass
  with `failures=[]`, including desktop, embedded desktop, and mobile contexts.
- The runtime continuation recheck repeated the 9-page fixture pass with
  `failures=[]`, including desktop, embedded desktop, and mobile contexts.
- The goal-continuation runtime recheck repeated the 9-page fixture pass with
  `failures=[]`, including desktop, embedded desktop, and mobile contexts.

## Visual Inspection Notes

- The desktop list and detail routes rendered without obvious layout breakage.
- The fixed playback bar appears at the bottom of the viewport; full-page
  screenshots can make it look like it floats mid-document, but the runtime
  viewport has content padding and no horizontal overflow.
- Computed list-row title contrast was `rgb(223, 226, 232)` on dark surface with
  opacity `1`; no contrast blocker was confirmed in this check.
- The latest ready-detail desktop and mobile screenshots were manually
  inspected after shortening policy chips; artifact policy rows no longer clip
  or break the status chip text in the checked viewports.

## Status For MVP Audit

- Web cabinet fixture runtime: proven locally for 045 result states.
- Desktop embedded cabinet fixture runtime: proven locally for 045 ready state.
- Production owner-auth web cabinet: not proven by this local fixture check.
- Production upload-to-transcript-to-review: not proven by this local fixture
  check.
