# Recording Package v5 Contract

## Identity

```text
schemaVersion          = local-recording-manifest.v5
mediaScribeSourceMode  = single_wav_v1
server source kind     = initial_mixed_recording
```

One package represents one immutable, first-party conversation timeline. It is not a container for separate ASR tracks.

## Exact Final Members

| File | Local role | Transport role | Required | Use |
| --- | --- | --- | ---: | --- |
| `manifest.json` | metadata | `manifest` | yes | package identity, consent, integrity, lifecycle and safe timing metadata |
| `meeting-transcription.wav` | `mixed_meeting_audio` | `media` | yes | sole transcription source |
| `meeting-review.m4a` | `review_playback` | `playback` | yes | playback candidate only |

Unknown audio roles/files, `mic.wav`, `incoming.wav`, raw source copies, `.partial` files, duplicate roles and malformed members are rejected for v5.

## Canonical WAV

`meeting-transcription.wav` must be a complete RIFF/WAVE file with:

- signed PCM 16-bit little-endian;
- mono, exactly 16,000 Hz;
- a nonempty finalized data chunk;
- valid frame count, byte count, SHA-256, duration and zero timeline start;
- an exact relationship to the v5 shared output timeline.

The file is generated directly from canonical 48 kHz PCM through a stateful native sample-rate converter. Completed AAC must never be decoded to make this WAV. A readable silent period remains part of the timeline; silence is not a presence failure.

## Playback M4A

`meeting-review.m4a` must be a complete M4A/MP4 file with:

- one AAC-LC audio stream;
- mono, exactly 48,000 Hz;
- no video, data, subtitle or attachment stream;
- valid final container, byte count, SHA-256 and declared duration;
- same canonical PCM timeline as WAV, allowing only separately recorded AAC encoder priming/remainder.

It is never staged for MediaScribe, never used to recreate WAV and never substitutes for a missing/invalid canonical WAV.

## Timeline Contract

Every source batch presented to the writer has source identity, PTS, duration, actual sample rate, channel count, discontinuity and route generation. The writer fixes a common epoch, normalizes source frames to mono 48 kHz, and uses one monotonically increasing frame index. It fills known gaps with silence and trims overlaps deterministically.

Queue overflow, unsafe timestamp, uncomparable clock, unsupported conversion, unexpected route generation, unbounded gap or finalization failure is a typed integrity outcome. It is not repaired with sample-count pairing, independent wall-clock padding or silent dropping.

For the 60-minute controlled acceptance, WAV, decoded M4A and transcript timeline have no unexplained divergence greater than 100 ms. AAC container priming/remainder is measured and recorded as metadata separately.

## Mixing Contract

One fixed, versioned profile mixes normalized local/system PCM before fan-out. It may use bounded gain and peak protection only to preserve intelligibility and avoid clipping. It must preserve natural silence and double-talk; it must not apply AEC, voice processing, echo cleanup, VAD trimming, amplitude presence gates, participant mute or a second retained audio representation.

All user-visible speech quality is tested at the final WAV/result boundary. No hidden text de-duplication may turn an invalid audio result into an accepted recording.

## Atomic Finalization

1. Create protected temporary writer outputs outside the final member names.
2. Drain known timestamped input, flush both converters and close both encoders/writers.
3. Reopen/inspect actual format, counts, duration and decodability.
4. Calculate SHA-256 and metadata.
5. Atomically rename both valid artifacts, write manifest, then make the package discoverable.

Any failure removes temporary output, prevents queue eligibility and records a safe reason code. No partial artifact becomes uploadable.

## Backward Compatibility

v3/v4 dual packages remain historical compatibility records. They retain their original roles and server source kind during normal retention. New client writes and new server registrations may not emit v3/v4 roles or silently convert historical data to v5.
