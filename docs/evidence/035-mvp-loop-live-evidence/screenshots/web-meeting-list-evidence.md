# Web Meeting List Evidence

Feature: `035-mvp-loop-live-evidence`

## Scope

This note replaces a live browser screenshot because the production owner route
could not be opened with a commit-safe authenticated session during this pass.
It records only metadata-safe route behavior and fixture-backed UI coverage.

## Production Route Probe

- Route: `https://rec.2brain.pro/meetings`
- Server result without committed auth context: `401 missing_auth_context`
- Browser automation result: Chrome extension navigation reported
  `net::ERR_BLOCKED_BY_CLIENT` for the same route.
- Safety decision: no live screenshot was committed because authenticated owner
  content could expose private meeting/account data.

## Fixture-Backed Coverage

Local web list coverage is represented by:

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q tests/integration/test_cabinet_meeting_list.py
```

The existing fixture tests cover:

- `/meetings` list route rendering.
- Meeting notes list shell.
- Upcoming block.
- New/upload affordance.
- Filter and sort affordances.
- Authorized workspace-only rows.
- Access/governance future slots.

## Readiness Classification

- Route availability: `ready`, because the route exists and returns the
  expected auth boundary instead of a missing route.
- Live owner review proof: `blocked`, because no commit-safe authenticated
  production session was available.
- Fixture UI shape: `ready`, because local tests cover the expected list shell.
