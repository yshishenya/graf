# Playback And Speaker Review Contract

## Read projection

- `transcript.segments[]` and `transcript.speaker_turns[]` keep existing timing/text fields and add a provider-neutral `speaker_key`.
- `speakers.speakers[]` keeps its existing `speaker_key`, intervals, and talk share. `label` is the saved display name when present, otherwise the canonical automatic label.
- `speakers.can_rename` is true only for the meeting creator or an active workspace owner/admin.
- Browser and desktop-embedded meeting detail render from the same projection.

Synthetic example:

```json
{
  "transcript": {
    "speaker_turns": [
      {
        "turn_id": "synthetic-turn",
        "speaker_key": "speaker_00",
        "speaker_label": "Мария",
        "start_seconds": 12.5,
        "end_seconds": 18.0,
        "text": "synthetic text"
      }
    ]
  },
  "speakers": {
    "can_rename": true,
    "speakers": [
      {
        "speaker_key": "speaker_00",
        "label": "Мария",
        "segments": [{"start_seconds": 12.5, "end_seconds": 18.0}]
      }
    ]
  }
}
```

## Timeline interaction

1. The main range and each lane expose one identical inner scale from zero to playable duration.
2. A pointer position on a lane resolves to `duration * boundedRatio` on that inner scale.
3. Every seek is clamped, updates the audio element, synchronizes all playheads and active lanes, and may request one transcript follow.
4. Active lanes are all lanes containing the current time. Current transcript state uses the latest turn whose start is not after the current time, falling back to the first turn.
5. Deliberate seeks center that turn without transferring focus; ordinary playback never continuously scrolls.

## Speaker-name mutation

Authenticated cabinet form routes:

```text
POST /meetings/{meeting_id}/speakers/{speaker_key}
POST /desktop/meetings/{meeting_id}/speakers/{speaker_key}
```

Form fields:

- `csrf_token`: required existing web CSRF token.
- `display_name`: trimmed UTF-8 text, zero through 80 visible characters; empty clears the override.

Outcomes:

- `303` back to the same meeting detail after a successful set/clear.
- Safe `403` for authenticated viewers without edit capability.
- Safe `404` for an inaccessible meeting or speaker key outside the current review.
- `422` for invalid name content.
- No response or audit payload contains transcript/audio content.

## Compatibility

- Existing clients may ignore additive `speaker_key` and `can_rename` fields.
- Existing automatic labels remain the fallback and imported provider labels are not mutated.
- Playback without speaker data and transcript without playback preserve their current usable states.
