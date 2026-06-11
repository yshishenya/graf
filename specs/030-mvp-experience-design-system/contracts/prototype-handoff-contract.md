# Contract: Prototype And Handoff Evidence

## Purpose

Define the minimum evidence required for the visual prototype to be accepted as
implementation-ready input while keeping repository Spec Kit artifacts as the
product source of truth.

## Preferred Source

Figma is preferred for:

- static visual pack;
- design system components/tokens;
- clickable key flows;
- review comments and visual iteration.

The design should stay compatible with a free Figma account when possible.

## Fallback Source

StitchFlow may be used when Figma access, plan limits, connector availability,
or workflow friction blocks delivery.

When StitchFlow is used, record:

- Stitch project id;
- screen ids and names;
- `DESIGN.md` upload/design-system status;
- exported screenshots;
- exported HTML/code checkpoint path;
- prototype/linking status;
- `download-project.json` or equivalent manifest path;
- warnings, missing screens, and external runtime dependencies.

## Repo Handoff Requirements

External design/prototype artifacts must be mirrored by repository references:

- screen inventory;
- owner value loop flow;
- route visibility matrix;
- cross-surface status model;
- component inventory;
- copy/status principles;
- accessibility and localization notes;
- clean-room brand-distance review;
- launch backlog map.

## Required Prototype Paths

The clickable prototype must cover:

1. First-run/sign-in or signed-out local policy state.
2. Desktop idle/ready state.
3. Active recording and one-action Stop.
4. Recording stopped and local saved/queued status.
5. Upload queue/current status in app and web.
6. Embedded cabinet subset entry.
7. Manual upload for audio and common video/meeting file.
8. Audio extraction/transcription in progress.
9. Meeting review complete.
10. Partial/degraded or failed processing.
11. Browser-only handoff.
12. Deletion/access entry point.

## Forbidden Prototype Content

Prototype artifacts must not include:

- real private meeting content;
- raw audio;
- secrets, tokens, passwords, signed URLs, API keys, device credentials;
- live local filesystem paths;
- copied Krisp UI, copy, icons, screenshots, assets, or proprietary behavior;
- claims that implementation or production rollout is already complete.

## Visual QA Requirements

Before accepting the prototype:

- inspect desktop and compact layouts for text overflow;
- verify light/dark contrast;
- verify non-color status cues;
- verify active recording and Stop are not obscured;
- verify browser-only routes do not appear as embedded desktop screens;
- verify clickable paths match the owner value loop;
- record visual QA notes in the handoff artifact.
