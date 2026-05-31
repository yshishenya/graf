# Contract: Browser Validation Evidence

## Purpose

Define the browser evidence required before release readiness.

## Required Targets

- Chrome
- Opera
- Yandex Browser
- Yandex Telemost-in-browser

## Per-Target Evidence

Each target records:

- target name and version if available;
- selected meeting microphone;
- selected meeting speaker;
- local speech usability;
- remote audio usability;
- readiness state before joining;
- route state after joining;
- pass, blocked, or not accepted status;
- failure reason when not passed.

## Pass Rules

- A target can pass only after the app is `ready` from live route evidence.
- A target can be blocked/not accepted only with a concrete reason.
- Release readiness requires every required target to have pass or blocked/not
  accepted evidence.
