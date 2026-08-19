# UI Contract: Цельная геометрия compact rail

## Collapsed state

- Rail remains 64px wide and uses the existing horizontal padding.
- Toggle, each navigation item and profile trigger are 40×40px.
- Every control and its icon are centered at `x=32px` relative to the rail.
- Active, hover and focus backgrounds use the same 40×40px bounds.
- Workspace header has no layout box in compact state.
- Focus ring is visible and not clipped; labels remain available to assistive
  technology while visual text is hidden.

## Responsive consistency

- Wide manual collapse and narrow responsive collapse compute the same compact
  control bounds.
- Embedded and standalone surfaces share the same compact axis.
- Expanded state retains the existing 176px width, text layout and actions.

## Interaction preservation

- One top toggle remains in the same slot across expanded/collapsed states.
- Toggle, Escape, focus retention and profile-menu semantics remain unchanged.
- No new state, listener, persistence, breakpoint or dependency is introduced.
