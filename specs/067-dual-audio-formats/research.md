# Research: Dual Audio Formats

**Feature**: `067-dual-audio-formats`

**Date**: 2026-06-27

## Decision Summary

- Keep transcription exactly as the current product contract: `mic.wav` plus
  `incoming.wav`, mono PCM WAV, aligned from `t=0`, submitted through the
  server-owned MediaScribe path.
- Add one playback/distribution asset for review and approved sharing:
  `meeting-review.m4a`, MP4/M4A container, AAC-LC codec
  (`audio/mp4`, `mp4a.40.2`).
- MVP encoding target: 48 kHz mono AAC-LC at 64 kbps from the capture-rate
  writer queue, finalized as a local playback derivative at Stop. Use 96 kbps
  only when reviewer validation catches artifacts; use 96-128 kbps stereo only
  when the source is genuinely stereo or music/content-heavy.
- Do not upsample or duplicate mono merely to claim quality. If only the current
  16 kHz transcription WAV pair is available, encode the review asset as a
  size/seek/distribution improvement, not as a source-fidelity improvement.
- Defer Opus/WebM as an optional web-only alternate. It is excellent for speech
  efficiency, but M4A/AAC-LC is the safer default for broad playback,
  downloads, and sharing.
- Do not store a second permanent MP3 copy for "just in case". If broad external
  compatibility becomes more important than app-owned playback, add an on-demand
  MP3 export path or switch the single distribution derivative after validation.

## Current Code Findings

- The local recording package currently creates `manifest.json`, `mic.wav`, and
  `incoming.wav`.
- `LocalRecordingWriter` records the transcription files as
  `wav-pcm-s16le`, `16_000` Hz, mono. Its source stream metadata and
  downsampler show capture input at 48 kHz and writer output at 16 kHz.
- `DesktopUploadClient` describes both audio tracks to ingest as
  `wav-pcm-s16le`, `16_000` Hz, mono.
- The server processing path stores microphone and system artifacts separately,
  then submits those two artifacts to MediaScribe as `mic_file` and
  `incoming_file`.
- The current cabinet review route fetches both WAV artifacts, mixes them on
  demand, returns `audio/wav`, and names the response `meeting-review.wav`.

Implication: the transcription path is already intentionally narrow and should
not be disturbed. The first playback/distribution slice should add a cached
compressed derivative without changing capture. Better listening source quality
requires a later capture-rate artifact decision.

## External Source Review

- MDN's web media codec guidance lists AAC with MP4, ADTS, and 3GP container
  support and notes that browser/runtime support can vary. This supports choosing
  MP4/M4A for the AAC asset while validating the actual embedded review surfaces.
  Source: https://developer.mozilla.org/en-US/docs/Web/Media/Guides/Formats/Audio_codecs
- Apple Podcasts' audio requirements recommend AAC for bandwidth-efficient
  distribution and list 64-128 kbps for 44.1/48 kHz mono content. This supports
  a 64 kbps mono default for meeting review, with a higher tier only when source
  content needs it. Source: https://podcasters.apple.com/support/893-audio-requirements
- Opus is standardized by IETF RFC 6716 and supports speech and music across a
  broad bitrate range. The official Opus project highlights 6-510 kb/s,
  8-48 kHz, mono/stereo, and low-latency speech/music operation. This supports
  keeping Opus as a strong future web-optimized alternate rather than the broad
  distribution default. Sources:
  https://datatracker.ietf.org/doc/html/rfc6716 and https://opus-codec.org/
- The WebM project defines WebM as a web media container with Opus/Vorbis audio.
  That makes it a good browser-oriented candidate, but not as good as M4A for
  general downloaded audio identity. Source: https://www.webmproject.org/about/

## Field Practice Review

Community and implementation examples mostly reinforce the split:

- Reddit podcast/audio threads commonly treat WAV as the editing/master source
  and MP3 as the broad publishing format. They also repeatedly warn to match the
  format to the real playback devices. For 2brain Rec, that means preserving WAV
  transcription truth and validating the actual web/macOS review surfaces before
  claiming a universal distribution format. Sources:
  https://www.reddit.com/r/podcasting/comments/1hm3bhd/wav_or_mp3_file/ and
  https://www.reddit.com/r/audioengineering/comments/6tu17x/whats_a_good_lossy_formatcompression_today_right/
- Reddit audio discussions also keep Opus in the "space-efficient at low
  bitrate" bucket, not the "every recipient can play it" bucket. That supports
  deferring Opus/WebM until there is a measured storage or bandwidth problem.
  Source:
  https://www.reddit.com/r/audioengineering/comments/1louzvq/is_opus_really_the_better_choice_for_phone/
- Medium transcription/pipeline writeups commonly use FFmpeg as an explicit
  conversion stage and normalize mixed real-world inputs before transcription.
  The useful practice is an explicit derivative pipeline with a declared encoder
  boundary, not changing the transcription source. Sources:
  https://medium.com/data-science-collective/implementing-whisper-openai-in-browser-for-offline-audio-transcription-adab61be7af7 and
  https://medium.com/%40mecreate/i-stopped-uploading-my-audio-to-the-cloud-for-transcription-services-like-elevenlabs-and-whispflow-a103895db2eb
- GitHub projects around Whisper and meeting notes usually accept many user
  formats, then rely on FFmpeg or equivalent normalization internally. One
  meeting-notes app advertises automatic compression for large or long audio,
  and Whisper's own README requires FFmpeg for decoding. Sources:
  https://github.com/openai/whisper and
  https://github.com/DevSlem/ai-meeting-notes
- GitHub discussion around `whisper.cpp` shows the same pragmatic conversion
  shape: convert arbitrary audio to temporary mono 16 kHz WAV for inference.
  This supports keeping the transcription format boring and separate from
  playback/export. Source:
  https://github.com/ggml-org/whisper.cpp/discussions/1399
- Older browser-side Opus recorder libraries are a warning, not a shortcut:
  one mature library is now unmaintained and points users toward modern browser
  APIs. That argues against adding a browser/WASM encoding path for this slice.
  Source: https://github.com/chris-rudmin/opus-recorder

## Recommended Product Shape

### Transcription

No format change.

- Keep `mic.wav`.
- Keep `incoming.wav`.
- Keep separate MediaScribe fields and timeline alignment.
- Do not send `meeting-review.m4a` to MediaScribe as the normal dual-track
  source.

### Playback And Distribution

MVP asset:

- Filename: `meeting-review.m4a`
- Container: MP4/M4A
- MIME type: `audio/mp4`
- Codec: AAC-LC (`mp4a.40.2`)
- Default bitrate: 64 kbps mono for speech-heavy meeting review from 44.1/48 kHz
  capture-rate source
- Higher tier: 96 kbps mono when reviewer validation catches artifacts or the
  meeting has music/screen-share media that benefits from more bits
- Stereo tier: 96-128 kbps only for genuinely stereo source; do not stereo-copy
  mono
- Sample rate: preserve the best validated capture-rate source, normally
  48 kHz; do not upsample 16 kHz WAV just to label the file high quality
- Seekability: optimize the MP4/M4A file for progressive playback and byte range
  seeking
- Generation: write from the macOS writer queue after capture callbacks have
  buffered samples, finalize at Stop, and keep WAV transcription files unchanged

### Mixing

For review/distribution, use one mixed program track unless a later feature
adds multi-track export.

- Mix microphone and incoming/system with headroom so simultaneous speakers do
  not clip.
- Keep silence and duration alignment, so transcript timestamp seeking remains
  meaningful.
- Store metadata for included source roles, duration, byte count, codec,
  bitrate target, source sample rate, generation status, and fallback reason.

## Alternatives Considered

### Continue Serving Mixed WAV

Rejected for the primary playback path. It preserves source samples but is too
large for fast playback and distribution, and the current route rebuilds the
mixed WAV on demand.

### Server-Side AAC/M4A As The First Step

Rejected for the MVP. The current server/runtime has no existing audio encoding
dependency to reuse. A native macOS derivative keeps the first slice smaller and
does not touch MediaScribe ingest.

### Opus/WebM As The Only Asset

Rejected as the default because it is better for controlled web playback than
general distribution. It remains a good optional follow-up if the product later
wants a lower-bitrate web-only ladder, for example 32-48 kbps mono Opus.

### MP3

Rejected as the stored first choice. MP3 is still the safest "send to anyone"
format, but AAC-LC gives better quality at comparable low bitrates and fits the
native macOS/iOS stack cleanly. Add MP3 as an on-demand export or switch the
single derivative only if validation shows external recipients cannot reliably
play M4A.

### FLAC/ALAC

Rejected for playback/distribution. Lossless files are useful for archival
masters, but they do not solve the size and bandwidth goal for review audio.

### Re-encode From The 16 kHz WAV Pair Only

Allowed only as a fallback. It can make playback smaller and seekable, but it
cannot honestly improve source fidelity over the current transcription WAVs.

## Validation Questions For Planning

- Should the next slice upload `meeting-review.m4a` as an optional playback
  artifact, or should server playback keep deriving audio until egress policy is
  fully modeled?
- If server-side encoding is later chosen, which container image change proves
  AAC support without widening runtime attack surface unnecessarily?
- What exact fallback state should the UI show when only a size-optimized
  playback asset exists and no fidelity uplift is possible?
- Which review/download players are in the required compatibility matrix:
  web cabinet, embedded macOS WebView, Finder/Quick Look, Safari, Chrome, and
  Firefox on the supported platforms?
- What listening validation set is enough to keep 64 kbps mono for the MVP or
  justify 96 kbps for specific content?
