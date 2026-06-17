# Contract: Runtime Polish And Clean-Room Baseline

Feature: `036-owner-review-live-polish`

## Purpose

Move the current desktop and web review surfaces toward the accepted feature
030 V8 baseline without copying Krisp expression or weakening native capture
trust.

## Target Surfaces

- `/Applications/2brain Rec.app` main meeting workspace.
- Desktop active, paused, resumed, and stopped recording states.
- Embedded desktop meeting list/detail review.
- Web meeting list at `/meetings`.
- Web meeting detail at `/meetings/{meeting_id}`.
- Governance/access/delete/share/export/download states where already
  implemented.
- Responsive compact web layout.

## Required Behavior

1. Meeting workspace content must appear before low-level diagnostics.
2. Native Record/Pause/Resume/Stop controls must remain visible and authoritative
   outside embedded web content.
3. Search/filter/sort/upload/new/review actions must use product-facing labels
   and stable responsive dimensions.
4. Unavailable features must use truthful disabled/deferred/blocked states, not
   fake controls.
5. Desktop and web text must fit containers on common desktop and compact
   viewports.
6. UI must preserve original 2brain design language and clean-room brand
   distance.

## Forbidden

- Committed Krisp screenshots or private reference captures.
- Copied Krisp brand assets, icons, color expression, or non-generic copy.
- In-app text that explains implementation shortcuts instead of product state.
- Diagnostic-first main workspace unless the app is in a failure or diagnostic
  mode.

## Evidence

Evidence may include sanitized screenshots from the installed app, synthetic
fixture screenshots, responsive screenshot notes, checklist results, and
forbidden-content scans. Private live meeting content must not be committed.
