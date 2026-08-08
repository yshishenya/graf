# Timeline and Artifact Contract

## Capture → Canonical PCM

```text
ScreenCaptureKit system batches ┐
                              ├─ timestamp normalizer ─ common 48 kHz index ─ mix ─┬─ WAV 16 kHz
app-owned microphone batches ┘                                                    └─ M4A 48 kHz
```

The two inputs are app-owned capture batches. They are not persisted as final files. Every consumer after the mix consumes the same canonical PCM frames.

## Required Source Batch Fields

| Field | Requirement |
| --- | --- |
| source | `microphone` or `system`; no anonymous source |
| presentation time | valid source PTS mapped to one comparable recording basis |
| duration / frame count | finite, positive and consistent with actual source sample rate |
| sample rate / channels | actual runtime values, not a hard-coded assumption |
| discontinuity | explicit `none`, gap, overlap, route change or drop signal |
| route generation | incremented when capture route changes; never silently joined across a mismatch |

## Timing Decisions

| Condition | Writer action | Package result |
| --- | --- | --- |
| source arrives later than epoch | insert timeline silence for that source | valid only if within controlled timing limits |
| known gap | insert exact silence in that source interval | safe timing metadata records gap |
| overlap | trim duplicate source-time frames deterministically | safe overlap metadata records trim |
| converter flush | write all final valid frames before close | no short tail/truncation |
| source queue overflow | do not discard older samples silently | integrity failure / no ready package |
| uncomparable PTS or route change | attempt only bounded re-establishment | typed degraded/failed truth, no count fallback |

## Artifact Fan-out Invariants

- The PCM fan-out call sequence is single-writer and ordered by canonical frame index.
- WAV output receives the same canonical frames after stateful 48 → 16 kHz conversion; M4A receives them at 48 kHz.
- The common-frame mix is exactly `0.5 × microphone + 0.5 × system` under `canonical-mix.v1`; no adaptive gain or ducking is permitted.
- A writer failure is propagated to finalization; `try?`, nil buffer/channel, skipped flush or missing close cannot be reported as a ready artifact.
- Review audio's AAC encoder padding is a container property, not a timeline drift allowance.
- Playback route selection/volume are never modified by the writer or mix.

## Negative Cases

Automated fixtures cover different start offsets, source rates, gap, double-talk, overflow, early Stop, stop-tail flush, corrupted WAV/M4A, wrong format/role/checksum, duration mismatch and historical v3/v4 reading. Hardware acceptance covers real output route and volume behavior. No test fixture stores speech text or user audio.
