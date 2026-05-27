# macOS Browser Target Matrix

## Purpose

Track official MVP browser meeting targets and route/capture validation status.

## Official MVP Targets

| Target | Status | Required Coverage |
|---|---|---|
| Chrome browser meetings | Planned | Synthetic route plus real browser meeting validation |
| Opera browser meetings | Planned | Synthetic route plus real browser meeting validation |
| Yandex Browser meetings | Planned | Synthetic route plus real browser meeting validation |
| Yandex Telemost in browser | Planned after QA | Synthetic route plus real browser meeting validation |

## Best-Effort Rule

Any app or meeting target outside the official matrix is best-effort unless a later Spec Kit feature adds it to supported scope.

## Required Route Assertions

- `2brain Rec Microphone` is selected as the meeting microphone.
- `2brain Rec Speaker` is selected as the meeting speaker.
- Remote audio is absent from the virtual microphone path.
- Local mic and remote speaker tracks are captured separately.
- `ready` is never shown until both mic and speaker routes pass validation.
