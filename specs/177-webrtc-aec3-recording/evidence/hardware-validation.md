# Hardware validation

Date: 2026-08-21

Status: **NOT EXECUTED — BLOCKED**.

## Controlled pilot decision

On 2026-08-21 the product owner explicitly authorized a limited public pilot
with the owner and known testers before this matrix is complete. This changes
the rollout boundary, not the evidence result: T035 remains open, the release
must describe the missing hardware acceptance, and no claim may be made that
real-room echo removal is generally accepted.

Pilot feedback must cover audible far-end echo, near-end speech damage,
double-talk, clipping, speaker/headphone behavior, route changes and long-run
stability. A material regression stops further pilot rollout and requires a
forward CalVer rollback; the live feed must never point to a lower version.

The required controlled matrix needs two Apple Silicon Macs, two rooms,
built-in speakers at 25/50/75%, headphones, independent far-end/near-end and
double-talk signals, wired/Bluetooth route changes, a clipping row and one
60-minute run. Those controlled conditions were not available in this local
implementation session.

Therefore this evidence does not claim:

- no audible echo on real speakers;
- real-room double-talk acceptance;
- 60-minute hardware clock alignment;
- release readiness.

Synthetic AEC3, full Swift, universal packaging and metadata-only integrity
checks passed separately. They do not replace this manual gate. No raw audio,
private meeting content, transcript or device identity is committed.

The 2026-08-21 technical audit added default-output-device observation,
bounded clock recovery, format-change rejection and stronger synthetic tests.
It did not execute or close the controlled hardware matrix.
