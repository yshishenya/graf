# Web Notes/Action Truth Evidence

Feature: `036-owner-review-live-polish`

Date: 2026-06-16

Surface: server-owned cabinet web/API review state.

## Validation

Command:

```sh
PYTHONPATH=src uv run --extra dev pytest -q tests/contract/test_notes_action_truth_contract.py tests/unit/test_notes_action_truth_view_models.py tests/integration/test_cabinet_meeting_detail.py tests/unit/test_cabinet_web_shell.py tests/contract/test_cabinet_no_secret_content_egress.py
```

Result: `21 passed`.

## Covered States

- `processing`: transcript and outcomes are still processing.
- `blocked`: failed processing or summary reported without stored launch-safe output.
- `deferred`: transcript exists, but generated outcomes are not stored/reviewable.
- `unavailable`: schema accepts unavailable states for unsupported/no-source cases.
- `available`: schema accepts available only when future stored output exists.

## Safety Notes

- No private meeting titles, transcript snippets, account identifiers, tokens,
  cookies, signed URLs, or local absolute paths are included here.
- The web detail no longer renders the old generic future placeholder. It
  renders explicit `Summary`, `Decisions`, `Action Items`, and `Follow-ups`
  rows with state chips and launch-readiness impact.
