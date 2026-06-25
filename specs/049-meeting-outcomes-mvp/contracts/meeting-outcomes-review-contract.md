# Contract: Meeting Outcomes Review

## Scope

The existing meeting list/detail APIs and server-rendered cabinet pages expose
meeting outcome state after access and lifecycle checks. The macOS app consumes
the same embedded server route, so no separate native outcome payload is
allowed for MVP.

## API Response Shape

`MeetingReviewResponse` and `MeetingListItem` continue exposing
`notes_action_truth` for compatibility. 049 extends the contract with stored
outcome content for allowed review responses.

Required detail fields:

```json
{
  "notes_action_truth": {
    "summary": {
      "state": "available",
      "label": "Summary ready",
      "reason": "Stored outcome content is available.",
      "readiness_impact": "closes_gap",
      "copy_key": "notes.summary.available",
      "items": [
        {
          "category": "summary",
          "sequence": 0,
          "text": "stored user-visible text",
          "truth_label": "supported",
          "source_refs": [
            {
              "transcript_segment_id": "00000000-0000-0000-0000-000000000000",
              "start_seconds": 12.5,
              "end_seconds": 18.0,
              "speaker_label": "Speaker 1",
              "source_role": "incoming",
              "evidence_kind": "segment"
            }
          ]
        }
      ]
    },
    "decisions": { "state": "not_found", "items": [] },
    "action_items": { "state": "not_inferable", "items": [] },
    "followups": { "state": "available", "items": [] },
    "risks": { "state": "available", "items": [] },
    "questions": { "state": "available", "items": [] },
    "evidence": { "state": "available", "items": [] },
    "source_basis": "stored_output",
    "provenance": {
      "generator_kind": "deterministic_extractive",
      "generator_version": "outcomes-extractive-v1",
      "generated_at": "2026-06-25T00:00:00Z",
      "latency_ms": 1200
    }
  }
}
```

The implementation may keep exact Pydantic class names local, but the contract
must preserve these semantics:

- Available category content is stored and reviewable.
- `not_found` and `not_inferable` states count as launch-safe stored category
  truth when generated and persisted.
- `processing`, `blocked`, `unavailable`, `unsafe`, and `deferred` never close
  the MVP blocker.
- Factual items include transcript segment or timestamp evidence when evidence
  exists.
- Detail responses for denied/unauthenticated/not-found meetings expose no
  outcome content and no more outcome existence detail than existing meeting
  authorization allows.

## Category States

Allowed category states:

- `available`
- `not_found`
- `not_inferable`
- `processing`
- `blocked`
- `unavailable`
- `deferred`
- `unsafe`

Readiness impact mapping:

- `closes_gap`: only when stored launch-safe outcome content or explicit stored
  `not_found`/`not_inferable` category truth exists for MVP-required
  categories.
- `keeps_gap_open`: processing, blocked, unsafe, unavailable, deferred, or
  provider summary without stored content.
- `non_blocking`: category is outside MVP or intentionally optional in a given
  status view.

## Web And Embedded Rendering

The web cabinet and `/desktop/meetings/{meeting_id}` embedded route must render
the same:

- category labels and states;
- item text for allowed users;
- source/timestamp evidence;
- safe unavailable/processing/blocked copy;
- no download/export coupling unless policy explicitly allows an artifact.

The bottom playback bar and transcript timestamps remain usable while outcomes
are processing, partial, blocked, or long.

## Forbidden In Responses And Evidence

The playback route and generic status endpoints must not include outcome text.
Diagnostics, release evidence, screenshots, and logs must not contain:

- transcript text;
- generated outcome text;
- prompts with meeting content;
- model responses;
- raw audio;
- signed URLs;
- storage object keys;
- credentials;
- private local paths;
- private meeting identifiers.
