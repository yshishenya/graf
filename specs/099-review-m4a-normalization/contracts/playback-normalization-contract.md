# Playback Normalization Contract

**Feature**: `099-review-m4a-normalization`

## Purpose

Define the accepted-source boundary, supported media matrix, canonical playback
profile, deterministic source selection/mix, full validation gate, and automatic
normalization behavior. This contract creates no upload endpoint, user track
selector, retry action, or MediaScribe dependency.

## Guarantee

Every retained accepted source that is valid, supported, contains usable audio,
and is within the documented limits automatically reaches one validated
canonical playback artifact. User and workspace-administrator intervention is
never part of the success path.

Impossible inputs finish with a safe terminal reason. Temporary system failures
stay in automatic recovery and never expose a retry/reprocess control.

## Accepted-source boundary

Normalization input must be registered to one accepted `MediaRevision`:

- manual upload: exactly one authoritative `media` artifact;
- first-party recording: exactly one `microphone` and one `system` artifact;
- optional first-party `playback` artifact: candidate derivative only.

The normalizer must reject:

- raw HTTP upload bodies;
- upload parts or an unfinalized session;
- arbitrary object keys or URLs;
- desktop/local filesystem paths;
- a source from another meeting, revision, user, or workspace;
- a changed/purged source fingerprint;
- a MediaScribe request/result object.

The accepted source artifact remains separate from canonical playback. A manual
M4A cannot be relabeled in place as `playback`.

## Canonical profile

Profile ID: `review_m4a_aac_lc_48k_mono_64k_v1`.

| Property | Required value |
|---|---|
| Container | ISO BMFF M4A, normal non-fragmented file |
| Egress MIME | `audio/mp4` |
| Streams | exactly 1 audio; 0 video/subtitle/data/attachment |
| Codec | AAC-LC, MPEG-4 Audio Object Type 2 |
| Sample rate | 48,000 Hz |
| Channels | 1, mono |
| Disposition | audio stream is default |
| Target audio bitrate | 64,000 bit/s |
| Reuse bitrate window | 56,000–72,000 bit/s |
| Start time | 0–100 ms |
| Duration | greater than 0 and at most 14,400 seconds |
| Object size | at most 134,217,728 bytes |
| MP4 layout | bounded boxes, `moov` before first `mdat`, no `moof` |
| Metadata | no source/user tags, chapters, filenames, or private text |
| Integrity | stored length/SHA-256 match; strict full decode passes |

Playback egress always uses the safe filename `meeting-review.m4a`; object keys
are not derived from source filenames and are never returned.

## Supported source matrix

Both the detected container/demuxer and selected audio codec must be allowed.

| Container family | Allowed audio codec families |
|---|---|
| WAV/RF64/W64 | PCM integer/float, A-law, mu-law |
| MP3 | MPEG Audio Layer III |
| raw AAC/ADTS | AAC-LC/HE-AAC |
| FLAC | FLAC |
| Ogg | Vorbis, Opus, FLAC |
| M4A/MP4/MOV/M4V | AAC-LC/HE-AAC, ALAC, MP3, PCM |
| WebM | Opus, Vorbis |
| Matroska/MKV | Opus, Vorbis, AAC, MP3, FLAC, PCM |

Unsupported:

- DRM/encrypted content;
- playlist/manifest inputs and remote references;
- container or codec outside the matrix;
- executable attachments or a source requiring a non-file protocol.

Extension and MIME do not authorize a format. The browser file picker advertises
the exact extension/MIME matrix, but server byte-level probe is authoritative.

## Limits

- actual duration: at most 14,400 seconds;
- manual file: existing 1 GiB limit;
- first-party track: existing 2.5 GiB limit;
- first-party package: existing 5 GiB limit;
- total streams: at most 16;
- audio streams: at most 8;
- final playback: at most 128 MiB;
- work-volume configured budget: 6 GiB;
- concurrent activity per media worker: 1.

No smaller hidden normalization source limit may make an already accepted valid
source unsupported.

## Probe contract

Probe runs from a UUID-only private disk path with:

- no shell;
- `-v error`;
- `-protocol_whitelist file`;
- explicit demuxer allowlist;
- fixed `-probesize 16777216` and `-analyzeduration 30000000`;
- `-show_error`, `-show_format`, `-show_streams`, `-show_chapters`;
- a fixed `-show_entries` allowlist;
- compact JSON with invalid string data rejected;
- 60-second timeout;
- stdout cap 256 KiB and stderr cap 1 MiB.

Raw probe JSON and tags are not persisted. The parser produces only safe typed
facts required by the job/attempt model.

## Single-container audio selection

1. Enumerate audio streams with supported codec, usable configuration, positive
   duration or bounded-decode potential, and non-attachment semantics.
2. If exactly one is usable, select it.
3. If several are usable, select only when exactly one has container
   `disposition.default=1`.
4. If no unique selection exists, set terminal
   `ambiguous_audio_tracks`.
5. Invoke FFmpeg with the selected global index: `-map 0:<index>`.
6. Never select the first stream, highest channel count, or fallback stream after
   the selected stream fails decode.
7. Never mix multiple streams from a manual media container.

## First-party dual-source mix

The explicit `microphone` and `system` roles are one product-defined logical
review source, not ambiguous streams. When the optional playback candidate is
unusable, derive one mono program track:

```text
sample = clamp((microphone + system) * 0.5, -1, 1)
duration = longest accepted source timeline
missing tail = silence
timestamps = start at zero and remain aligned
```

The implementation uses explicit labeled filter outputs and maps exactly one
result. It must not:

- choose one role and discard the other;
- infer a role from filename/order;
- alter either accepted WAV;
- send the playback derivative to the normal dual-track MediaScribe contract;
- claim that 16 kHz accepted source becomes higher fidelity after the required
  48 kHz playback resample.

## Reuse/remux/transcode decisions

### Candidate or manual M4A fully canonical

- Verify byte length and SHA-256.
- Probe and BMFF-validate.
- Strictly decode the entire audio stream.
- Verify every canonical property.
- First-party candidate may be promoted.
- Manual source bytes are copied to a distinct immutable playback attempt object.

No audio re-encode occurs.

### Audio canonical, container layout noncanonical

Perform lossless explicit-stream remux with metadata/chapters removed and
`+faststart`; then run the complete canonical gate. This is a new playback
object and not byte-for-byte reuse.

### Other supported source

Transcode the selected single stream, or the explicit dual-source mix, to:

```text
AAC-LC / 48 kHz / mono / 64 kbit/s / default stream / M4A +faststart
```

Use:

- `-hide_banner -loglevel error -nostdin -xerror -y`;
- `-protocol_whitelist file` and explicit demuxer allowlist;
- explicit `-map` or labeled mix output;
- `-vn -sn -dn`;
- `-map_metadata -1 -map_chapters -1`;
- one filter/codec thread;
- `aresample=48000` with first PTS normalized to zero;
- `-ac 1 -ar 48000 -c:a aac -profile:a aac_low -b:a 64k`;
- default audio disposition;
- `-fs 134217728` as defense in depth;
- `-movflags +faststart -f ipod`.

Duration defense must not silently publish a truncated source. A source with
unknown/unreliable duration is fully decoded within the hard limit before
publication eligibility. Any output touching the duration guard is discarded
unless complete source EOF within 14,400 seconds was proved.

## Complete output gate

Every copied, remuxed, or transcoded output must pass all of these after the
process exits:

1. regular file, positive size, at most 128 MiB;
2. complete SHA-256 and stat;
3. strict bounded probe;
4. stdlib top-level BMFF parser proves valid bounds/order and no fragmentation;
5. exactly the canonical stream/profile values;
6. strict full decode to null with no recoverable error accepted;
7. output duration is positive, within limit, and within the encoded/copy
   tolerance of the selected complete source timeline;
8. no metadata/chapters/extra streams;
9. attempt row facts match the file;
10. source fingerprint and meeting lifecycle rechecked under publication lock.

Failure of a GRAF-generated output is a retryable system incident, not a
terminal accusation that the valid source is unsupported.

Duration tolerance is fixed and derivation-specific:

- byte copy or lossless remux: absolute difference at most 50 ms;
- single-source transcode or dual-source mix: absolute difference at most
  250 ms, covering AAC frame/resample delay without hiding truncation.

The 56-72 kbit/s window is required when reusing existing audio. Generated AAC
is authorized by the exact 64 kbit/s encoder command receipt plus the complete
output gate; its measured average bitrate is recorded but is not falsely
required to be CBR for silence or sparse content.

## Publication

- Register the immutable attempt object key before upload.
- Candidate/attempt objects are never returned by playback routes.
- Upload the complete validated object to the attempt key.
- Lock meeting, job, and revision.
- Recheck accepted source fingerprint and deletion state.
- If another valid canonical artifact already won, clean this attempt and reuse
  the winner.
- Otherwise supersede other playback candidates/legacy rows, create or promote
  one validated `TrackArtifact`, point the job at it, mark attempt published,
  and commit.
- The unique canonical index is the final conflict guard.

## Failure classification

Permanent source states:

- `empty_source`;
- `unsupported_container` / `unsupported_codec` / `encrypted_media`;
- `corrupt_source` / `no_audio` / `ambiguous_audio_tracks`;
- size/duration/stream limit exceeded;
- source missing, purged, or mismatched.

Automatic recovery states:

- storage/database/Temporal/temp capacity unavailable;
- worker interruption/cancellation or timeout;
- FFmpeg/ffprobe dependency temporarily unavailable;
- publication interruption;
- generated output fails the canonical gate.

User-facing error details never include raw dependency output, source filename,
path, object key, codec dump, tag, or media content.
