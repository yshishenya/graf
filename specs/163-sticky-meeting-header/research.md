# Research: Закреплённый верхний блок встречи

## Decision: one sticky wrapper

Sticky positioning should belong to the smallest group that must remain
together. Keeping only tabs sticky creates a visual split: title and actions
scroll away while the tab underline remains. A wrapper around topline, share
host and tabs gives one background, z-index and stacking context.

## Decision: native CSS, no scroll listener

The existing main element is already the scroll container. CSS `position:
sticky` is native, preserves normal flow and avoids scroll performance and
partial-update lifecycle problems. A negative top margin plus matching padding
lets the header cover the main content padding while preserving initial spacing.

## Decision: responsive scroll margin

Transcript and outcome source jumps need a larger margin than the old tab-only
value. Use a CSS custom property with desktop and narrow defaults. It is a
layout constant, not user state; no ResizeObserver is introduced unless
visual validation proves the fixed responsive values insufficient.

## Alternatives considered

- Keep tabs sticky and duplicate title in a compact bar — rejected: duplicate
  context and two stacking layers are confusing.
- JavaScript scroll shadow/state manager — rejected: unnecessary for native CSS
  sticky and creates partial-render lifecycle work.
- Fixed `top` offsets with no wrapper — rejected: title/actions still scroll.
