# Analyze: macOS Dev Channel and Native Home

**Date**: 2026-08-17

## Consistency result

- Constitution: PASS. Capture remains system-audio-first, permissions stay
  native, and no TCC or legacy-driver workaround is introduced.
- Spec/plan: PASS. Production release identity is preserved; Dev is loopback,
  isolated, stable-signed, and no-feed.
- Tasks: PASS. Static contracts precede channel/storage/build/native changes;
  quickstart, native smoke, and fast CI are named closeout gates.
- Ownership: PASS. Features 095, 105, 130, 152, and 153 remain owners of their
  historical permission, public-release, local-workflow, and release-process
  contracts.

## Blocking findings

None. The only operational limitation is the existing manual native smoke
dependency on an unlocked Mac; it is evidence-gated and does not justify a TCC
workaround.

## Implementation review

- Correctness: PASS. `GrafAppChannel` is the single namespace decision point;
  production and legacy fallback behavior remain unchanged, while Dev never
  reads the legacy `2brain Rec` path.
- Permissions and privacy: PASS. The bundle keeps native usage descriptions,
  carries the microphone entitlement on both outer and nested code, requires a
  named signer, and contains no TCC reset, profile, or audio-driver workaround.
  Dev uses `LSEnvironment` for an explicitly supplied loopback origin and
  blanks inherited credential variables before the local configuration reads
  them.
- Signing and updater: PASS. The Dev bundle uses `pro.2brain.graf.dev`, checks
  its final signature and designated requirement, omits `SUFeedURL` and
  `SUPublicEDKey`, and refuses designated-requirement drift on update. The
  production installer and Sparkle configuration were not changed.
- Native navigation and accessibility: PASS. Home reuses the existing safe
  meetings fallback, has a disabled state, tooltip, keyboard shortcut, and
  stable accessibility identifier; Back/Forward/Reload guards are unchanged.
- Ponytail review: PASS. No new router, persistence layer, dependency, or
  duplicate storage abstraction was added; all touched stores reuse one small
  channel helper.

## Remaining evidence

- Focused Swift and static checks pass. The repository fast lane was repeated
  after the final native-executable packaging correction: 1100 tests plus lint
  and Python compile passed. Native computer-use smoke is complete for both
  grants and same-identity update/relaunch; no TCC workaround was used.
- The slice is locally validated but still awaits the implementation
  commit/PR. Public notarization, appcast mutation, production deployment, and
  release publication remain separate approval-gated work owned by Features
  105/130/153.
