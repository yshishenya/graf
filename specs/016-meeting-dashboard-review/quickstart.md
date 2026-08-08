# Quickstart: Meeting Dashboard Review

Feature: `016-meeting-dashboard-review`
Date: 2026-06-16

## Prerequisites

- Work from repository root.
- Use the server development environment under `apps/server`.
- Do not commit raw authenticated Krisp screenshots or private meeting content.
- Use seeded/sanitized meeting content for UI screenshots and tests.

## Local Test Commands

```sh
cd apps/server
uv run --extra dev pytest -q
uv run --extra dev ruff check .
```

Focused expected tests for this feature:

```sh
cd apps/server
uv run --extra dev pytest -q \
  tests/contract/test_cabinet_contract.py \
  tests/contract/test_cabinet_no_secret_content_egress.py \
  tests/integration/test_cabinet_meeting_list.py \
  tests/integration/test_cabinet_meeting_detail.py \
  tests/unit/test_cabinet_view_models.py \
  tests/unit/test_cabinet_web_shell.py
```

## Scenario 1: Authorized Meeting List

1. Seed at least one meeting in each UI state: ready, processing, failed or
   blocked, and partial/degraded.
2. Request `GET /api/v1/cabinet/meetings` with valid user/workspace/device auth
   context.
3. Verify only authorized workspace meetings appear.
4. Verify each row includes title, date/time, duration, source, status, primary
   action, and governance/future-action state.
5. Verify no transcript text, secrets, signed URLs, external job IDs, raw audio,
   or live paths appear in the list response.

## Scenario 2: Ready Meeting Detail

1. Seed a processed meeting with transcript and diarization segments.
2. Request `GET /api/v1/cabinet/meetings/{meeting_id}` as the owner.
3. Verify transcript segments are ordered, timestamped, and include speaker
   labels and source-role truth.
4. Verify speaker lanes/talk-time state derives from diarization data.
5. Verify notes are unavailable or sample-only unless explicitly seeded as safe
   fixture content.
6. Verify share/export/download/delete/template/assistant controls are present
   as gated/non-mutating states.

## Scenario 3: Processing Or Degraded Detail

1. Seed a meeting with processing workflow/job state but no imported transcript.
2. Open the detail API and web route.
3. Verify the page shows waiting/processing truth and does not display fake
   transcript, notes, playback success, share success, export success, or
   deletion success.
4. Repeat with failed/blocked/partial status and verify the user-facing reason
   is content-safe.

## Scenario 4: RLS And Privacy-Preserving Denial

1. Seed a second workspace and meeting not owned by the active auth context.
2. Request the foreign meeting detail URL from the active user.
3. Verify the response is 404 or privacy-preserving denial and does not include
   the foreign title, transcript text, source metadata, or existence proof.

## Scenario 5: Web Cabinet Shell

1. Start the FastAPI development server.
2. Open `/meetings` in a browser with valid development auth/session context.
3. Verify the meeting list renders with search/filter/sort controls and no text
   overflow at desktop browser width.
4. Open a ready meeting route and verify `Notes` plus `Recording & Transcript`
   tab model, transcript list, speaker timeline, playback shell, and gated
   governance controls.
5. Open a processing meeting route and verify the truthful waiting state.

## Scenario 6: Desktop Embedded Route Boundary

1. Open `/desktop/meetings` and `/desktop/meetings/{meeting_id}`.
2. Verify the route renders the same server-owned product state as browser
   cabinet where allowed.
3. Verify the server-rendered embedded content contains no `Record`, `Stop`,
   device selector, screen recorder picker, noise/accent controls, local path,
   raw file access, or diagnostics export controls.
4. Verify unavailable/offline copy is bounded and does not hide native capture
   truth.

## Scenario 7: Reference And Evidence Hygiene

1. Confirm tracked `specs/016-meeting-dashboard-review/research/` artifacts
   contain only sanitized notes or public screenshots.
2. Confirm private raw captures remain under:

```text
<private-reference-captures>/2brain-rec/016-meeting-dashboard-review/2026-06-16/
```

3. Scan implementation screenshots, logs, problem responses, and validation
   output for forbidden content:
   - credentials;
   - tokens;
   - signed URLs;
   - raw audio;
   - live local paths;
   - real private transcript text;
   - private email addresses/account identifiers.

## Done When

- All focused cabinet tests pass.
- Full server pytest suite and Ruff pass or documented pre-existing failures
  are isolated.
- Browser screenshots show list, ready detail, processing detail, and
  responsive embedded route without overlap.
- Tracked evidence is metadata-only and sanitized.
- Future actions are visible in stable locations but do not mutate state.
