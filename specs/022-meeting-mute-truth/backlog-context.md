# Backlog Context: Meeting-App Mute Truth

Date: 2026-06-04

This file preserves the git-cleanup analysis that led to creating
`022-meeting-mute-truth`.

GitHub backlog issue: https://github.com/yshishenya/crisp/issues/137

## Source Branch Analysis

The old branch `009-respect-meeting-mute` was reviewed during git cleanup.

Findings:

- The branch has exactly one unique commit ahead of `master`:
  `603f457 docs: Track meeting mute recording issue`.
- The commit is documentation/specification only. It does not include code,
  tests, implementation plans, or completed Spec Kit tasks.
- The old specification status is `Draft - clarification/research required`.
- The old specification contains an unresolved clarification marker for the
  canonical source of meeting-app mute truth.
- The old checklist is intentionally incomplete because clarification is needed.
- The branch forked before later merged work. A raw merge is not safe because it
  can reintroduce stale tree state from before the server ingest and issue-canon
  merges.

Decision:

- Do not raw-merge `009-respect-meeting-mute`.
- Do not delete the concern from product memory.
- Preserve the useful product context in this `022` backlog slice.
- Treat `022` as the canonical future feature record.

## Original Problem Statement

During manual local recording validation, the user found that when the
microphone is muted inside a meeting application, local microphone audio can
still appear in the local recording.

This creates a privacy and capture-truth issue:

- The user may believe muted speech is not part of the meeting.
- Local recording may still capture that speech.
- Existing local recording acceptance proves visible recording and artifact
  persistence, not meeting-app mute correctness.

## Product Boundary

The accepted local recording slices remain valid for their own scope:

- `007`: visible manual recording and one-action stop.
- `008`: local recording persistence and truthful saved/degraded/failed local
  artifact state.
- `010`: MediaScribe-ready local artifact format with `manifest.json`,
  `mic.wav`, `incoming.wav`, role mapping, and metadata-only diagnostics.

Those slices must not be described as proving that meeting-app mute intent is
respected. This backlog slice exists to close that gap later.

## Required Future Workflow

Before implementation:

1. Run `$speckit-clarify 022`.
2. Resolve the canonical mute-truth source.
3. Resolve unsupported-target behavior.
4. Resolve muted interval artifact truth.
5. Resolve user-facing limitation copy.
6. Resolve QA target matrix.
7. Run `$speckit-plan 022`.
8. Run high-risk checklists for privacy, driver/audio, recording, UX, and QA.
9. Generate tasks and analyze before any code changes.

## Known High-Risk Questions

- Can meeting-app mute state be observed directly for the first target matrix?
- If not, is post-mute routed audio enough to infer safe local mic capture?
- Should unsupported targets block recording or produce degraded/not-accepted
  artifacts?
- How should known muted intervals be represented in local artifacts?
- What exactly should the app say when mute truth is unavailable?
- How should hardware mute, macOS input mute, product pause, and meeting-app
  mute be distinguished?
- How does this interact with `020-speaker-to-mic-leakage`, where far-end audio
  can contaminate the local mic track?

## Git Hygiene Notes

If future work needs old branch content, cherry-pick or copy only the useful
documentation from `603f457` onto a fresh branch from current `master`. Do not
merge `009-respect-meeting-mute` directly.
