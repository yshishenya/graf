# Research: Единый верхний toggle и аккуратный rail

## Current-state evidence

- Computer Use on `GRAF Dev` after native Reload showed the embedded left rail
  compact in a visually wide window. The shared initializer uses a separate
  `min-width: 1121px` embedded query while the normal cabinet uses `981px`.
- In the standalone in-app Browser at 1280px the rail starts expanded.
- At a temporary 900px viewport the rail starts compact, but the compact layout
  keeps a 52px workspace-header box with its content hidden. This creates an
  empty vertical band between the top toggle and the first nav item.
- After expanding the 900px rail, a click on the main heading changes it back to
  compact. The document outside-click handler is the direct cause; the same
  handler also collapses after navigation links.
- The compact accessibility tree exposes nav links without accessible names
  because their visible labels are removed with `display: none` and the links do
  not provide an explicit `aria-label`.

## Decisions

### 1. Use one native fixed top slot

The same `InspectorDisclosureButton` remains the only control. A small shared
top-slot helper is used by collapsed and expanded inspectors; expanded content
starts below it, and the scroll view no longer owns the disclosure control.

**Rationale**: A stable action location reduces search cost and makes the
second click possible without pointer travel. A dedicated slot protects the
title, settings action and capture controls from overlay collisions.

**Alternatives rejected**:

- Keeping expanded header plus compact footer: reproduces the reported bug.
- Duplicating top and bottom buttons: creates two competing controls and focus
  ambiguity.
- Overlaying the button on content without reserved space: can hide focus or
  capture content while scrolling.

### 2. Keep rail state manual until explicit dismissal

Remove the document outside-click and nav-link collapse handlers. Reuse the
existing toggle focus retention and Escape dismissal. The `railReady` guard and
one-time responsive initialization remain unchanged.

**Rationale**: A panel described as staying open until the opposite action must
not react to unrelated content clicks. Escape remains a conventional keyboard
way to dismiss a temporary expanded navigation surface.

### 3. Use the practical 981px embedded default

Use the same `min-width: 981px` responsive decision for standalone and embedded
surfaces. CSS still determines the actual 64px/176px geometry, and the web
viewport can naturally become compact when the native inspector consumes space.

**Rationale**: The measured `GRAF Dev` window is large to the user but the
1121px embedded CSS viewport threshold leaves it compact. The existing browser
981px threshold is already exercised and provides the expected wide/narrow
boundary without adding another configuration source.

**Alternative rejected**: Persisting a preference or reading native window
geometry from the web view; both add state/bridge complexity and were not
requested.

### 4. Compact rail removes hidden structure but keeps semantics

Hide the workspace header only in the compact presentation. Add explicit
`aria-label` values to all cabinet navigation anchors so visually hidden labels
do not make the compact rail unnamed.

**Rationale**: Compactness should remove visual bulk, not navigation meaning.
The change reuses existing item labels and does not add a second accessibility
component or tooltip system.

## UX/accessibility principles applied

- Stable placement and same action affordance across states.
- Visible state labels are mirrored by `aria-expanded`, `aria-label`, title and
  focus/hover feedback.
- Hover tooltip supplements, but does not replace, the accessible name.
- Responsive compactness removes nonessential visual decoration while keeping
  one-handed targets, keyboard access and nav semantics.
- Evidence follows clean-room review: only general interaction principles are
  used; no Krisp layout, copy or visual asset is copied.
