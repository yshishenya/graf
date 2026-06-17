# Web Meeting Detail Evidence

Feature: `035-mvp-loop-live-evidence`

## Scope

This note documents the owner meeting detail surface without committing private
meeting content. It uses route truth plus existing safe fixtures.

## Production Route Status

- Base detail family: `https://rec.2brain.pro/meetings/{meeting_id}`
- Live detail proof: not opened against a private production meeting in this
  pass.
- Blocking reason: production owner review currently requires auth context;
  `/meetings` returned `401 missing_auth_context` without a commit-safe session.

## Fixture-Backed Coverage

Local detail coverage is represented by:

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q tests/integration/test_cabinet_meeting_detail.py
```

The existing fixture tests cover:

- Ready detail state with transcript/provenance/playback.
- Processing, failed, and partial detail truth.
- Foreign meeting denial without existence proof.
- Web detail shell with notes and recording/transcript tabs.
- Embedded desktop detail variant without native capture copy.
- Assistant/notes placeholder truth for deferred AI notes.

## Notes And Actions Truth

Launchable notes/action output is still blocked. The current web detail shell
must remain truthful by showing planned or placeholder assistant/notes states
instead of implying generated notes/actions exist.

## Readiness Classification

- Detail route family: `ready` in fixture-backed local coverage.
- Live private detail proof: `blocked`.
- Notes/action output: `blocked` until a dedicated notes/action slice or
  explicit MVP deferral is accepted.
