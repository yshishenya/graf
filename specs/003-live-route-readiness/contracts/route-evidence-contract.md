# Contract: Route Evidence

## Purpose

Define the evidence needed to accept or reject a live audio route.

## Microphone Path

Required evidence:

- selected physical microphone is not a 2brain Rec virtual device;
- selected physical microphone is available to the current user;
- valid frames arrive during the user-triggered check;
- ordinary silence is distinguishable from missing frames;
- output to `2brain Rec Microphone` is associated with the selected physical
  microphone route.

Pass condition:

- valid path evidence exists and no self-routing or capturability failure is
  present.

## Speaker Path

Required evidence:

- selected physical output is not a 2brain Rec virtual device;
- short audible stimulus is user-triggered;
- stimulus route reaches the selected physical output path;
- missing/muted/unavailable output produces a failure reason.

Pass condition:

- speaker route evidence exists and no self-routing or output failure is present.

## Latency And Leakage

- Built-in/wired `addedLatencyMs` must be `<= 30`.
- Built-in/wired `relativeLeakageDb` must be `<= -45 dB` and not intelligible.
- Bluetooth/AirPods-class routes are recorded separately as managed pilot routes.
