# UX And Embedded Cabinet Requirements Checklist: Manual Media Upload UI

**Purpose**: Validate upload UX, accessibility, localization, responsive, and
desktop WebView boundary requirement quality before implementation
**Created**: 2026-07-07
**Feature**: [spec.md](../spec.md)

**Note**: This checklist tests requirements and plans, not implementation
behavior.

## Requirement Completeness

- [x] CHK001 Are browser and embedded desktop upload entry points both defined
  from the meetings workspace instead of a separate upload destination?
  [Completeness, Spec FR-001, FR-002, Research Upload Sheet Decision]
- [x] CHK002 Are required controls documented for file selection, title,
  duration, start, abort-before-acceptance, progress, error, accepted, and
  detail/list handoff states? [Completeness, Contract Upload Sheet Contract]
- [x] CHK003 Are duration metadata and manual fallback requirements complete
  enough to prevent an implementation that sends missing/guessed duration?
  [Completeness, Spec FR-005, FR-006, Research Duration Decision]
- [x] CHK004 Are no-file, invalid-duration, network, auth, server rejection,
  duplicate, accepted-processing-failure, and no-audio/unsupported-media cases
  covered? [Coverage, Spec US3, Spec Edge Cases, Contract Upload Sheet
  Contract]

## Requirement Clarity

- [x] CHK005 Is upload success clearly separated from transcript readiness and
  notes readiness? [Clarity, Spec FR-007, SC-004, Status Matrix dependency]
- [x] CHK006 Are cancellation semantics clear before and after server
  acceptance? [Clarity, Spec Clarifications, Spec FR-009]
- [x] CHK007 Is the embedded desktop boundary unambiguous that web content does
  not own native Record, Stop, active capture, local queue truth, permissions,
  diagnostics, or offline recovery? [Clarity, Spec FR-015, Contract Desktop
  Boundary Contract]
- [x] CHK008 Is "common video/meeting file" bounded by the MVP audio-first
  promise so implementation cannot add full video review scope? [Clarity, Spec
  FR-004, Out Of Scope]

## Requirement Consistency

- [x] CHK009 Do spec, plan, research, and contract agree that `/desktop/meetings`
  hosts embedded upload and `/desktop/upload` is not required in this slice?
  [Consistency, Research Upload Sheet Decision, Contract Desktop Boundary]
- [x] CHK010 Do browser and embedded surfaces share the same status meanings
  while allowing desktop-safe copy and route restrictions? [Consistency, Spec
  FR-014, Contract Browser And Embedded Entry Points]
- [x] CHK011 Are Russian-first copy requirements consistent with existing
  cabinet language and the instruction not to expose implementation labels?
  [Consistency, Spec FR-017, Plan Constraints]
- [x] CHK012 Are UI implementation constraints consistent with feature `058`:
  existing Jinja/static CSS/vanilla JS/HTMX only, no frontend build pipeline or
  UI kit? [Consistency, Plan Technical Context, Research XHR Decision]

## Accessibility And Responsive Quality

- [x] CHK013 Are keyboard, focus, screen-reader, progressbar/live-region,
  reduced-motion, non-color status, and compact-width requirements explicitly
  stated? [Non-Functional, Spec FR-016, Contract Accessibility]
- [x] CHK014 Are long Russian labels and error states required not to overlap or
  overflow in browser and embedded widths? [Non-Functional, Spec Edge Cases,
  Contract Accessibility]
- [x] CHK015 Are determinate and indeterminate upload progress requirements
  defined for assistive technology? [Non-Functional, Spec FR-008, Contract
  Upload Sheet States]

## Acceptance Criteria Quality

- [x] CHK016 Can browser upload success be measured without private media or
  screenshots? [Acceptance Criteria, Spec SC-001, Quickstart Scenario 1]
- [x] CHK017 Can embedded upload success be measured without claiming native
  desktop upload ownership? [Acceptance Criteria, Spec SC-002, Quickstart
  Scenario 2]
- [x] CHK018 Can safe failure states be verified through focused tests and
  no-secret scans? [Acceptance Criteria, Spec SC-003, Quickstart Scenario 4]
- [x] CHK019 Does the closeout gate require existing cabinet/desktop route
  regressions to keep passing? [Acceptance Criteria, Spec SC-005, SC-006,
  Quickstart Scenario 5]

## Dependencies And Assumptions

- [x] CHK020 Is dependency on `087` explicit enough that tasks do not replan
  one-track MediaScribe processing? [Dependency, Spec Clarifications, Plan
  Summary]
- [x] CHK021 Are deferred items complete for bulk import, resumable browser
  upload, direct object upload, native desktop upload bridge, full video review,
  and production deploy? [Coverage, Spec Out Of Scope, Plan Scale/Scope]
- [x] CHK022 Is live visual screenshot evidence intentionally out of scope
  unless safe synthetic evidence is added, while UI quality remains covered by
  focused rendering/accessibility checks? [Assumption, Plan Validation Plan,
  Quickstart]

## Notes

- Review result: 2026-07-07. Requirement quality is sufficient for task
  generation after UX/accessibility/embedded boundary review; no blocking gaps
  found.
