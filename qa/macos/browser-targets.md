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

## US1 Acceptance Coverage

| Target | US1 Install/Visibility | US1 Route Verification | Notes |
|---|---|---|---|
| Chrome browser meetings | Required before browser QA | Required before browser QA | Browser meeting capture starts in US2 |
| Opera browser meetings | Required before browser QA | Required before browser QA | Browser meeting capture starts in US2 |
| Yandex Browser meetings | Required before browser QA | Required before browser QA | Browser meeting capture starts in US2 |
| Yandex Telemost in browser | Required before browser QA | Required before browser QA | Validate support status before RC |

US1 does not require joining a real meeting. It requires the virtual devices to
be selectable in the browser target settings and route readiness to stay blocked
until both synthetic paths pass.
