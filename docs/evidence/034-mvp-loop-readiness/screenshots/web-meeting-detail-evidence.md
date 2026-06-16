# Web Meeting Detail Evidence

Feature: `034-mvp-loop-readiness`

Status: `metadata_safe_fixture_evidence`

## Safe Evidence

- Command: `uv run --extra dev pytest -q tests/unit/test_cabinet_web_shell.py tests/integration/test_cabinet_meeting_list.py tests/integration/test_cabinet_meeting_detail.py`
- Scope: verifies tabs, transcript/playback/provenance, notes placeholder truth, assistant/template placeholders, speaker assignment lane, access/share/artifacts/delete governance, and desktop-embedded detail boundaries.
- Boundary: fixture transcript text is synthetic and safe; no private meeting screenshot is committed.

## Live Capture Boundary

The evidence is strong enough for local fixture behavior and clean-room IA review. It does not prove a live private meeting journey.

## Forbidden Content Boundary

This note contains no raw audio, transcript from private meetings, private email, signed URL, token, local user path, or private Krisp screenshot.
