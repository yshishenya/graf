# Hardware validation

Date: 2026-08-21

Status: **PASS — product-owner hardware acceptance**.

## Accepted matrix

After public release `v2026.08.21.3`, the product owner reported successful
recordings on two devices in two different rooms and explicitly confirmed that
all remaining T035 scenarios were satisfactory. T035 is accepted on that
manual listening and operational evidence.

| Scenario | Result | Evidence boundary |
| --- | --- | --- |
| Two devices in two rooms | PASS | Product-owner report after the public update |
| Built-in speakers at 25%, 50% and 75% | PASS | Product-owner manual acceptance |
| Headphones | PASS | Product-owner manual acceptance |
| Far-end-only and near-end-only speech | PASS | No objectionable echo or speech damage reported |
| Double-talk | PASS | Local speech remained acceptable in the tested calls |
| Clipping | PASS | No clipping regression reported |
| Wired/Bluetooth route changes | PASS | Route-change scenarios accepted |
| 60-minute run | PASS | Long-run scenario accepted without reported drift or instability |

One post-release recording on the locally installed `2026.08.21.3` app was
also observed through metadata-only logs to start, save and stop normally.
Microphone and system-audio functional permission probes remained granted after
the Sparkle update. No raw audio or private meeting data was inspected or
retained for this closeout.

## Evidence boundary

This is a product-owner manual hardware acceptance, not a new laboratory
benchmark. No per-device raw reference was retained, so this receipt does not
claim an independently reproduced hardware 20 dB measurement. The numeric
SC-001 reduction, convergence, double-talk and clock-drift checks remain backed
by the deterministic synthetic matrix; T035 adds the required real-room
listening and operational acceptance.

The accepted result applies to the tested devices, rooms and routes. It is not
a promise that every future acoustic environment is echo-free. A material
regression still stops rollout expansion and requires a higher-CalVer forward
fix; the live feed must never point to an unsigned or lower version.

No raw audio, transcript, private meeting data, credential, device identity or
private path is committed in this evidence.
