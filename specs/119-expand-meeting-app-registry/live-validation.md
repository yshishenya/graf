# 119 Live Validation Matrix

**Date**: 2026-07-21

This is post-enable QA for the common applications list. Verified native
identities are already `prompt_enabled`; a complete current-build result upgrades
their evidence to `runtime_verified`. A failure requires correction or disable.
Do not paste raw unified-log lines or meeting content here.

| Target | App build | AudioHAL start | AudioHAL end | Idle/prejoin safe | Non-meeting audio safe | Prompt visible | Recording indicator + Stop | Result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `zoom` | released evidence | pass | pass | pass | pass | pass | pass | `runtime_verified` |
| `yandex_telemost` | released evidence | pass | pass | pass | pass | pass | pass | `runtime_verified` |
| `telegram_macos` | pending current build | pending | pending | pending | pending | pending | pending | enabled; post-enable QA pending |
| `telegram_desktop` | pending current build | pending | pending | pending | pending | pending | pending | enabled; post-enable QA pending |
| `telegram_a` | pending current build | pending | pending | pending | pending | pending | pending | enabled; post-enable QA pending |
| `ayugram_desktop` | pending current build | pending | pending | pending | pending | pending | pending | enabled; post-enable QA pending |
| `kotatogram_desktop` | pending current build | pending | pending | pending | pending | pending | pending | enabled; post-enable QA pending |
| `dion` | 5.33.0 | pending | pending | pending | pending | pending | pending | enabled; post-enable QA pending |
| `iva_connect` | current App Store build | pending | pending | pending | pending | pending | pending | enabled; post-enable QA pending |
| `videomost` | 9.1.1 | pending | pending | pending | pending | pending | pending | enabled; post-enable QA pending |

All other expansion targets begin with the same pending result and are added to
this table when their current macOS build is available for a real call. Evidence
upgrades are per target/build; a result for Telegram Desktop also covers TDX,
Forkgram, or 64Gram only when the tested package has the same bundle identity
and equivalent call behavior.
