# Analysis: Цельная геометрия compact rail

## Root cause

Feature 159 left three compact axes in the final cascade: 64px rail, 52px
navigation/footer box and 40px icon column. Wide manual collapse used an
incomplete global state while narrow embedded collapse inherited additional
geometry from older media blocks. Profile added its own inline-flex padding.

Historical commits `99479bcc` and `9a93a5cc` proved the simpler invariant:
sidebar padding and one control size must close exactly around one axis.

## Implementation review

- Final JS-ready collapsed state owns 40×40 dimensions and centering for toggle,
  nav, update/download and profile.
- Existing expanded sidebar padding and responsive gaps are unchanged. The
  compact owner keeps its existing `8px 6px` padding and explicitly owns its
  4px nav gap.
- The existing toggle rules now compensate only their own wide/narrow padding;
  expanded content geometry is unchanged.
- Compact footer visibility is restored after JS initialization so the profile
  does not disappear below 1120px.
- JavaScript, Jinja, responsive breakpoint, persistence, routing and native
  code were not changed.

## Findings resolved during live review

1. Profile remained at `x=26` because an inline-flex trigger ignored auto
   margins. The compact owner now uses flex and centers it at `x=32`.
2. Narrow expanded toggle moved to `x=6`. Scoped wide/narrow toggle offsets keep
   expanded `x=12` and collapsed `x=11.5` without changing expanded content.
3. Compact `GRAF Dev` hid the profile through a stale media visibility rule.
   The final state now restores visibility and pointer access.

## Review passes

- Correctness/root cause: no remaining actionable finding after wide/narrow
  computed geometry, same-coordinate click checks and a final independent
  re-review (`No issues found`).
- Frontend review: no applicable React/Tailwind/business-logic violation; no
  actionable CSS finding.
- UX/accessibility: common axis, common state bounds, accessible names, visible
  focus, no overflow/overlap, profile menu keyboard close PASS.
- Clean-room/brand distance: internal GRAF history only; no external layout,
  asset, copy or icon copied.
- Ponytail: lean; no new abstraction, dependency, state, listener or override
  architecture. CSS remains in the existing base, embedded and final state
  owners; no fourth responsive system was added.

## Non-blocking tooling note

The optional `speckit-agent-context-update` hook could not import PyYAML from
system Python. No dependency was installed; its one managed AGENTS.md plan
pointer was updated directly. This does not affect product code or validation.
