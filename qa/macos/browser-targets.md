# macOS Browser Target Matrix

## Purpose

Track official MVP browser meeting targets and route/capture validation status.

## Official MVP Targets

| Target | Status | Required Coverage |
|---|---|---|
| Chrome browser meetings | Manual smoke passed | Synthetic route plus real browser meeting validation; long-duration recording acceptance deferred |
| Opera browser meetings | Manual smoke passed | Synthetic route plus real browser meeting validation; long-duration recording acceptance deferred |
| Yandex Browser meetings | Skipped/not accepted in current cycle | Must be run before it is marketed as supported |
| Yandex Telemost in browser | Manual smoke passed | Synthetic route plus real browser meeting validation; long-duration recording acceptance deferred |
| Zoom | Manual smoke passed, best-effort target | Not in the original browser-only MVP matrix; keep as additional app evidence until a spec adds official support |

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

## 005 Short Smoke vs Future Long-Duration Acceptance

| Target | 005 Short Smoke Evidence | Future Recording-Assisted Acceptance |
|---|---|---|
| Chrome browser meetings | Passed current metadata-only manual smoke | Deferred until local recording exists |
| Opera browser meetings | Passed current metadata-only manual smoke | Deferred until local recording exists |
| Yandex Browser meetings | May be marked `not_accepted` if skipped | Deferred until local recording exists |
| Yandex Telemost in browser | Passed current metadata-only manual smoke | Deferred until local recording exists |

005 evidence must never treat short smoke confirmation as long-duration replay
acceptance. Unsupported, skipped, or unavailable targets must be recorded as
`blocked` or `not_accepted`, not `passed`.
