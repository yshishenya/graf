# Research: установка, TCC и перезапуск GRAF на macOS

## Вопросы

1. Можно ли убрать предупреждение Gatekeeper на чужом Mac без Apple Developer
   account?
2. Почему микрофон остаётся в состоянии «Запрещено» и не добавляется вручную?
3. Почему системный «Quit & Reopen» может застревать на модальном окне GRAF?

## Наблюдения в репозитории

- `build-local-installer.sh` создаёт стабильный `GRAF.app` с bundle identifier
  `pro.2brain.graf`, но обычный локальный `.pkg` остаётся без подписи пакета.
- Вложенное приложение подписывается локальным self-signed identity
  `GRAF Local Code Signing`. Это сохраняет designated requirement на машине
  владельца, но не является переносимым публичным доверием.
- Installed `Info.plist` содержит `NSMicrophoneUsageDescription` и
  `NSScreenCaptureUsageDescription`, но не содержит отдельного
  `NSAudioCaptureUsageDescription`. Для system-audio-first потока описание
  системного аудио должно быть явно отражено в метаданных приложения.
- Installed `v2026.07.24.2` имеет правильные bundle id, путь и локальную
  signing lineage, но его hardened-runtime подпись содержит только
  `com.apple.security.cs.disable-library-validation`; entitlement
  `com.apple.security.device.audio-input` отсутствует. Поэтому полный сброс
  TCC не меняет ситуацию: macOS не регистрирует приложение как допустимый
  клиент микрофона.
- `AVCaptureDevice.requestAccess(for: .audio)` уже является правильным первым
  запросом микрофона. После `denied` повторный вызов не должен быть основным
  recovery-действием: пользователю нужен раздел Privacy & Security >
  Microphone.
- Onboarding использует SwiftUI `.sheet`, а lifecycle delegate закрывает только
  `attachedSheet` и `sheetParent`. В коде нет явного `NSApp.abortModal()` для
  активной AppKit modal session, поэтому системный quit/reopen может ждать
  модальный цикл, который SwiftUI sheet уже не отражает как обычный sheet.

## Проверенные внешние рекомендации

- Apple требует usage description для media capture и рекомендует проверять
  текущий authorization status перед захватом:
  [Requesting Authorization for Media Capture on macOS](https://developer.apple.com/documentation/bundleresources/requesting-authorization-for-media-capture-on-macos)
  и [`AVCaptureDevice.requestAccess`](https://developer.apple.com/documentation/avfoundation/avcapturedevice/requestaccess%28for%3Acompletionhandler%3A%29).
- Для hardened-runtime приложения Apple отдельно документирует
  `com.apple.security.device.audio-input` как entitlement, разрешающий запись
  аудио через Core Audio:
  [Audio Input entitlement](https://developer.apple.com/documentation/bundleresources/entitlements/com.apple.security.device.audio-input).
- ScreenCaptureKit требует screen-capture usage description; после выдачи
  screen/system-audio access процесс может потребовать перезапуск:
  [Capturing screen content in macOS](https://developer.apple.com/documentation/screencapturekit/capturing-screen-content-in-macos).
- Пользовательское управление находится в разделе Screen & System Audio
  Recording:
  [Apple Support](https://support.apple.com/guide/mac-help/control-access-screen-system-audio-recording-mchld6aa7d23/mac).
- Для приложения от неизвестного разработчика Apple поддерживает разовое
  ручное действие Open Anyway в Privacy & Security либо повторное открытие из
  Finder через Control-click > Open:
  [Open a Mac app from an unknown developer](https://support.apple.com/guide/mac-help/open-a-mac-app-from-an-unknown-developer-mh40616/mac).
- Публичное автоматическое доверие требует Developer ID и notarization:
  [Developer ID](https://developer.apple.com/support/developer-id/) и
  [Notarizing macOS software](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution).
- При возврате `.terminateLater` приложение обязано вызвать
  `reply(toApplicationShouldTerminate:)` после завершения bounded cleanup:
  [applicationShouldTerminate](https://developer.apple.com/documentation/appkit/nsapplicationdelegate/applicationshouldterminate%28_%3A%29)
  и [reply](https://developer.apple.com/documentation/appkit/nsapplication/reply%28toapplicationshouldterminate%3A%29).

## Решения

### Sparkle bootstrap and release channel

- The repository already embeds Sparkle 2.9.4 and has a single active public
  Ed25519 manifest. The smallest safe change is to configure the existing
  installer with `GRAF_UPDATE_FEED_URL`; adding another updater or rotating the
  key would break continuity.
- A package built without the feed and public key cannot discover future
  updates, even when the public appcast is valid. Therefore the first migration
  is a manual updater-enabled bootstrap; later versions are delivered through
  the signed appcast.
- Sparkle release archives must preserve bundle id, local designated
  requirement, active public key and strictly increasing CalVer. The protected
  workflow stages versioned artifacts before the appcast and requires a safe
  release-operator Keychain attestation.
- The current no-account package remains a manual Gatekeeper channel. Sparkle
  signatures protect update authenticity, but they do not create public
  Gatekeeper trust or replace Developer ID/notarization.

### Gatekeeper

Не добавлять отключение Gatekeeper, снятие quarantine как пользовательский
workflow, TCC reset или попытку имитировать Developer ID. Вместо этого:

1. сохранить integrity checks приложения и вложенного кода;
2. честно описать локальный канал как self-signed/без публичного notarization;
3. дать один системный manual trust path;
4. оставить public Developer ID/notarization отдельным release gate.

### Микрофон

Сохранить штатный AVFoundation request на состоянии `unknown`. Для `denied` и
`restricted` primary recovery должен вести в системные настройки и не обещать
повторный prompt или обход политики. Список микрофона в UI остаётся независимым
от system-audio статуса.

Для всех hardened-runtime сборок добавить `com.apple.security.device.audio-input`
в подпись самого `GRAF.app`. Для teamless Sparkle-сборки сохранить рядом
`com.apple.security.cs.disable-library-validation`; для team-identified сборки
не отключать library validation. Проверять entitlement только у нового
кандидата, чтобы разрешить безопасный переход со старого `.2`, в котором он
отсутствовал.

### Перезапуск

Добавить в onboarding явное действие «Перезапустить GRAF» после открытия раздела
Screen & System Audio Recording. Перед `terminateLater`:

1. сбросить SwiftUI onboarding state и meeting prompt;
2. завершить attached/detached sheets;
3. вызвать `NSApp.abortModal()` для активной modal session;
4. закрыть видимые вспомогательные modal windows;
5. запустить существующий capture cleanup и сохранить 10-секундный timeout.

После нового процесса статус должен вычисляться заново; готовность допускается
только при `microphone == granted` и `systemAudio == granted`.

## Не выбранные альтернативы

- `tccutil reset`, правка базы TCC, PPPC profile и MDM: нарушают продуктовые
  privacy gates и не являются допустимым способом выдать доступ.
- Возврат удалённого HAL/virtual audio driver: противоречит текущему MVP и не
  решает Gatekeeper/TCC проблему.
- Запуск приложения через global `spctl --master-disable`: слишком широкий и
  небезопасный workaround для пользователя.
- Принудительный `kill -9`: может потерять локальный файл и нарушает bounded
  cleanup contract.
