# US2 Playback and Progress Receipt

**Scope**: deterministic local tests only. No audio payload, transcript text,
credential, provider request or installed app was used.

## 2026-07-17

- The current focused macOS command passed: `213` tests, `0` failures.
  It includes v5 package completeness, valid review-M4A handling, timeline
  metadata, monotonic intermediate byte progress, resume/retry behavior,
  accessible active capture and one-action Stop.
- The focused server and release-integration group passed: `117` tests, `11`
  expected skips, `0` failures, with one pre-existing Starlette TestClient
  deprecation warning. It covers reuse of the accepted playback candidate,
  independent playback/transcript state and deletion of both v5 audio
  artifacts.
- `ContractValidation`, the v5 metadata validator self-tests, shell syntax,
  Ruff, Compose rendering and `git diff --check` passed.

The receipt proves model and synthetic workflow behavior. A real route/volume
check and a user-visible installed-app upload-progress observation remain open
until the separately approved hardware procedure runs.
