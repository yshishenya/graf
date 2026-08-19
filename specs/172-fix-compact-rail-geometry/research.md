# Research: Цельная геометрия compact rail

## Current-state evidence

- Supplied Retina screenshot measures a 64px CSS rail with intended center
  `x=32px`, while toggle is at `x≈26`, navigation icons at `x≈15` and profile
  at `x≈21`.
- The active item is `52×36px`: its background is centered but its icon is
  aligned inside the leading part of a 40px grid column.
- Current CSS contains three responsive rail systems: legacy embedded at
  `max-width:720px`, newer embedded at `max-width:1120px`, and the final global
  JS-ready collapsed/pinned block. Wide manual collapse activates only the
  incomplete final system.
- JavaScript only changes `is-rail-pinned`; profile-menu JavaScript only changes
  visibility and ARIA state. Neither causes horizontal offsets.

## Historical evidence

- `99479bcc` introduced the last complete model: `52px rail = 6px padding +
  40px control + 6px padding`; toggle and nav item shared one center.
- `9a93a5cc` preserved that model while moving widths into tokens.
- `b7f8c58f` introduced the regression by adding a late universal collapsed
  layer after rail tokens had changed, leaving a mix of 64px rail, 52px item,
  40px column and independent profile padding.
- `84de1792` and `b76c077d` fixed shell/playback width and compact header/state
  behavior respectively, but intentionally did not repair internal alignment.

## Decisions

### 1. Preserve current shell widths, restore the old invariant

Keep compact/expanded widths `64px / 176px`, but center one 40×40 interaction
cell inside the compact rail for toggle, navigation and profile.

**Rationale**: This retains valid recent work while restoring the proven simple
model. It removes the measured 64/52/40 mismatch without a broad rollback.

**Alternatives considered**:

- Revert the whole rail to 52px/184px: rejects valid newer shell, profile and
  playback work and expands scope.
- Use 44×44px cells: accessible but introduces a new geometry not requested or
  historically validated; current desktop controls consistently use 40px.
- Center only SVGs inside 52px items: leaves the oversized active background.

### 2. Final collapsed state owns complete compact geometry

The JS-ready `:not(.is-rail-pinned)` block defines width, height, centering and
icon placement for every compact action at every viewport width. Older embedded
media blocks may retain surface concerns, but not competing compact dimensions.

**Rationale**: Wide manual and narrow responsive collapse then resolve to the
same cascade. One state class maps to one complete visual contract.

**Alternative considered**: Add another later override; rejected because it
would create a fourth system and preserve the root cause.

### 3. No JavaScript or markup change

Retain current toggle/state/profile behavior and accessible labels.

**Rationale**: DOM and state tracing found no behavioral defect. A CSS-only fix
is the smallest root-cause change and avoids unrelated regression risk.

## UX/accessibility principles applied

- One axis and one target geometry reduce visual noise and pointer uncertainty.
- Active, hover and focus states occupy the same bounds.
- Focus remains visible inside the rail; accessible names and keyboard behavior
  are preserved.
- The compact header is removed from layout rather than visually hidden while
  reserving space.
- Historical reference is internal GRAF history; no competitor design or asset
  is copied.
