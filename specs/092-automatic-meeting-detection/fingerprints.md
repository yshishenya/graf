# 092 Meeting Detection Fingerprint Appendix

**Status**: research seed for `$speckit-plan`

**Date**: 2026-07-08

**Scope**: macOS bundle IDs for the first Gilb-style native-app detector,
Windows executable/process names for future Windows support, and browser URL
families for web meetings.

The native macOS detector allowlist registry lives in
`specs/092-automatic-meeting-detection/native-allowlist.md`. This appendix keeps
the evidence behind that registry.

## Confidence Rules

- **confirmed**: found in vendor/admin documentation, MDM/security allowlists,
  or multiple independent public technical lists.
- **runtime_verified**: observed on the local Mac through macOS `AudioHAL`
  app-ownership unified-log events during a live app run. This confirms that the
  Gilb-style detector can see active audio ownership for the target bundle, but
  first-release behavior still goes through GRAF's prompt, debounce, stop, and
  settings gates.
- **runtime_start_verified**: observed target `AudioHAL` ownership for a bundle
  start on the local Mac, but did not capture the corresponding ownership
  removal/end event in the same pass. This is useful evidence, but not enough
  to promote a target to Tier A without a later end-state check.
- **package_verified**: extracted from the current macOS app package
  (`Contents/Info.plist` / code signature) without installing or launching the
  app. This confirms app identity, but does not yet prove live microphone
  ownership during a meeting.
- **installed_verified**: extracted from a locally installed app and optionally
  checked for idle launch behavior. This confirms app identity on the test Mac,
  but does not yet prove live audio ownership during a meeting.
- **seed**: found in Gilb or comparable OSS allowlists and plausible for first
  planning, but still needs live QA on current app versions.
- **verify_required**: the product exists or has desktop downloads, but public
  sources did not expose a trustworthy current bundle ID/process name. Planning
  must install or unpack the app and capture the fingerprint before Tier A.
- **future_windows**: saved for future Windows detector work; not part of the
  first macOS implementation.

Apple's canonical way to get a macOS bundle identifier is to inspect the app's
`Contents/Info.plist` / `CFBundleIdentifier`. Windows process names must be
verified from the installed executable or live process, because installer file
names often differ from runtime process names.

Vendor download links, `.app` names, `.dmg` / `.msi` package names, install
directories, preference plist names, and desktop shortcuts are inventory hints.
They are useful for QA setup but are not enough to promote a target to Tier A
unless the runtime bundle ID/process and live audio ownership are
verified.

## Package Verification Pass

On 2026-07-08, selected macOS packages were downloaded to a temporary `/tmp`
lab, mounted read-only with `hdiutil attach -readonly -nobrowse -noautoopen`,
inspected through `Contents/Info.plist` and `codesign -dv`, then detached. Apps
were not copied into `/Applications`, launched, granted permissions, or added to
login items.

This pass verified package identity for Yandex Telemost, Контур.Толк, MTS Link,
TrueConf, VK Calls, VINTEO, eXpress, Пачка, and Yandex Browser. It does not
replace the runtime meeting test: each native meeting target still needs a real
call and macOS audio ownership check before Tier A auto-detection.

## Local Runtime Checks

On 2026-07-08, the locally installed `/Applications/TrueConf Client.app` was
checked without recording audio:

- installed app identity matches the package pass: `org.trueconf.client`,
  executable `TrueConf Client`, version `8.5.4`, team `G39BQY9ZQ8`;
- local metadata reports display name `TrueConf.app`, while the bundle path and
  `CFBundleDisplayName` remain `TrueConf Client`;
- launching the app idle did not emit an `AudioHAL` audio ownership event
  during the observation window;
- no live-call `AudioHAL` ownership was captured in this pass, so TrueConf still
  needs a real call or microphone-test run that emits ownership for
  `org.trueconf.client` before it can be promoted to Tier A.

On 2026-07-08, the locally installed `/Applications/Yandex.Telemost.app` was
checked through the same unified-log path:

- installed app identity matches the package pass bundle ID:
  `ru.yandex.desktop.telemost`, executable `Yandex.Telemost`, local version
  `2.37.4`, team `477EAT77S3`;
- starting a meeting emitted `AudioHAL` ownership for
  `ru.yandex.desktop.telemost`;
- non-allowlisted audio utility ownership remains ignored by the allowlist-only
  detector input;
- quitting Telemost removes the target ownership and drives end-state detection.

On 2026-07-08, the locally installed `/Applications/VK Teams.app` was checked
without recording audio:

- installed app identity: `ru.mail.messenger-biz-avocado-desktop`, executable
  `VK Teams`, version `25.4.3`, team `4D6LA585PP`;
- launching the app idle did not emit an `AudioHAL` audio ownership event
  during the observation window;
- live-call `AudioHAL` ownership was not captured because this local environment could
  not enter a VK Teams call without account authorization. It still needs a
  signed-in call or microphone-test run that emits ownership for
  `ru.mail.messenger-biz-avocado-desktop` before Tier A.

On 2026-07-08, the locally installed `/Applications/zoom.us.app` was checked
without recording audio:

- installed app identity: `us.zoom.xos`, executable `zoom.us`, version
  `6.7.7.76486`, team `BJ4HAAB9B3`;
- during the observation window, the user started a Zoom meeting and macOS
  emitted ownership for `us.zoom.xos`;
- non-allowlisted audio utility ownership is ignored by the allowlist-only
  detector input;
- after closing Zoom with user approval, the stream moved to non-target
  ownership events and then to an empty ownership set, confirming target removal
  and end-state detection.

### Native-App Extrapolation

Yandex Telemost and Zoom both produced the same usable macOS pattern:
`AudioHAL` ownership appears for the allowlisted bundle ID when the app starts
using call audio, and the allowlisted target disappears when the app leaves or
quits. This supports a generic native-app detector for the first macOS release:

- keep a registry of approved native meeting bundle IDs;
- parse all macOS `AudioHAL` app-ownership events;
- ignore every ownership event not present in the approved native meeting
  allowlist;
- debounce start/end changes and feed GRAF prompt/auto-rule logic;
- do not create app-specific detection rules unless a target later proves to
  have non-standard runtime behavior.

This extrapolation applies to native macOS meeting apps. Browser meetings still
need browser metadata plus URL/calendar/join intent, and future Windows support
needs a separate WASAPI/process-session detector.

## macOS Native / Installed App Fingerprints

| Target | macOS bundle ID seed | Status | Notes |
| --- | --- | --- | --- |
| Zoom | `us.zoom.xos` | runtime_verified | Present in Gilb and MDM/security allowlists. Local runtime check on 2026-07-08 from installed app `zoom.us.app` version `6.7.7.76486`, team `BJ4HAAB9B3`: observed `AudioHAL` ownership during user-started meeting and target removal/end-state after closing Zoom. |
| Microsoft Teams classic | `com.microsoft.teams` | confirmed | Classic Teams bundle ID. |
| Microsoft Teams new/work/school | `com.microsoft.teams2` | confirmed | New Teams bundle ID. |
| Webex Meetings/App | `com.cisco.webexmeetingsapp`, `com.webex.meetingmanager` | seed | Present in Gilb and OSS screen-sharing lists; confirm current Webex app flavor during QA. |
| Slack | `com.tinyspeck.slackmacgap` | confirmed | Slack admin docs use this domain for desktop configuration. |
| FaceTime | `com.apple.FaceTime` | seed | Built-in Apple app; confirm audio ownership behavior. |
| Discord | `com.hnc.Discord` | seed | Present in Gilb/comparable OSS lists. |
| Skype | `com.skype.skype` | seed | Present in Gilb; product status should be checked before Tier A. |
| WhatsApp | `net.whatsapp.WhatsApp` | seed | Present in Gilb. |
| VooV Meeting | `com.tencent.tencentmeeting` | seed | Present in Gilb; lower Russian-market priority. |
| Tuple | `app.tuple.app` | seed | Present in Gilb; lower priority. |
| Gather | `com.gather.Gather` | seed | Present in Gilb; lower priority. |
| Yandex Telemost | `ru.yandex.desktop.telemost` | runtime_verified | Package-only verification on 2026-07-08 from official DMG (`2.36.4`) and local runtime verification from installed app (`2.37.4`): `Yandex.Telemost.app`, executable `Yandex.Telemost`, team `477EAT77S3`. Observed `AudioHAL` ownership start during a meeting and target ownership removal on quit; non-allowlisted ownership events are ignored. |
| Контур.Толк | `kontur.talk` | package_verified | Package-only verification on 2026-07-08 from official DMG: `Толк.app`, executable `Толк`, version `3.6.0`, team `VEWAJ43QEN`. Live audio ownership still needs verification. |
| SaluteJazz / Jazz | `salutejazz.jazz-app` | seed | Present in Gilb; live bundle verification required. |
| MTS Link / МТС Линк | `ru.weteams.desktop` | package_verified | Package-only verification on 2026-07-08 from official DMG: `МТС Линк.app`, executable `МТС Линк`, version `0.87.0`, team `ZZ645F8B29`. Live audio ownership still needs verification. |
| TrueConf | `org.trueconf.client` | package_verified | Package-only verification on 2026-07-08 from official DMG and local installed app check: `TrueConf Client.app`, executable `TrueConf Client`, version `8.5.4`, team `G39BQY9ZQ8`. Idle launch did not emit audio ownership; live call ownership still needs verification. |
| VK Calls | `com.vk.calls.native.1` | package_verified | Package-only verification on 2026-07-08 from official DMG: `VK Calls.app`, executable `VK Calls`, version `1.44.39190`, team `FD3X58MN39`. Live audio ownership still needs verification. |
| VK Teams / VK WorkSpace | `ru.mail.messenger-biz-avocado-desktop` | installed_verified | Local installed app check on 2026-07-08: `VK Teams.app`, executable `VK Teams`, version `25.4.3`, team `4D6LA585PP`. Idle launch did not emit audio ownership; live call ownership still needs verification with an authorized account. |
| IVA Connect / IVA MCU / IVA One | unknown | verify_required | IVA Connect Desktop official docs confirm Windows, Linux, and macOS support; exact bundle ID needs live verification. |
| VideoMost | unknown | verify_required | Official page confirms VideoMost Proton desktop Electron client; exact macOS bundle ID/package details need validation. |
| VINTEO | `com.vinteo.desktop` | package_verified | Package-only verification on 2026-07-08 from official ARM64 DMG: `VinteoDesktop.app`, executable `VinteoDesktop`, version `4.27.0`, team `U47995Q86Q`. Live audio ownership still needs verification. |
| Dion | unknown | verify_required | Official DION on-prem docs show macOS desktop packages such as `dion_5.21.0.dmg` and `Dion-5.21.0-universal.dmg`; bundle ID needs live verification. |
| eXpress | `ru.unlimitedtech.express.desktop` | package_verified | Package-only verification on 2026-07-08 from official ARM64 DMG: `eXpress.app`, executable `eXpress`, version `3.68.38`, team `NUMFWSGG8Z`. Live audio ownership still needs verification. |
| Pruffme | unknown | verify_required | Appears primarily web-first; desktop app fingerprint not confirmed. |
| РОСЧАТ / MiniCom-PING | unknown | verify_required | Public RosChat repository exposes Windows/Linux packages; no trustworthy macOS app/bundle found in this pass. |
| Пачка | `com.todesktop.240607opwvcw853` | package_verified | Package-only verification on 2026-07-08 from official ARM64 DMG: `Pachca.app`, executable `Pachca`, version `2.9.1`, team `GAU33Q8VQF`. Live audio ownership still needs verification. |
| tada.team | unknown | verify_required | Official FAQ says desktop app is available on macOS via App Store and Windows/Linux via direct links; bundle ID needs live verification. |
| ВКурсе | unknown | verify_required | No separate desktop bundle found; appears tied to IVA ecosystem or web/mobile surfaces. |

## Windows Future Fingerprints

These are not first-release requirements. They are saved to avoid losing
research when a future Windows desktop detector is planned.

| Target | Windows executable/process seed | Status | Notes |
| --- | --- | --- | --- |
| Zoom | `zoom.exe`, possible `CptHost.exe` helper | confirmed/seed | `zoom.exe` appears in security allowlists and Gilb; `CptHost.exe` appears in OSS screen-sharing detection lists and should be treated as helper-only until validated. |
| Microsoft Teams classic/new | `Teams.exe`, `ms-teams.exe` | confirmed | `Teams.exe` appears in security allowlists; Microsoft crash/support records show `ms-teams.exe` for new Teams. |
| Webex | `webex.exe`, `atmrg.exe`, `wmlhost.exe`, `webexmta.exe`, `washost.exe` | seed | Gilb maps `webex.exe`; security allowlists list Webex helper processes. Live QA must decide which process owns WASAPI mic sessions. |
| Slack | `slack.exe` | confirmed | Slack support docs mention `Slack.exe`; security allowlists agree. |
| Discord | `Discord.exe` | seed | Present in OSS process lists and Gilb map as lowercase `discord.exe`. |
| Skype | `skype.exe` | seed | Present in Gilb; product status should be checked before implementation. |
| WhatsApp | `whatsapp.exe` | seed | Present in Gilb. |
| VooV Meeting | `voovmeetingapp.exe` | seed | Present in Gilb. |
| Tuple | `tuple.exe` | seed | Present in Gilb. |
| Gather | `gather.exe` | seed | Present in Gilb. |
| Yandex Telemost | `yandextelemost.exe` | seed | Present in Gilb; verify current Windows build. |
| Контур.Толк | `ktalk.exe` | seed | Present in Gilb; verify current Windows build. |
| SaluteJazz / Jazz | `jazz.exe` | seed | Present in Gilb; verify current Windows build. |
| MTS Link / МТС Линк | unknown runtime process; installer `linkchats-desktop.exe`, MSI `linkchats-desktop.msi` | verify_required | Official docs confirm the installers and `%APPDATA%\MTS Link\config.json`; inspect installed process. |
| TrueConf | `TrueConf.exe` | confirmed | Official command-line docs use `TrueConf.exe` and default path `C:\Program Files\TrueConf\Client\TrueConf.exe`. |
| VK Teams | `vkteams.exe` | seed | Official docs confirm desktop downloads; Staffcop and third-party technical pages name `vkteams.exe`. Runtime owner of mic capture still needs validation. |
| VK Calls | unknown | verify_required | Must inspect current installer/app. |
| IVA Connect | unknown runtime process | verify_required | Official MSI docs confirm install locations `C:\Program Files\IVA Connect` and `%LOCALAPPDATA%\IVA Connect`; process name still needs live inspection. |
| VideoMost | unknown runtime process; package/app name `VideoMost Proton` | verify_required | Official page confirms desktop Electron client; exact executable name not found publicly. |
| VINTEO | unknown runtime process; installers `vinteo-desktop-4.27.0-x64.exe`, `vinteo-desktop-4.27.0-x64.msi` | verify_required | Official download center confirms packages; inspect installed process. |
| Dion | unknown runtime process; packages `dion_5.21.0.exe`, `dion_5.21.0.msi`, `Dion_Setup_5.21.0.exe` | verify_required | Official DION docs show package naming; inspect installed process. |
| eXpress | `eXpress.exe`; installers `eXpress Setup.exe`, `eXpress.msi` | confirmed | Official admin docs use `taskkill /IM eXpress.exe /F`, installer names, and install/cache/update directories. |
| Pruffme | unknown | verify_required | Likely web-first; validate before Windows work. |
| РОСЧАТ / MiniCom-PING | unknown runtime process; packages `roschat-*.exe`, `roschat.msi`, `minicom-ping-*.exe`, `minicom-ping-*.msi` | verify_required | Public RosChat repository confirms packages; inspect installed process. |
| Пачка | unknown runtime process; Windows NSIS installer and corporate MSI | verify_required | Official docs confirm Windows installers; inspect installed process. |
| tada.team | unknown runtime process; direct EXE x64/x32 and MSI links | verify_required | Official FAQ confirms Windows direct and MSI downloads; inspect installed process. |
| ВКурсе | unknown | verify_required | No separate Windows desktop fingerprint found; validate whether it maps to IVA Connect or web. |

## Browser App Fingerprints

Browser bundle/process fingerprints are for browser metadata adapters only.
They must not be added to the native audio-ownership allowlist.

| Browser | macOS bundle ID seed | Windows process seed | Status |
| --- | --- | --- | --- |
| Safari | `com.apple.Safari` | n/a | seed |
| Google Chrome | `com.google.Chrome` | `chrome.exe` | confirmed |
| Microsoft Edge | `com.microsoft.edgemac` | `msedge.exe` | seed |
| Firefox | `org.mozilla.firefox` | `firefox.exe` | confirmed/seed |
| Opera | `com.operasoftware.Opera` | `opera.exe` | seed |
| Yandex Browser | `ru.yandex.desktop.yandex-browser` | `browser.exe` or Yandex-specific Chromium process | package_verified | Package-only verification on 2026-07-08 from official DMG: `Yandex.app`, executable `Yandex`, version `26.6.0.1813`, team `477EAT77S3`. Windows process must be verified. |

## Browser Meeting URL Families

These are URL-family seeds for the browser detector. Store only service family,
host category, and pattern class in diagnostics; do not store full private URLs.

| Service | URL / host family seed | Status | Notes |
| --- | --- | --- | --- |
| Google Meet | `meet.google.com/<meeting-code>` | seed | Exclude home/new/landing/join/settings pages. |
| Microsoft Teams web | `teams.microsoft.com/l/meetup-join...`, Teams live/join paths | seed | Validate exact current routes in QA. |
| Zoom web | `zoom.us/j/...`, `/wc/...`, `/s/...` | seed | Validate region/custom domains. |
| Webex web | `*.webex.com/meet/...`, `*.webex.com/wbxmjs/...` and current join paths | verify_required | Webex routes vary by tenant/app version. |
| Yandex Telemost | `telemost.yandex.ru/...`, `telemost.yandex.com/...` | seed | Public docs confirm link-based join; exact meeting-code path must be sampled. |
| Контур.Толк | `talk.kontur.ru`, `*.ktalk.ru`, `yo.tel` | seed | Public support mentions workspace URLs like `xxxxxxxx.ktalk.ru`; exact meeting path must be sampled. |
| MTS Link | `mts-link.ru`, `my.mts-link.ru`, legacy `webinar.ru` / `events.webinar.ru` families | seed | Product renamed from Webinar.ru; exact meeting routes must be sampled. |
| TrueConf | `https://<server>/c/<CID>`, example `https://hq-trueconf.ru/c/<id>` | confirmed | TrueConf docs state conference page format and browser/app join choice. |
| VK Calls | `calls.vk.com`, `vk.com/call...` families | seed | Public docs confirm link/app join; exact route must be sampled. |
| VK Teams | VK WorkSpace / VK Teams tenant URLs | verify_required | Needs current tenant sample. |
| IVA Connect / IVA MCU | tenant/on-prem IVA URLs | verify_required | On-prem deployments may use arbitrary customer domains. |
| VideoMost | tenant/on-prem VideoMost URLs | verify_required | On-prem deployments may use arbitrary customer domains. |
| VINTEO | tenant/on-prem VINTEO URLs | verify_required | On-prem deployments may use arbitrary customer domains. |
| Dion | Dion public/tenant URLs | verify_required | Needs current sample. |
| eXpress | `express.ms` and customer domains | verify_required | Needs current meeting sample. |
| Pruffme | `pruffme.com` and customer domains | seed | Public product is web-first; exact meeting route must be sampled. |

## Planning Verification Tasks

Before any target is promoted to Tier A:

1. Install or unpack the current app package for macOS.
2. Read `CFBundleIdentifier` from `Contents/Info.plist`.
3. Start a real call and confirm macOS emits `AudioHAL` ownership for
   `<bundle_id>`.
4. Confirm process launch without mic does not prompt.
5. On Windows future work, install the app and map the executable that owns the
   active WASAPI capture session, not just the launcher/updater executable.
6. For browser services, sample real join links and classify URL paths into
   meeting, landing, prejoin, settings, and post-meeting pages.

## Source Notes

- Gilb allowlist and Windows map:
  https://github.com/gilb-ai/gilb-recorder/blob/main/crates/gilb-meeting/src/allowlist.rs
- Gilb macOS detector:
  https://github.com/gilb-ai/gilb-recorder/blob/main/crates/gilb-meeting/src/macos.rs
- Apple bundle ID extraction guidance:
  https://support.apple.com/guide/deployment/get-the-bundle-id-for-a-mac-app-dep0af2cd611/web
- Slack desktop configuration / cleanup docs:
  https://slack.com/help/articles/11906214948755-Manage-desktop-app-configurations
  and https://slack.com/help/articles/360048367814-Update-the-Slack-desktop-app
- Microsoft Teams macOS bundle ID notes:
  https://www.msb365.blog/?p=5429
- Check Point SASE certificate-pinning bypass process lists:
  https://sc1.checkpoint.com/documents/Infinity_Portal/WebAdminGuides/EN/SASE-Admin-Guide/Content/Topics-SASE-AG/Internet_Access/Certificate_Pinning.htm
- `no_screen_mirror` OSS screen-sharing process list:
  https://github.com/FlutterPlaza/no_screen_mirror
- MTS Link official desktop downloads:
  https://mts-link.ru/application/
  and https://help.mts-link.ru/article/19452
  and https://help.mts-link.ru/article/23258
  and direct macOS package:
  https://apps.webinar.ru/weteams/linkchats-desktop.dmg
- TrueConf macOS client and URL join docs:
  https://trueconf.com/downloads/mac.html
  and https://trueconf.com/blog/knowledge-base/launch-trueconf-client-applications-via-command-line-parameters
  and https://trueconf.com/blog/knowledge-base/join-video-conference
  and direct macOS package:
  https://trueconf.com/download/client/macos/trueconf_client.dmg
- IVA Connect Desktop docs:
  https://iva.ru/docs/desktop/latest/ug/introduction.html
  and https://iva.ru/docs/desktop/latest/ug/appendix/configuring-msi.html
- Yandex Telemost Homebrew cask and official pages:
  https://formulae.brew.sh/cask/yandextelemost
  and https://telemost.yandex.ru/
  and direct macOS package redirect sampled from `download-desktop`:
  https://disk.cdn.yandex.net/update/stable/430fd883e929fb671cd08c5990ab3d61/YandexTelemost.dmg
- Yandex Browser and Kontur Talk Homebrew cask JSON:
  https://formulae.brew.sh/api/cask/yandex.json
  and https://formulae.brew.sh/api/cask/kontur-talk.json
  and package URLs:
  https://download.cdn.yandex.net/browser/update/26_6_0_1813_111583_m_s_r/yandex.dmg
  and https://st.ktalk.host/ktalk-app/mac/ktalk.3.6.0-mac.dmg
- VK Calls Homebrew cask:
  https://github.com/Homebrew/homebrew-cask/blob/9b58803d31014ef0d6938d6d5366e6b0f1343e32/Casks/v/vk-calls.rb
  and current update/package metadata:
  https://vkcalls-native-ac.vk-apps.com/latest/latest-mac.yml
  and https://vkcalls-native-ac.vk-apps.com/1.44.39190/vk-calls-1.44.39190.dmg
- VK WorkSpace install docs and Staffcop VK Teams process note:
  https://workspace.vk.ru/docs/saas/user-guides/vk-teams/installation/installation
  and https://docs.staffcop.ru/cases/vkteams_key_size.html
- VINTEO download center:
  https://download.vinteo.com/VinteoClient/mac/4.27.0/
  and https://download.vinteo.com/VinteoClient/win/4.27.0/
  and direct ARM64 macOS package:
  https://download.vinteo.com/VinteoClient/mac/4.27.0/vinteo-desktop-4.27.0-arm64.dmg
- DION desktop package docs:
  https://faq-onprem.dion.vc/ru/2024-10/administration/desktop-download-page
- VideoMost Proton:
  https://www.videomost.com/videomost-server/videomost-proton
- eXpress download and installation docs:
  https://express.ms/en/download/
  and https://express.ms/en/faq/installation-and-requirements/
  and current ARM64 package redirect:
  https://express.ms/download/dmg-arm64
- Pachca desktop app docs:
  https://pachca.com/help-center/start/vsyo-pro-prilozheniya-pachki
  and direct ARM64 macOS package:
  https://install.pachca.com/mac/dmg/arm64
- tada.team FAQ:
  https://tdwiki.notion.site/FAQ-2d90114f90bc48a39851edccc0421f7d
- RosChat public package repository:
  https://repo.ros.chat/client/windows/
  and https://repo.ros.chat/client/windows/x64/
  and https://repo.ros.chat/client/linux/
