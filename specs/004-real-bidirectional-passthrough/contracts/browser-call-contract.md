# Contract: Browser Call Evidence

## Required Targets

- Chrome browser meetings.
- Opera browser meetings.
- Yandex Browser meetings.
- Yandex Telemost in browser.

## Required Fields

- Target name.
- Target version, when available.
- Selected meeting microphone.
- Selected meeting speaker.
- 2brain Rec route status before joining.
- Local speech usability.
- Remote audio usability.
- Leakage status.
- Latency status.
- Pass, blocked, or not accepted status.
- Concrete failure reason when not passed.

## Pass Criteria

- Meeting target uses `2brain Rec Microphone`.
- Meeting target uses `2brain Rec Speaker`.
- Local speech is heard by the remote/control side.
- Remote speech is heard locally through selected physical output.
- Remote speech is not looped into `2brain Rec Microphone` beyond threshold.
- No recording or transcript generation starts during validation.

## Blocked/Not Accepted Criteria

A target may be recorded as blocked/not accepted when local environment,
browser behavior, unavailable account/device access, or unsupported route state
prevents safe validation. The evidence must explain the concrete reason and must
not imply support.

## Privacy Boundary

Evidence is metadata-only. It must not contain raw audio, transcript text,
meeting content, credentials, tokens, or signed URLs.
