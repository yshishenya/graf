# Contract: AEC Processing

## Readiness

Before a recording becomes active, GRAF must create and configure one processor
with the pinned dependency identity. Only desktop AEC3 is enabled. Failure to
create, configure or initialize it blocks normal recording start.

## Input

The timeline supplies finite, deinterleaved mono float samples at 48 kHz. Each
call receives exactly 480 system samples and the 480 microphone samples for the
same canonical PTS interval and route generation.

Callback size and callback delivery time are not processor inputs. The existing
timeline owns downmix, resampling, PTS mapping, reordering and bounded buffering.

## Processing order

For each 10 ms pair:

```text
system[480]     -> ProcessReverseStream
stream delay 0 -> set_stream_delay_ms
microphone[480] -> ProcessStream
cleaned mic + unchanged system -> 0.5 canonical mix
```

Every return code is checked. A partial final pair is padded on both sides,
processed once, and trimmed to the original common sample count. Output frame
indices and total sample count remain exact.

## Disabled processing

The bridge explicitly disables:

- mobile echo-control mode;
- AEC enforced high-pass and general high-pass filtering;
- noise suppression/ANC;
- gain controller 1 and 2;
- transient suppression;
- VAD, amplitude gates and speech inference;
- AecDump.

## Error boundary

The C ABI catches C++ exceptions and returns bounded status values. Any failed
reverse or capture call permanently closes the active processor for that
recording. Swift records a safe reason, stops emitting frames, and retains at
most the prefix already returned successfully. It never returns or mixes the
raw microphone frame that failed processing.

## Discontinuity

An absent render interval is different from a valid silent interval. Missing
reference, backward PTS, gap, overflow, route/format/timebase change or producer
runtime failure ends the trusted segment. The first release does not
transparently reset across those boundaries; it exposes degradation and
preserves one-action Stop.

Privacy Pause is not a discontinuity: the existing wrapper preserves PTS and
supplies deliberate zero microphone samples while the matching render reference
continues through AEC3. Resume restores captured microphone samples through the
same mandatory processor. Neither transition may bypass AEC or create raw-mic
output.

## Threading and lifetime

Create, process, read statistics and destroy the processor on the existing
serialized recording path. One recording owns one processor. No WebRTC object
or C++ standard-library type crosses the C ABI.
