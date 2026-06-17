# Contract: Notes And Actions Truth

Feature: `036-owner-review-live-polish`

## Purpose

Ensure meeting review surfaces do not overclaim generated notes, decisions,
action items, or follow-ups.

## State Enum

Each outcome category must be represented as one of:

- `available`: stored output exists and can be shown safely.
- `processing`: upstream processing may still produce output.
- `blocked`: output cannot be produced or shown because of an error, policy, or
  missing prerequisite.
- `unavailable`: no output exists for the meeting.
- `deferred`: the product intentionally does not implement this output in the
  current MVP slice.

## Outcome Categories

- `summary`
- `decisions`
- `action_items`
- `followups`

## Required Behavior

1. Meeting list and detail states must expose whether notes/actions are usable,
   pending, blocked, unavailable, or deferred.
2. Detail surfaces must explain the launch-readiness impact when outcomes are
   unavailable or deferred.
3. `available` must be backed by stored data; transcript existence alone is not
   enough.
4. The UI must not present placeholder text as generated notes.
5. Readiness evidence must keep `mvp_loop_ready` excluded when outcome
   categories remain unavailable, blocked, or deferred in a P1-blocking way.

## Evidence

Committed evidence should use state labels, copy keys, fixture-backed tests, and
safe screenshots. Private transcript text or generated private meeting content
must not be committed.
