# 30-Minute Development Gate Evidence

Date: 2026-06-04

Status: superseded / not accepted as driver live-route evidence.

No 30-minute driver live-route controlled meeting run is accepted for `019`.
Revalidation of issue #234 showed the attempted live virtual-device publication
strategy can still cause CoreAudio CPU runaway or probe timeouts, so this gate
must not be counted as driver acceptance.

Feature `025-system-audio-capture-pivot` supersedes this MVP recording gate with
direct system-audio plus microphone capture and has its own accepted 30-minute
and 75-minute evidence. Future driver/virtual-device routing requires a
separate advanced-routing spec and fresh safety evidence.

Required accepted coverage:

| Target | Built-in | Wired | USB |
|--------|----------|-------|-----|
| Chrome | not-tested | not-tested | not-tested |
| Opera | not-tested | not-tested | not-tested |
| Zoom | not-tested | not-tested | not-tested |
| Telemost | not-tested | not-tested | not-tested |

Acceptance requires `unexpectedReleaseCount == 0`, no normal `Run Check`, fresh client activity evidence, route lifecycle evidence, release decision evidence, and recording timeline evidence when recording is active.

## 2026-06-10 Superseded Decision

- Decision: closed as superseded by accepted feature `025-system-audio-capture-pivot`.
- Driver live-route result: not accepted.
- MVP recording result: accepted under `025` using system-audio capture evidence.
- Issue link: #234 closed as superseded / parked for future advanced-routing work.
