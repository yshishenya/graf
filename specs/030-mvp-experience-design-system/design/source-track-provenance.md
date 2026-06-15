# Source And Track Provenance

## Provenance Types

| Type | User-facing meaning | Forbidden implication |
|---|---|---|
| `desktop_separate_tracks` | Captured by 2brain Rec with local mic and incoming/system audio tracks | Does not imply participant notice or cloud backup |
| `uploaded_mixed_audio` | User uploaded a file with mixed audio | Must not imply speaker separation or dual-track quality |
| `uploaded_extracted_audio` | Audio was extracted from a video/meeting container | Must not imply full video review |
| `no_usable_audio` | File has no usable audio | Must not imply processing can continue |
| `unknown_track_separation` | Source does not prove separation | Must not imply transcript quality guarantees |

## Placement

- Meeting list row metadata.
- Meeting review header.
- Transcript/playback provenance block.
- Upload confirmation and failure states.
- AI answer drawer when source quality affects answer confidence.
- Export/download modal when exported artifacts do not include all original
  tracks.

## Copy Principle

Say what is known about the media source and avoid claims the artifact cannot prove.

## Display Rules

| Placement | Required copy shape | Example pattern |
|---|---|---|
| Meeting row | Short source label plus status | `Desktop recording - separate local tracks` |
| Review header | Source label plus detail tooltip | `Uploaded file - mixed audio, speaker labels may be limited` |
| Transcript pane | Confidence/provenance notice near transcript search | `Transcript generated from extracted audio` |
| Playback strip | Channel/source label | `Mixed audio` or `Mic + system tracks` |
| Upload confirmation | What will happen next | `We will extract audio, then transcribe it` |
| Failure state | What is known and next action | `No usable audio found. Upload another file.` |

## Forbidden Claims

- Do not promise speaker diarization quality for uploaded mixed audio.
- Do not imply a video review experience when only audio extraction is in scope.
- Do not imply local-only recordings are backed up before upload succeeds.
- Do not imply deletion covers external integrations, user-downloaded exports,
  or third-party systems outside 2brain Rec control.
