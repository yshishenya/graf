# 092 Native macOS Meeting App Allowlist

**Status**: Spec Kit registry seed for the first macOS detector probe.

**Date**: 2026-07-08

This is the current macOS seed allowlist artifact for the planned native macOS
meeting detector. The production target list should be delivered through the
remote/cache/packaged-seed registry design in
`specs/092-automatic-meeting-detection/registry-telemetry.md`, not as a
client-only hardcoded list. No production code allowlist exists yet.

The detector input rule is intentionally simple:

1. Parse passive macOS `AudioHAL` ownership events keyed by bundle ID.
2. Keep only bundle IDs that are in this native meeting allowlist.
3. Ignore every non-allowlisted ownership event.
4. Debounce start/end changes.
5. Feed prompt or target-scoped auto-record policy.
6. Feed metadata-only local telemetry rollups for known target health and
   unknown app discovery without allowing telemetry to start recording.

Browsers are not part of this native audio-ownership allowlist. Browser meetings
must use the browser metadata path: active tab URL/title/service family plus
calendar or join intent, with browser audio ownership only as supporting
evidence.

## Modes

| Mode | Meaning | Product behavior |
| --- | --- | --- |
| `prompt_enabled` | Local runtime start and end are verified on this Mac. | Eligible for the first product prompt/auto-rule path, subject to policy gates. |
| `diagnostic_only` | Bundle ID is known, but live audio ownership is not fully verified. | Probe may observe and log metadata-only diagnostics; product prompt stays disabled until runtime validation passes. |
| `blocked_missing_bundle` | Target exists, but reliable macOS bundle ID is not known. | Cannot be matched from macOS audio ownership; package or local install verification required first. |
| `manual_or_browser_only` | Target is not suitable for this native macOS app allowlist. | Use manual recording or browser-specific detection path. |
| `disabled` | Target is known but explicitly disabled by registry policy. | No prompt, no auto-record, and only registry-health diagnostics if needed. |

## Allowlist

| Target | Bundle ID(s) | Mode | Evidence | Comment |
| --- | --- | --- | --- | --- |
| Zoom | `us.zoom.xos` | `prompt_enabled` | `runtime_verified` | `AudioHAL` ownership start and target removal/end were captured locally on 2026-07-08. |
| Yandex Telemost | `ru.yandex.desktop.telemost` | `prompt_enabled` | `runtime_verified` | `AudioHAL` ownership start and target removal/end were captured locally on 2026-07-08/09. |
| Microsoft Teams classic | `com.microsoft.teams` | `diagnostic_only` | `confirmed` | Known classic Teams bundle ID. Needs current local package/runtime check before prompt mode. |
| Microsoft Teams new/work/school | `com.microsoft.teams2` | `diagnostic_only` | `confirmed` | Known new Teams bundle ID. Needs current local package/runtime check before prompt mode. |
| Slack calls/huddles | `com.tinyspeck.slackmacgap` | `diagnostic_only` | `confirmed` | Slack desktop identity is confirmed, but call/huddle audio ownership still needs validation. |
| Webex Meetings/App | `com.cisco.webexmeetingsapp`, `com.webex.meetingmanager` | `diagnostic_only` | `seed` | Multiple Webex app flavors exist; verify which bundle emits audio ownership in current Webex. |
| FaceTime | `com.apple.FaceTime` | `diagnostic_only` | `seed` | Built-in app. Keep diagnostic-only until product decides whether personal calls are in scope. |
| Discord | `com.hnc.Discord` | `diagnostic_only` | `seed` | Present in comparable allowlists. Lower priority for GRAF meeting-capture MVP. |
| Skype | `com.skype.skype` | `diagnostic_only` | `seed` | Product status and current runtime behavior need validation before prompt mode. |
| WhatsApp | `net.whatsapp.WhatsApp` | `diagnostic_only` | `seed` | Present in comparable allowlists. Needs current runtime validation. |
| VooV Meeting | `com.tencent.tencentmeeting` | `diagnostic_only` | `seed` | Lower Russian-market priority. Needs package/runtime validation. |
| Tuple | `app.tuple.app` | `diagnostic_only` | `seed` | Lower priority. Needs package/runtime validation. |
| Gather | `com.gather.Gather` | `diagnostic_only` | `seed` | Lower priority. Needs package/runtime validation. |
| Kontur Talk / Толк | `kontur.talk` | `diagnostic_only` | `package_verified` | Official DMG verified: `Толк.app`, version `3.6.0`, team `VEWAJ43QEN`. Needs live audio ownership. |
| MTS Link / МТС Линк | `ru.weteams.desktop` | `diagnostic_only` | `package_verified` | Official DMG verified: `МТС Линк.app`, version `0.87.0`, team `ZZ645F8B29`. Needs live audio ownership. |
| TrueConf | `org.trueconf.client` | `diagnostic_only` | `package_verified` | Official DMG and local app verified. Idle launch did not emit audio ownership; needs live call/mic-test ownership validation. |
| VK Calls | `com.vk.calls.native.1` | `diagnostic_only` | `package_verified` | Official DMG verified: `VK Calls.app`, version `1.44.39190`, team `FD3X58MN39`. Needs live audio ownership. |
| VK Teams / VK WorkSpace | `ru.mail.messenger-biz-avocado-desktop` | `diagnostic_only` | `installed_verified` | Local app verified: `VK Teams.app`, version `25.4.3`, team `4D6LA585PP`. Idle launch was quiet; live call blocked by missing account. |
| VINTEO | `com.vinteo.desktop` | `diagnostic_only` | `package_verified` | Official ARM64 DMG verified: `VinteoDesktop.app`, version `4.27.0`, team `U47995Q86Q`. Needs live audio ownership. |
| eXpress | `ru.unlimitedtech.express.desktop` | `diagnostic_only` | `package_verified` | Official ARM64 DMG verified: `eXpress.app`, version `3.68.38`, team `NUMFWSGG8Z`. Needs live audio ownership and product-scope decision. |
| Pachca / Пачка | `com.todesktop.240607opwvcw853` | `diagnostic_only` | `package_verified` | Official ARM64 DMG verified. ToDesktop bundle ID is non-obvious; needs live audio ownership and product-scope decision. |
| SaluteJazz / Jazz | `salutejazz.jazz-app` | `diagnostic_only` | `seed` | Present in Gilb/comparable list. Needs package/runtime validation. |
| IVA Connect / IVA MCU / IVA One | unknown | `blocked_missing_bundle` | `verify_required` | Desktop macOS support exists, but exact bundle ID is not verified. |
| VideoMost | unknown | `blocked_missing_bundle` | `verify_required` | Desktop client exists, but exact macOS bundle ID is not verified. |
| Dion | unknown | `blocked_missing_bundle` | `verify_required` | macOS packages are documented, but exact bundle ID is not verified. |
| Pruffme | unknown | `manual_or_browser_only` | `verify_required` | Appears primarily web-first in this pass. Use browser path unless a desktop bundle is verified. |
| RosChat / MiniCom-PING | unknown | `blocked_missing_bundle` | `verify_required` | Windows/Linux packages found; no trustworthy macOS app bundle in this pass. |
| tada.team | unknown | `blocked_missing_bundle` | `verify_required` | macOS App Store availability is noted publicly, but bundle ID is not verified. |
| VKurse / ВКурсе | unknown | `manual_or_browser_only` | `verify_required` | No separate desktop bundle found; may map to IVA/web surfaces. |

## Explicitly Not In Native Allowlist

| Target | Reason |
| --- | --- |
| Google Chrome / Chromium browsers | Browser audio ownership is too generic; use browser metadata path. |
| Yandex Browser | Browser audio ownership is too generic; use browser metadata path. |
| Safari | Browser audio ownership is too generic; use browser metadata path. |
| Microsoft Edge | Browser audio ownership is too generic; use browser metadata path. |
| Firefox | Browser audio ownership is too generic; use browser metadata path. |
| Opera | Browser audio ownership is too generic; use browser metadata path. |
| Krisp or other audio processing layers | Not a meeting app target; ignore if it appears as non-allowlisted ownership. |

## Promotion Rule

Move a target to `prompt_enabled` only after:

1. Current app identity is verified from installed app or official package.
2. A real call or microphone-test run emits `AudioHAL` ownership for the target bundle ID.
3. Leaving/quitting the call removes that target ownership.
4. Idle launch or brief prejoin/device-test behavior is documented.
5. The target passes GRAF policy gates: prompt, visible local recording state,
   one-action stop, metadata-only diagnostics, and reversible target-scoped
   auto-record settings.
