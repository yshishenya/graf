# Data Model: Сквозное укрепление интерфейса GRAF

**Feature**: `293-interface-hardening` | **Date**: 2026-11-10

## CaptureStatusPresentation

Представление состояния записи для всех нативных поверхностей.

| Поле | Тип | Правила |
|---|---|---|
| `kind` | `CaptureStatusKind` | `idle`, `detecting`, `starting`, `active`, `paused`, `degraded`, `stopping`, `stopped`, `failed` |
| `title` | `String` | Единственный источник текста; без внутренних кодов |
| `detail` | `String?` | Причина/ограничение; не дублирует title |
| `systemImage` | `String` | SF Symbol |
| `tone` | `StatusTone` | `neutral`, `success`, `warning`, `danger`, `muted` |
| `isActionable` | `Bool` | Показывать ли блокирующее действие |
| `showsStop` | `Bool` | Доступна ли остановка |
| `showsPause` | `Bool` | Доступна ли пауза |
| `showsResume` | `Bool` | Доступно ли возобновление |

Инварианты:
- `active` и `starting` всегда `showsStop == true`.
- `paused` показывает `showsResume == true` и `showsStop == true`.
- `failed` не притворяется успехом; `tone == .danger` или `.warning`.
- `detail` не содержит `_`, `/`, `\`, `sessionId`, `failureCode`, путей, URL, токенов, паролей и других credentials.

## RecordingBlockerPresentation

| Поле | Тип | Правила |
|---|---|---|
| `kind` | `RecordingBlockerKind` | `permission`, `storage`, `capture`, `policy`, `indicator`, `source`, `alreadyRecording`, `unknown` |
| `title` | `String` | Короткий заголовок |
| `detail` | `String` | Понятная причина и следующее действие |
| `recoveryAction` | `RecordingRecoveryAction?` | `openPermissions`, `retry`, `stop`, `chooseMicrophone`, `openStorage`, `none` |
| `isRetryable` | `Bool` | Можно ли повторить без изменения настроек |

Инварианты:
- `detail` не содержит внутренних кодов и путей.
- `permission` всегда предлагает открыть настройки или повторить проверку.
- `storage` не предлагает продолжить запись.

### Blocker → retryable → recovery

| Kind | Retryable | Recovery action | Видимое действие |
|---|---|---|---|
| `permission` | да, после изменения | `openPermissions`/`retry` | «Открыть настройки» / «Проверить ещё раз» |
| `storage` | да, после освобождения места | `openStorage` | «Освободить место» |
| `capture` | да | `retry` | «Повторить» |
| `policy` | нет | `none`/`stop` | «Запись недоступна по правилам» |
| `indicator` | да | `retry` | «Восстановить индикатор» |
| `source` | да | `chooseMicrophone`/`retry` | «Выбрать микрофон» |
| `alreadyRecording` | да | `none` | «Запись уже идёт» |
| `unknown` | да | `retry` | «Повторить проверку» |

## LocalRecordingPresentation

| Поле | Тип | Правила |
|---|---|---|
| `status` | `LocalRecordingStatus` | `saving`, `active`, `saved`, `degraded`, `blocked`, `failed`, `terminal`, `deleting`, `corrupted`, `uploading`, `expired` |
| `title` | `String` | «Сохраняем запись…», «Сохранено на Mac», «Нужна помощь» и т.п. |
| `detail` | `String?` | Ограничение/причина |
| `systemImage` | `String` | SF Symbol |
| `tone` | `StatusTone` | Цвет |
| `requiresAttention` | `Bool` | Подсветка и раскрытие |
| `allowsOpen` | `Bool` | Можно ли открыть локальную копию |
| `allowsSend` | `Bool` | Можно ли отправить |
| `allowsDelete` | `Bool` | Можно ли удалить локальную копию |

Инварианты:
- `saving` и `active` показывают прогресс/активность, но не `allowsDelete`.
- `saved` не требует внимания.
- `degraded` всегда `requiresAttention == true`, потому что ограничение проверки важно пользователю.
- `blocked` и `failed` всегда `requiresAttention == true`.
- `terminal` означает подтверждённое удаление/завершение; `allowsOpen/send/delete == false`.
- `deleting` показывает, что удаление в процессе; destructive-действия недоступны.
- `corrupted` показывает повреждение; `allowsOpen` только если есть проверяемый playable fragment, иначе false.
- `uploading` показывает реальный прогресс; отмена/повтор доступны по существующей политике; `requiresAttention == false`, пока нет ошибки.
- `expired` означает истёкший срок политики хранения; автоматическая отправка не выполняется, доступны локальное открытие (если playable), удаление и поддержка; `requiresAttention == true`.

### Condition → state → action → copy

| Условие | Состояние | Действие | Видимый результат |
|---|---|---|---|
| Идёт запись | `active` | Stop | «Идёт запись» |
| Идёт сохранение | `saving` | Stop/ожидание | «Сохраняем запись…» |
| Идёт частичная отправка | `uploading` | прогресс/отмена по политике | «Отправляем запись… N%» |
| Сохранено без ограничений | `saved` | Open/Send/Delete по правам | «Сохранено на Mac» |
| Сохранено с ограничением проверки | `degraded` | Open; Send по правам; помощь | «Сохранено с ограничением» |
| Отправка заблокирована | `blocked` | Повторить/поддержка | «Не можем отправить запись» |
| Запись не завершилась | `failed` | Повторить/поддержка/локальная копия | «Нужна помощь» |
| Срок хранения истёк | `expired` | Open при playable fragment; Delete; Support | «Срок хранения истёк» |
| Запись удалена подтверждённо | `terminal` | нет | «Удалено» |
| Удаление выполняется | `deleting` | нет | «Удаляем локальную копию…» |
| Файл повреждён | `corrupted` | Open только при playable fragment; поддержка | «Запись повреждена» |

## PermissionPresentation

| Поле | Тип | Правила |
|---|---|---|
| `step` | `DesktopPermissionStep?` | `microphone`, `systemAudio`, `nil` |
| `microphone` | `CapturePermissionState` | `unknown`, `granted`, `denied`, `restricted`, `stale` |
| `systemAudio` | `CapturePermissionState` | То же |
| `title` | `String` | Один источник текста |
| `detail` | `String` | Что произойдёт и что сделать |
| `primaryAction` | `PermissionPrimaryAction` | `request`, `openSettings`, `retry`, `finish`, `dismiss` |
| `isReady` | `Bool` | Оба `granted` |

Инварианты:
- `stale` всегда даёт `retry`, не `grant`.
- `restricted` не предлагает повторный запрос, только настройки/возврат.
- `isReady` только при обоих `granted`.

## InterfacePreferences

| Поле | Ключ | Тип | По умолчанию |
|---|---|---|---|
| `windowFrame` | `pro.2brain.graf.windowFrame` | `String?` (NSStringFromRect) | nil → 1280×760 по центру |
| `inspectorExpanded` | `pro.2brain.graf.inspectorExpanded` | `Bool` | false |
| `selectedMicrophoneDeviceID` | `pro.2brain.graf.selectedMicrophoneDeviceID` | `String?` | nil (системный по умолчанию) |
| `workspaceZoom` | `pro.2brain.graf.workspaceZoom` | `Double` | 1.0 (существующий) |

Правила:
- Некорректные/устаревшие значения сбрасываются к default.
- Выбранный микрофон сохраняется только если устройство всё ещё доступно; иначе fallback на системный.
- Размер окна ограничивается `minSize` и видимой областью экрана.
- Если выбранный микрофон отключился во время активной записи, запись не переключается на другое устройство автоматически: она переходит в `degraded`, системный звук продолжается, пользователь видит объяснение и Stop. После остановки сохранённый выбор остаётся, и при повторном подключении устройства он восстанавливается; если пользователь выбрал другой микрофон, новый выбор имеет приоритет.
- При закрытии приложения во время сохранения приложение даёт ограниченное время на завершение, сохраняет восстановимое локальное состояние при неудаче и не удаляет уже записанные данные.

## AccountSwitchResetPlan

| Поле | Действие |
|---|---|
| `cabinetRoute` | сбросить на `meetingsURL` |
| `calendarPrompt` | `nil` |
| `pendingCalendarPromptID` | `nil` |
| `failedCalendarPromptID` | `nil` |
| `selectedRecordingSessionID` | `nil` |
| `localRecordingPlayer` | `close()` |
| `uploadQueueItems` | перезагрузить в новом scope |
| `webBridges` | `invalidate()` |
| `webView` | новый `sessionBoundaryID`/reload |
| `notificationContext` | `refreshContext()`/invalidate |

Инварианты:
- Сброс выполняется до любого сетевого обновления.
- Старый заголовок встречи не остаётся видимым после смены аккаунта.
- Локальные записи не привязываются к новому аккаунту без явного правила.

## ReleaseEvidence

| Поле | Тип | Правила |
|---|---|---|
| `version` | CalVer `YYYY.MM.DD.N` | `2026.11.10.3` |
| `sourceSHA` | 40-hex | точный замороженный SHA |
| `tag` | `vYYYY.MM.DD.N` | аннотированный тег |
| `notaryRequestIDs` | `[String]` | ZIP и PKG |
| `notaryStatus` | `Accepted` | оба |
| `stapled` | `Bool` | true |
| `gatekeeper` | `Bool` | true |
| `sparkleSignature` | `Bool` | true |
| `appcastVersion` | CalVer | совпадает |
| `sha256` | 64-hex | ZIP/PKG |
| `releaseNotes` | русский Markdown | что изменилось, проверки, совместимость, ограничения |

## State transitions

```text
idle -> detecting -> starting -> active -> paused -> active
                                  |          |
                                  v          v
                               stopping -> stopped/finalized
                                  |
                                  v
                                failed
```

Правила:
- `starting`/`active`/`paused`/`degraded`/`stopping` показывают Stop.
- `stopping` не показывает повторный Stop как доступный.
- `failed` не показывает «Готово к записи» без нового старта.
- Смена аккаунта не меняет состояние локальной записи, но очищает UI-контекст старого аккаунта.
