# Research: Одна колонка настроек без legacy gutter

## Current evidence

- At 1280×720 the outer sidebar occupies x=0–176 and cabinet main starts at
  x=176. Settings content starts at x≈469 instead of after main padding.
- `.settings-page` computes to `220px 770px` with a 32px gap. The legacy nav is
  `display:none`, but content remains explicitly assigned to column 2.
- The resulting 252px empty slot is visible on overview and shared by ordinary
  settings and billing templates; calendar uses the same older two-column
  contract.
- DOM exposes one visible navigation landmark, so the defect is layout
  skeleton rather than duplicated visible controls.

## History

- Features 135 and 151 intentionally used an inner settings navigation.
- Feature 159 selected one primary outer rail with mode switching.
- Commit `b7f8c58f` hid the legacy inner nav but retained its two-column grid and
  tests that require column 2.
- Features 168–172 adjust outer rail/native geometry and do not own settings
  content composition.

## Decisions

### 1. Complete the existing mode-switch migration

When `settings_mode` owns navigation in the outer shell, emit no inner nav and
place content in the first settings grid column.

**Rationale**: fixes the root cause once at shared boundaries and matches the
already selected product IA.

**Alternatives considered**:

- Center column 2 visually: preserves an unnecessary second-rail skeleton.
- Add another CSS override keyed by route: duplicates state and misses callers.
- Edit every settings/billing template: 21 repetitive changes for one macro
  invariant.

### 2. Preserve the real fallback — superseded by Feature 174

Feature 174 completed the caller trace and found no production consumer. The
macro and its standalone fallback were therefore removed; the outer cabinet
sidebar is the only settings navigation owner.

**Supersession rationale**: the additional evidence required by this decision
is now available in Feature 174.

### 3. No JavaScript or route changes

**Rationale**: computed styles, DOM and history prove the defect is shared
template/CSS composition. Existing route and state logic are correct.

## Product Design audit

- Strength: the outer settings rail has clear grouping, active state and a
  canonical return to meetings.
- Structural risk: the empty 252px slot makes the content appear detached and
  wastes nearly one quarter of the available workspace.
- Accessibility risk: hidden duplicate markup is removed from the document,
  reducing ambiguity for future partial updates; keyboard and semantic behavior
  still require runtime verification after implementation.
- Evidence limit: screenshot proves visual hierarchy, while focus order and
  landmark count require DOM/keyboard checks.
