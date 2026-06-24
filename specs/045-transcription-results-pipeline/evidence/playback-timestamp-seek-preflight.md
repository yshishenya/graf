# Playback Timestamp Seek Preflight

**Feature context**: `045-transcription-results-pipeline`
**Prepared**: 2026-06-24
**Candidate follow-up**: `046-meeting-playback-timestamp-seek`

## Purpose

This note prevents the MVP playback gap from being hidden inside the already
implemented `045` transcription/result pipeline. It is not a new Spec Kit
feature spec and does not start implementation.

`045` proves that processed meetings can expose transcript/diarization
availability, timestamp labels, speaker/source-role truth, and a playback shell
in web plus desktop review. It does not prove PRD-level interactive audio
playback linked to transcript timestamps.

## Current Truth

- `045` is still local dirty branch state and is not committed, PR-reviewed,
  merged, released, or deployed.
- Existing cabinet contract/unit/web-shell tests prove timestamp labels,
  speaker/source-role mapping, playback availability state, and the presence of
  a `detail-playback` shell.
- Current web HTML renders transcript timestamps as text and renders a playback
  bar, but it does not expose segment seek controls, waveform, retained-audio
  source selection, or a proven play/pause/seek runtime.
- PRD meeting detail requires player controls and transcript timestamp seek
  when audio is available.

## Start Conditions For 046

Do not start `046` implementation in this dirty `045` worktree.

Start the follow-up only after one of these is true:

1. `045` is committed, PR-reviewed, merged, and the new slice can branch from
   current `origin/master`.
2. The owner explicitly approves creating a separate dependent worktree from
   the unmerged `045` branch and accepts that it is stacked on 045.

Before creating the new Spec Kit feature, verify:

- `specs/046-*` does not already exist.
- The chosen base has the final 045 review-state API and cabinet HTML shape.
- The worktree is clean or its unrelated changes are explicitly accounted.
- The active feature is updated through the Spec Kit branch/feature hook, not
  by editing `.specify/feature.json` by hand.

## Candidate User Stories

### US1: Play Retained Meeting Audio From Review

As a meeting owner, I want to play retained meeting audio from the meeting
detail page so that I can verify the transcript against the source recording.

Independent proof:

- For a fixture processed meeting with retained audio allowed by policy, web
  review and desktop embedded review expose play/pause, current time, duration,
  speed, and seek controls.
- For a meeting without retained or authorized audio, the player explains the
  unavailable state without breaking transcript review.

### US2: Seek From Transcript Timestamps

As a meeting owner, I want clicking a transcript timestamp or segment to seek
playback to that segment start time so that review is fast and precise.

Independent proof:

- Clicking a transcript timestamp updates the player time to the segment start
  time in browser runtime checks.
- Keyboard focus and activation work for transcript timestamp controls.
- Seek behavior does not expose raw audio URLs, signed URLs, private paths, or
  transcript content in logs/evidence.

### US3: Keep Playback Policy And Provenance Truthful

As a privacy/security owner, I need playback to respect access, retention,
deletion, and artifact egress policy so that processed results do not leak
audio outside approved boundaries.

Independent proof:

- Unauthorized, deleted, audio-purged, transcript-only, and no-audio states do
  not expose playable audio.
- Status and diagnostics remain metadata-only.
- Desktop embedded review matches web review for player availability and
  blocked/unavailable states.

## Candidate Scope

In scope:

- Server-mediated playback endpoint or controlled stream/download path for
  policy-authorized retained audio.
- Review-state contract additions for playback source availability, current
  policy state, duration, allowed speeds, and unavailable reasons.
- Web cabinet player controls.
- Desktop embedded player parity.
- Transcript segment controls with timestamps as seek targets.
- Playwright/runtime checks for desktop and mobile web cabinet viewports.
- Contract tests for no secret/content egress.

Out of scope unless explicitly included:

- Transcript editing.
- Speaker-label editing.
- Full waveform generation from raw audio if it requires a separate media
  processing pipeline. A simple timeline/progress bar is acceptable for MVP if
  the owner accepts it.
- Video review.
- Public sharing/export redesign.
- Real echo/noise suppression. That remains `044`.

## Likely Files To Inspect First

- `docs/prd-voice-layer-final.md`
- `apps/server/src/twobrain_rec_server/cabinet/web.py`
- `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- `apps/server/src/twobrain_rec_server/api/cabinet.py`
- `apps/server/src/twobrain_rec_server/cabinet/egress.py`
- `apps/server/src/twobrain_rec_server/api/schemas.py`
- `apps/server/tests/contract/test_cabinet_contract.py`
- `apps/server/tests/unit/test_cabinet_view_models.py`
- `apps/server/tests/unit/test_cabinet_web_shell.py`
- `apps/server/tests/contract/test_cabinet_no_secret_content_egress.py`
- macOS embedded cabinet/WebKit tests or harnesses under `apps/macos` once the
  server review contract is updated.

## Candidate Validation

Minimum local validation for 046 should include:

- API/schema contract tests for playback availability and unavailable reasons.
- Unit tests mapping transcript segment start seconds to accessible seek
  controls.
- Browser runtime checks for play/pause/seek controls and transcript timestamp
  activation in web and desktop embedded routes.
- Mobile viewport check for no horizontal overflow.
- No-content/no-secret egress tests for playback status and diagnostics.
- Full `infra/scripts/ci-local.sh` before PR readiness.

Production proof should happen only after release/deploy approval and should
record metadata-only evidence: player available/unavailable state, timestamp
seek success, duration/current-time metadata, access/deletion policy outcome,
and no raw audio, transcript text, signed URLs, credentials, or private meeting
content.

## Decision Needed

For the full MVP claim, the owner must choose one:

1. Implement and prove `046-meeting-playback-timestamp-seek` before MVP.
2. Explicitly defer interactive playback/timestamp seek from a narrower pilot
   MVP and state that the pilot only proves transcript display, not audio-linked
   review.
