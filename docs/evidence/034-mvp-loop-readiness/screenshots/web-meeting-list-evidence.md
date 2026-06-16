# Web Meeting List Evidence

Feature: `034-mvp-loop-readiness`

Status: `metadata_safe_fixture_evidence`

## Safe Evidence

- Command: `uv run --extra dev pytest -q tests/unit/test_cabinet_web_shell.py tests/integration/test_cabinet_meeting_list.py tests/integration/test_cabinet_meeting_detail.py`
- Scope: verifies the web meeting list, desktop-embedded list route, access chips, future action slots, governance state, and absence of native recording controls in embedded web content.
- Boundary: fixture data only; no private meeting screenshot is committed.

## Live Capture Boundary

A metadata-safe browser screenshot can be added later if a reviewer needs visual evidence. The current evidence proves server-rendered IA and policy state through tests, not pixel-perfect live rendering.

## Forbidden Content Boundary

This note contains no raw audio, transcript from private meetings, private email, signed URL, token, local user path, or private Krisp screenshot.
