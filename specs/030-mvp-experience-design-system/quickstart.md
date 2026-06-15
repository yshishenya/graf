# Quickstart: Validate MVP Experience Design System Plan

This quickstart validates design-readiness artifacts. It does not run or
approve production UI implementation.

## Prerequisites

- Current branch/worktree points at `030-mvp-experience-design-system`.
- `specs/030-mvp-experience-design-system/spec.md` has five accepted
  clarification bullets.
- Figma access is available or StitchFlow fallback is available.
- Do not use real meeting content, credentials, API keys, signed URLs, or live
  local paths in prototype artifacts.

## 1. Verify Spec Kit Paths

```sh
bash .specify/scripts/bash/check-prerequisites.sh --json --paths-only
```

Expected:

- `FEATURE_DIR` is `specs/030-mvp-experience-design-system`.
- `FEATURE_SPEC` points to this feature's `spec.md`.

## 2. Verify Required Planning Artifacts

```sh
test -f specs/030-mvp-experience-design-system/plan.md
test -f specs/030-mvp-experience-design-system/research.md
test -f specs/030-mvp-experience-design-system/data-model.md
test -f specs/030-mvp-experience-design-system/quickstart.md
test -f specs/030-mvp-experience-design-system/contracts/route-visibility-contract.md
test -f specs/030-mvp-experience-design-system/contracts/cross-surface-status-contract.md
test -f specs/030-mvp-experience-design-system/contracts/prototype-handoff-contract.md
```

Expected: all commands exit successfully.

## 3. Check Clarification And Placeholder Hygiene

```sh
rg -n "T[O]DO|T[B]D|\\[(FEATURE|DATE)\\]" \
  specs/030-mvp-experience-design-system/spec.md \
  specs/030-mvp-experience-design-system/plan.md \
  specs/030-mvp-experience-design-system/research.md \
  specs/030-mvp-experience-design-system/data-model.md \
  specs/030-mvp-experience-design-system/contracts
```

Expected: no matches in finalized planning artifacts.

## 4. Validate Route Visibility Contract

Review [route-visibility-contract.md](./contracts/route-visibility-contract.md)
and confirm:

- every embedded route is account/upload/status/review/basic-settings related;
- broad admin, billing, team management, public sharing, exports/downloads,
  detailed audit, help/legal, and full video UX are browser-only, handoff, or
  deferred;
- unknown routes default to browser handoff or hidden in desktop;
- no embedded route owns active recording, Stop, permissions, local queue truth,
  or capture recovery.

Expected: 100% of launch-critical routes have one classification.

## 5. Validate Cross-Surface Status Contract

Review [cross-surface-status-contract.md](./contracts/cross-surface-status-contract.md)
against desktop and web prototype screens.

Expected:

- app and web show the same meaning for recording saved, queued, uploading,
  uploaded, audio extraction, transcription, transcript ready, notes ready,
  degraded/failed, deleted, and access denied;
- uploaded never means transcript ready;
- transcript ready never means notes ready;
- deletion copy is limited to what `2brain Rec` controls.
- deletion and retention notes account for local buffers, server records,
  object storage, workflow payloads, backups, MediaScribe, Langfuse,
  diagnostics, post-egress limits, and unreachable clients where relevant.
- uploaded-media review states do not imply separate microphone/system tracks
  or speaker separation unless the source provenance supports it.

## 6. Validate Owner Value Loop Prototype

Walk the clickable prototype from both desktop and browser entry points:

1. first-run/sign-in or signed-out local policy state;
2. desktop idle/ready;
3. active recording and Stop;
4. local saved/queued status;
5. upload/transcription status in app and web;
6. manual upload for audio and common video/meeting file;
7. transcription in progress;
8. completed meeting review;
9. degraded/failure state;
10. browser-only handoff;
11. deletion/access entry point.
12. source/track provenance for desktop recording and manual upload.

Expected: at least 95% of primary MVP journey steps can be completed without
inventing missing screens or states.

## 7. Validate Prototype Handoff

For Figma:

- record file/link;
- record key frame names;
- record clickable paths;
- record design-system/component status.

For StitchFlow fallback:

- record project id and screen ids;
- save `DESIGN.md` status;
- save screenshots and HTML/code checkpoint;
- inspect `download-project.json` or equivalent warnings.

Expected: every external artifact has a matching repo handoff reference.

## 8. Brand-Distance And Visual QA

Review all visual artifacts:

- no copied Krisp UI expression, copy, icons, assets, screenshots, or
  proprietary behavior;
- active recording indicator and Stop remain visible in desktop states;
- text does not overflow in compact desktop surfaces;
- light/dark themes preserve contrast;
- status is not communicated by color alone.

Expected: brand-distance review has zero copied Krisp elements and no blocking
visual QA defects.

## 9. Next Spec Kit Commands

Recommended next steps after this plan:

```text
$speckit-checklist
$speckit-tasks
$speckit-analyze
```

Implementation remains blocked until checklist/tasks/analyze gates pass.
