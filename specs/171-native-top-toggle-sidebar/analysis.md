# Review: Единый верхний toggle и аккуратный rail

## Lane

`high-risk-feature`: shared native/web navigation geometry and accessibility.
Capture, auth, permissions, storage, AI and deployment remain out of scope.

## Correctness review

- Native disclosure is owned by one shared `inspectorDisclosureHeader` helper;
  both collapsed and expanded modes render one top-trailing control.
- Expanded native content reserves the header row before its `ScrollView`, so
  the scrollable content cannot cover the disclosure target.
- Web rail initialization reuses `setRailPinned`, applies one 981px default to
  both surfaces, and remains idempotent through `data-rail-ready`.
- The root cause of the reported auto-collapse was removed: navigation and
  outside-content click listeners no longer mutate the user's manual rail
  state. Escape remains an explicit keyboard close action.
- Compact web mode removes the workspace-header layout slot while retaining
  the toggle, profile, update/download and navigation targets.

## Accessibility and UX review

- Native target remains 44 px with stable accessibility identifiers, labels,
  hints and help text.
- Web toggle updates `aria-expanded`, `aria-label`, `title` and tooltip copy in
  one state transition and restores focus after activation.
- Compact navigation anchors carry explicit accessible names after their visual
  labels are hidden; active-page semantics and hrefs are unchanged.
- Existing reduced-motion, focus-visible and forced-colors rules remain in
  effect. No onboarding, persistence, analytics or new dependency was added.

## Visual review

The in-app Browser matrix passed at 1280×700 and 900×700 for the embedded
surface, including content click, settings navigation, two-toggle behavior,
hidden compact header and horizontal-overflow checks. Computer Use confirmed
the native top slot, no overlap with the title/settings/capture content and
same-position re-collapse in `GRAF Dev`.

## Ponytail review

No actionable simplification finding remains. The patch reuses the existing
state helper, button, CSS variables and test harness; it deletes obsolete
listeners and an empty compact slot rather than introducing a coordinator,
storage or dependency.

## Evidence and limitations

Focused evidence is recorded in `quickstart.md` and contains only dimensions,
states, labels and counts. No meeting text, audio, credentials or private
screenshots are committed. Full CI, production deployment and public macOS
packaging are intentionally deferred to the release train that owns this
isolated layout slice.
