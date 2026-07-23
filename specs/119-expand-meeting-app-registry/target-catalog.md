# 119 Meeting Target Evidence Catalog

**Research cutoff**: 2026-07-21

**Runtime platform**: macOS MVP
**Meaning of “supported” here**: every verified native target is
`prompt_enabled` and shown with the same auto-record checkbox as Zoom/Telemost.
Live validation is post-enable QA; auto-record itself requires explicit user
selection or “Выбрать все”.

The current runtime consumer is Feature
`124-restore-automatic-recording`: preserve the complete list, per-target
preference, eight-second prompt countdown, automatic start on expiry,
`Записать сейчас`, `Пропустить`, and `Всегда писать это приложение`.

## Evidence Sources

- **R092** — released `2026.07.09.4` feature-092 baseline and its recorded evidence.
- **PKG** — current downloadable macOS package `Info.plist` inspected.
- **LOCAL** — installed macOS application `Info.plist` inspected locally.
- **SRC** — maintained upstream source build definition inspected at a pinned commit.
- **GILB** — `gilb-ai/gilb-recorder` native meeting-app allowlist at
  `70efe0b37208d2e9be0568bf77b30a3a99ff691e`.
- **MUESLI** — `pHequals7/muesli` app identity list at
  `e0d6d7fada714be3f803fb17b24aafbafaafbd30`.
- **DIST** — current maintained macOS distribution/cask or MDM catalog metadata inspected.
- **APPLE** — current Apple App Store product and bundle metadata inspected.

All rows below are public product metadata. The catalog contains no meeting URL,
room code, participant, title, audio, transcript, credential, or private path.

## Released Baseline, Preserved

| Target | Product / aliases | Platform / market | Mode / evidence | Fingerprint or reason | Source |
| --- | --- | --- | --- | --- | --- |
| `zoom` | Zoom | macOS / global | prompt / runtime | `us.zoom.xos` | R092 |
| `yandex_telemost` | Yandex Telemost | macOS / Russia | prompt / runtime | `ru.yandex.desktop.telemost` | R092 |
| `microsoft_teams_classic` | Microsoft Teams classic | macOS / global | prompt / confirmed | `com.microsoft.teams` | R092, GILB |
| `microsoft_teams_new` | Microsoft Teams new | macOS / global | prompt / confirmed | `com.microsoft.teams2` | R092, GILB |
| `slack_calls` | Slack calls / Huddles | macOS / global | prompt / confirmed | `com.tinyspeck.slackmacgap` | R092, GILB |
| `webex` | Webex Meetings classic | macOS / global | prompt / seed | `com.cisco.webexmeetingsapp`, `com.webex.meetingmanager` | R092, GILB |
| `facetime` | FaceTime | macOS / global | prompt / seed | `com.apple.FaceTime` | R092, GILB |
| `discord` | Discord | macOS / global | prompt / seed | `com.hnc.Discord` | R092, GILB |
| `skype` | Skype | macOS / global | prompt / seed | `com.skype.skype` | R092, GILB |
| `whatsapp` | WhatsApp | macOS / global | prompt / seed | `net.whatsapp.WhatsApp` | R092, GILB |
| `voov_meeting` | VooV Meeting / Tencent Meeting | macOS / global | prompt / seed | `com.tencent.tencentmeeting` | R092, GILB |
| `tuple` | Tuple | macOS / global | prompt / seed | `app.tuple.app` | R092, GILB |
| `gather` | Gather | macOS / global | prompt / seed | `com.gather.Gather` | R092, GILB |
| `kontur_talk` | Контур.Толк | macOS / Russia | prompt / package | `kontur.talk` | R092 |
| `mts_link` | MTS Link | macOS / Russia | prompt / package | `ru.weteams.desktop` | R092 |
| `trueconf` | TrueConf | macOS / Russia | prompt / package | `org.trueconf.client` | R092 |
| `vk_calls` | VK Calls | macOS / Russia | prompt / package | `com.vk.calls.native.1` | R092 |
| `vk_teams` | VK Teams | macOS / Russia | prompt / installed | `ru.mail.messenger-biz-avocado-desktop` | R092 |
| `vinteo` | VINTEO | macOS / Russia | prompt / package | `com.vinteo.desktop` | R092 |
| `express` | eXpress | macOS / Russia | prompt / package | `ru.unlimitedtech.express.desktop` | R092 |
| `pachca` | Пачка | macOS / Russia | prompt / package | `com.todesktop.240607opwvcw853` | R092 |
| `salutejazz` | SaluteJazz | macOS / Russia | prompt / seed | `salutejazz.jazz-app` | R092, GILB |
| `iva_connect` | IVA Connect | macOS / Russia | prompt / package | `su.ivcs.ucim` | Apple package metadata |
| `videomost` | VideoMost | macOS / Russia | prompt / package | `com.videomost.lite` | Apple package metadata |
| `dion` | DION | macOS / Russia | prompt / package | `vc.dion.desktop` | official signed 5.33.0 DMG |
| `yandex_telemost_web` | Yandex Telemost web | browser / Russia | manual / verify | family `yandex_telemost` | R092 |
| `google_meet_web` | Google Meet web | browser / global | manual / verify | family `google_meet` | R092 |
| `pruffme` | Pruffme | browser / Russia | manual / verify | family `pruffme` | R092 |
| `roschat_minicom_ping` | RosChat MiniCom-PING | macOS / Russia | blocked / verify | current safe ID not proven | R092 |
| `tada_team` | tada.team | macOS / Russia | blocked / verify | current safe ID not proven | R092 |
| `vkurse` | VKurse | browser / Russia | manual / verify | no safe native identity | R092 |

## Verified Native Expansion

Every row is prompt-enabled in the common applications list. Package/source
identity does not assert a live call receipt; results are added to
`live-validation.md` after enablement.

| Target | Product / aliases | Market | Evidence | macOS bundle ID(s) | Source |
| --- | --- | --- | --- | --- | --- |
| `telegram_macos` | Telegram for macOS / Telegram Lite | global | installed | `ru.keepcoder.Telegram` | PKG |
| `telegram_desktop` | Telegram Desktop / TDX / Forkgram / 64Gram | global | installed | `com.tdesktop.Telegram` | LOCAL, PKG, SRC |
| `telegram_a` | Telegram A | global | package | `org.telegram.TelegramA` | DIST |
| `ayugram_desktop` | AyuGram Desktop | global | installed | `one.ayugram.AyuGramDesktop` | LOCAL, SRC `ba8c1a6b…` |
| `kotatogram_desktop` | Kotatogram Desktop | global | package | `io.github.kotatogram` | SRC `7263a1b5…` |
| `zoom_phone` | Zoom Phone | global | confirmed | `us.zoom.ZoomPhone` | MUESLI |
| `aircall` | Aircall / Aircall Workspace | global | package | `io.aircall.phone`, `io.aircall.workspace` | GILB, DIST |
| `dialpad` | Dialpad / Dialpad Meetings | global | package | `com.electron.dialpad`, `com.electron.uberconference` | GILB, DIST |
| `ringcentral` | RingCentral current / RingCentral classic / Glip | global | package | `com.ringcentral.glip`, `com.ringcentral.RingCentral`, `com.Glip.Glip` | DIST |
| `gotomeeting` | GoTo / GoTo Meeting / GoToMeeting classic | global | package | `com.gotomeeting`, `com.logmein.GoToMeeting`, `com.logmein.goto` | DIST |
| `jitsi_desktop` | Jitsi Desktop / Jitsi Meet | global | package | `org.jitsi.jitsi`, `org.jitsi.jitsi-meet` | DIST, SRC |
| `signal_calls` | Signal calls | global | package | `org.whispersystems.signal-desktop` | DIST |
| `viber_calls` | Viber calls | global | package | `com.viber.osx` | DIST |
| `element_calls` | Element / Matrix calls | global | package | `im.riot.app` | DIST |
| `wire_calls` | Wire calls | global | package | `com.wearezeta.zclient.mac` | DIST |
| `wechat_calls` | WeChat calls | global | package | `com.tencent.xinWeChat` | DIST |
| `wecom_calls` | WeCom / WeChat Work calls | enterprise | package | `com.tencent.WeWorkMac` | DIST |
| `cisco_jabber` | Cisco Jabber | enterprise | package | `com.cisco.Jabber` | DIST |
| `lifesize` | Lifesize | enterprise | package | `com.lifesize.cloud` | DIST |
| `mattermost_calls` | Mattermost calls | enterprise | package | `Mattermost.Desktop` | DIST |
| `rocket_chat_calls` | Rocket.Chat calls | enterprise | package | `chat.rocket` | DIST |
| `zulip_calls` | Zulip calls | enterprise | package | `org.zulip.zulip-electron` | DIST |
| `tandem` | Tandem | global | package | `tandem.app` | DIST |
| `teamspeak` | TeamSpeak 3 | global | package | `com.teamspeak.TeamSpeak3` | DIST |
| `lark` | Lark / Feishu | global | package | `com.electron.lark` | DIST |
| `dingtalk` | DingTalk | global | package | `com.alibaba.DingTalkMac` | DIST |
| `vk_messenger_calls` | VK Messenger calls | Russia | package | `com.vk.messages` | DIST |
| `webex_current` | Webex current | enterprise | package | `Cisco-Systems.Spark` | DIST |
| `jami` | Jami | global | package | `cx.ring.Ring` | DIST |
| `linphone` | Linphone | global | package | `org.linphone.Linphone` | DIST |
| `mumble` | Mumble | global | package | `net.sourceforge.mumble.Mumble` | DIST |
| `three_cx` | 3CX | enterprise | package | `com.3cx.macos` | DIST |
| `pexip` | Pexip Infinity Connect | enterprise | package | `com.pexip.infinityconnect` | DIST |
| `vsee` | VSee Messenger | enterprise | package | `com.vsee.vsee` | DIST |
| `zoho_cliq` | Zoho Cliq | enterprise | package | `com.zoho.cliq` | DIST |
| `line_calls` | LINE calls | global | package | `jp.naver.line.mac` | APPLE |
| `kakaotalk_calls` | KakaoTalk calls | global | package | `com.kakao.KakaoTalkMac` | APPLE |
| `eight_by_eight_work` | 8x8 Work | enterprise | package | `com.electron.8x8---virtual-office` | DIST |
| `onsip` | OnSIP | enterprise | package | `com.onsip.app` | APPLE |
| `telephone_sip` | Telephone SIP calls | global | package | `com.tlphn.Telephone` | APPLE |
| `vonage_business` | Vonage Business Communications | enterprise | package | `com.vonage.vbc` | DIST |
| `avaya_cloud_office` | Avaya Cloud Office | enterprise | package | `com.cloudoffice.app` | DIST |
| `cloudtalk_phone` | CloudTalk Phone | enterprise | package | `com.cloudtalk-phone.app` | DIST |
| `cloudya` | Cloudya | enterprise | package | `X26F74J8TH.net.nfon.app.cloudya` | DIST |
| `enreach_contact` | Enreach Contact | enterprise | package | `com.electron.enreachcontact` | DIST |
| `teamviewer_meeting` | TeamViewer Meeting | enterprise | package | `com.teamviewer.blizz` | DIST |
| `alfaview` | alfaview | global | package | `com.alfaview.desktop` | DIST |
| `loop_messenger` | LOOP Messenger calls | global | package | `ru.loop.app` | DIST |
| `sipgate` | sipgate | enterprise | package | `com.sipgate.desktop` | DIST |
| `tencent_meeting` | Tencent Meeting | global | package | `com.tencent.meeting` | DIST |
| `yealink_meeting` | Yealink Meeting | enterprise | package | `com.yealink.meeting.app` | official signed 4.7.43 arm64 DMG |
| `adobe_connect` | Adobe Connect | enterprise | package | `com.adobe.adobeconnect.app` | DIST |
| `quo_business_phone` | Quo / OpenPhone | enterprise | package | `ca.illusive.openphone` | DIST |
| `teamviewer_quickjoin` | TeamViewer QuickJoin | enterprise | package | `com.teamviewer.TeamViewerQJ` | DIST |

Expansion result: 85 targets, 87 distinct macOS bundle IDs, 79 prompt-enabled
native targets, 2 blocked native targets, 3 browser/manual targets, and 1
cross-platform/manual target. Exact counts are asserted from the migration.

## Telegram Candidates Considered But Not Added As Current macOS Identities

| Candidate | Classification | Reason |
| --- | --- | --- |
| TDX | alias of `telegram_desktop` | Current macOS source uses `com.tdesktop.Telegram`. |
| Forkgram | alias of `telegram_desktop` | Current package uses `com.tdesktop.Telegram`. |
| 64Gram | alias of `telegram_desktop` | Current macOS source uses `com.tdesktop.Telegram`. |
| Telegram Lite | alias of `telegram_macos` | Product rename/history shares `ru.keepcoder.Telegram`. |
| Bettergram | historical/deferred | Repository and releases are stale; no current maintained macOS package proof. |
| Unigram | excluded | Windows client, no current macOS build. |
| Nekogram / NekoX / Telegram X forks | excluded | Android/mobile families, no current macOS desktop package. |
| Plus Messenger / iMe / Nicegram | excluded | Mobile-first clients; a current macOS runtime package identity was not proven. |
| WebK / WebA / other web clients | browser/manual | A browser client is not a native app fingerprint and generic browser audio is unsafe. |
| Linux-only tdesktop forks | excluded | macOS MVP cannot claim a Linux application identity. |

## Browser Provider Research Backlog

The following maintained or historically common services were reviewed from
MeetingBar and vendor catalogs: Zoom/ZoomGov, Teams, Webex, Jitsi, RingCentral,
GoTo Meeting/Webinar, 8x8, Whereby, Vonage, Around, Discord, Slack Huddles,
Gather, Tuple, Pumble, Doxy.me, Zoho Cliq, Livestorm, Riverside, StreamYard,
LiveKit, Demodesk, Gong, Chorus, Luma, oVice, VSee, Lifesize, TeamViewer Meeting,
VooV, Lark/Feishu, Blackboard, and Amazon Chime.

Only the five families already recognized by production code are represented as
runtime browser classifications. Discontinued services (including BlueJeans,
Join.me, StarLeaf, and the consumer Amazon Chime service), landing-only pages,
and providers without safe joined-page metadata remain historical/deferred.
