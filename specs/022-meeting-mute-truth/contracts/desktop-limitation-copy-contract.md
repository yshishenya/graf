# Contract: Desktop Limitation Copy

## Required Copy

When meeting-app mute truth is unavailable, stale, contradictory, unsupported,
or deferred, the desktop app must show:

```text
2brain cannot verify mute inside this meeting app. Use Pause or Stop in 2brain to keep local speech out of the recording.
```

## Placement

The copy must be visible in the native capture surface before or during manual
recording for unproven targets. It may appear as a compact warning/banner near
capture controls, but it must not obscure:

- active recording indicator;
- Pause/Resume;
- Stop;
- local recording status;
- upload/review status from earlier slices.

## Accessibility

- The warning must have an accessibility label matching the visible copy.
- Text must wrap without truncating the core action: "Use Pause or Stop".
- It must remain readable in dark and light themes.

## Copy Boundaries

The app may say:

- product-owned Pause/Stop protects local recording speech;
- meeting-app mute cannot be verified for the current target;
- the artifact is `meeting_mute_unproven`, unsupported, deferred, or degraded.

The app must not say:

- third-party meeting-app mute is respected for MVP targets;
- muted speech was universally deleted outside 2brain Rec control;
- server, MediaScribe, Langfuse, retention, deletion, or sharing behavior
  changed because of this local feature.
