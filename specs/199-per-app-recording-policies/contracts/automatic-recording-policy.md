# Contract: Target-scoped automatic recording policy

## Policy resolution

For a verified native prompt-capable target:

1. `never` returns a terminal suppression outcome.
2. `always` returns automatic-start eligibility only when the current workspace
   policy, acknowledgement, permissions, readiness, visible indicator and Stop
   gates pass.
3. `ask` returns a prompt outcome.

The final start decision rechecks the current registry, detector activity and all
capture prerequisites immediately before capture.

## Prompt outcomes

| Event | Current action | Persisted rule |
|---|---|---|
| Start, checkbox off | Start current recording | unchanged |
| Start, checkbox on | Start current recording | `always` |
| Skip, checkbox off | Suppress current meeting | unchanged |
| Skip, checkbox on | Suppress current meeting | `never` |
| Timeout, checkbox either | Start current recording if gates pass | unchanged |

Timeout is not a consent or policy-acknowledgement event. A failed save of an
explicit rule must leave the previous rule unchanged and report a bounded,
user-readable save error in settings or prompt flow.

## Settings contract

- Per-target radio cards expose exactly `Всегда`, `Спрашивать`, `Никогда`.
- A bulk radio-card control applies one selected value to all eligible targets.
- Mixed target values display `Разные` and do not mutate until a concrete value is
  selected.
- Technical switches retain their short labels; detailed copy is exposed through
  an information hint reachable by pointer, keyboard and VoiceOver.
