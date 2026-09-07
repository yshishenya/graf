# Contract: Windows native desktop boundary

Дата: 2026-08-23

Контракт сохраняет границу Feature 058/057/177 для нового Windows host. Он не
создаёт новый серверный API и не разрешает удалённой странице владеть capture.

## 1. Ownership

| Capability | Windows native | Server WebView |
|---|---:|---:|
| Record/Pause/Resume/Stop | owner | no authority |
| capture readiness/permissions | owner | bounded read-only state |
| render loopback/microphone/AEC/timeline | owner | none |
| active indicator/tray/Stop | owner | cannot hide |
| local package/manifest/integrity | owner | no file path/access |
| upload queue/retry/reconcile | owner through existing GRAF API | auth page can recover session |
| meeting list/detail/review | no duplicate | owner |
| settings page/account/workspace | only native-only settings | owner when route is allowed |
| deletion report and server lifecycle | no business decision | owner; local purge remains native |
| MediaScribe/MinIO credentials | never | server only |

## 2. Readiness gate

`Record` can enter `starting` only when every condition is true:

- microphone privacy state is granted and selected/default capture endpoint is
  available;
- render endpoint is available for shared loopback;
- endpoint formats can be normalized to 48 kHz mono;
- AEC3 static processor is created with the pinned configuration;
- AAC encoder is available for the normal playback artifact;
- local recording directory can be created and written atomically;
- WebView may be unavailable; it is not a capture prerequisite;
- native indicator and one-action Stop have been installed before the first audio
  batch is accepted.

If any condition is false, no normal recording starts. UI shows the safe reason
and recovery action. A missing WebView runtime or network is not converted into a
fake audio permission error.

Constitution 7: workspace legal-policy setup, participant notice/consent and
server recording-policy acknowledgements are not prerequisites. Remove their
unused fields/reason codes; never synthesize an approval. This does not change
server authentication, recording ownership or deletion authority. Both manual
and automatic Start use the same native gate; an existing active session or
failure to show the native indicator/Stop prevents another start.

## 3. Session transitions

```text
idle -> checking_readiness -> ready -> starting -> recording
recording <-> paused
recording/paused -> degraded -> stopping
recording/paused/starting -> stopping
stopping -> finalizing -> saved_local -> queued -> uploaded
finalizing -> failed|blocked
```

Rules:

- one `WindowsDesktopSession` can be active at a time;
- `Stop` is idempotent while `starting`, `recording`, `paused`, `degraded` or
  `stopping`; repeated clicks do not create a second finalizer;
- `Pause` is a privacy pause: keep the system reference and PTS timeline alive,
  feed a timestamped zero microphone contribution through the same AEC3 path,
  and preserve a bounded privacy segment in the manifest; do not switch to raw
  mic or invent silence by wall clock;
- `Resume` restores mic samples only after the same endpoint/timeline gates are
  valid;
- a route/clock/device discontinuity ends the trusted normal segment. The first
  version may finalize a proven cleaned prefix as degraded, but may not silently
  splice a new endpoint into the old normal package.

### Уточнение 2026-09-06: запуск и завершение (T081/T082/T084)

- Ручной и автоматический Start используют один нативный путь. Отдельный
  видимый overlay с состоянием и Stop показывается до передачи Start
  контроллеру; если показать его нельзя, Start отклоняется. Tray в скрытой
  области уведомлений не заменяет этот индикатор.
- Запуск асинхронный: не позднее пяти секунд по монотонным часам от перехода
  в `starting` оба нативных worker — system/render и microphone — должны
  подтвердить готовность для этой попытки. До этого ни один аудиоблок не
  принимается в timeline/AEC/writer. Ошибка, отмена или истечение срока
  прекращает запуск без записи; запоздалая готовность не возобновляет его.
  Эти пять секунд не заменяют восьмисекундный вопрос автозаписи.
- Stop доступен одним действием и остаётся отзывчивым, в том числе при
  `starting`: ожидание запуска, остановки worker или финализатора не блокирует
  поток UI. Повторный Stop не создаёт новую операцию завершения.
- В `stopping/finalizing` сохраняется исключительное владение сессией до
  фактического завершения worker, writer и атомарного сохранения итоговой
  локальной очереди. Новый Record не разрешается только потому, что Stop
  уже вернулся или истёк срок запуска.
- При незавершённой попытке записи обычное закрытие окна/приложения и
  `request_app_quit` откладывают завершение процесса до этого сохранения;
  нативный UI продолжает показывать состояние.
  Ошибка сохранения видима и не считается успешной финализацией. Ожидание
  сетевой отправки или доступности WebView для закрытия не требуется.

## 4. Capture source contract

Both sources publish `RecordingAudioBatch` values with:

- `source` (`system_render` or `microphone`);
- actual source format and normalized format;
- device/QPC-derived presentation timestamp;
- opaque clock domain and route generation;
- finite sample count and discontinuity marker.

Callbacks must only drain WASAPI packets and enqueue into a bounded queue. They
must not perform file I/O, WebView calls, UI work, allocations that can grow
without bound or blocking waits. The worker/timeline owns normalization,
alignment and AEC3.

The system source is the global mix from the selected/default render endpoint.
The microphone source is the selected/default physical capture endpoint. The
contract does not claim process isolation, and protected render content may be
unavailable.

Уточнение T081/T084 от 2026-09-07: `IAudioCaptureClient::GetBuffer` возвращает
`pu64QPCPosition` в 100-нс единицах, а `pu64DevicePosition` — в кадрах от
начала конкретного потока. Первое значение нельзя повторно делить на аппаратную
частоту QPC; второе нельзя считать общей шкалой двух устройств. Флаг
`AUDCLNT_BUFFERFLAGS_TIMESTAMP_ERROR` не разрешает использовать метку как
достоверную. Исправление единиц не отменяет контроль разрывов/дрейфа.

### Фоновая автоматическая запись и завершение встречи

US5/AC4–6: готовность не зависит от сворачивания главного окна/панели.
Существующий отдельный индикатор и Stop подготавливаются скрытыми. Фактический
показ и доступность Stop обязательны до захвата; ошибка не разрешает старт.
Нельзя показывать ложную активную запись при одной лишь подготовке.

Автоматическая запись отслеживается с принятого `starting`. Другой PID может
подтвердить продолжение только с той же точной проверенной идентичностью и
активными render/capture потоками. Свежий полный снимок не старше 2 секунд
принимается только с новым монотонным timestamp. После 15 секунд непрерывно
подтверждённого отсутствия вызывается обычный Stop/финализация. Ошибка,
устаревший/будущий/переставленный снимок или разрыв более 2 секунд прерывают
отсчёт отсутствия, но не продлевают предел 600 секунд без положительного
подтверждения. Повторный снимок не добавляет времени. Терминальное состояние,
ручной Stop/Record/Exit сбрасывают слежение без изменения сохранённого правила.

### Постоянные настройки и точная идентичность

US5/AC7–9: настройка сохраняется по `targetKey` общего каталога, ASCII
`[a-z][a-z0-9_]{0,63}`. Обнаружение, callbacks вопроса и срок текущей записи
используют `identityKey` (EXE SHA-256, DER сертификата SHA-256, ревизия).
Membership проверяет также targetKey: общий ключ продукта не разрешает
подменять точную identity. Несколько проверенных версий дают одну строку
настроек; все три режима сохраняются при одобренных обновлениях.

HKCU `ApplicationRulesV2`: заголовок `graf.automatic-recording.v2\n`, записи
`targetKey=always|ask|never\n`, максимум 64 KiB, без дублей/неполных строк.
Ошибка декодирования даёт Ask для всего документа. Одна атомарная запись;
ошибка сохранения не меняет прежний выбор и отображается. Правила временно
отсутствующих продуктов сохраняются, но действуют только при подтверждённой
identity. V1/global не читаются как разрешения и не удаляются. Происхождение
первой Teams-записи зафиксировано в research.md; её наличие не подтверждает
настоящую встречу или все версии программы.

## 5. Timeline and artifact contract

### Уточнение T085: общая шкала и ограниченная коррекция

- Начало каждого пакета определяется абсолютным QPC WASAPI в 100-нс
  единицах; округлять его до целых кадров источника до нормализации нельзя.
  После нормализации
  оба источника имеют общую шкалу 48 kHz. Независимые device origins не
  сдвигают шкалу; timeline начинает выдачу с первого общего интервала.
  Callback arrival, часы UI и время запуска worker не задают PTS.
- Device position отдельно проверяется на монотонность, неизменность формата
  и соответствие размеру предыдущего пакета. Несовпадение числа кадров
  устройства и полученных кадров не исправляется интерполяцией.
- Оценка дрейфа использует накопленный интервал от первой метки. Допустимый
  остаток: 100 ppm от ожидаемого числа кадров плюс фиксированная погрешность
  метки 1 ms и один кадр округления. Фиксированная погрешность не накапливается
  и не сбрасывается на каждом пакете: устойчивое превышение 100 ppm в итоге
  прекращает нормальный сегмент. Короткое колебание в этом пределе не считается
  доказанной ошибкой частоты. Сам остаток не разрешает восстанавливать пропажу
  данных: для восстановления действуют отдельные ограничения ниже.
- Normalizer непрерывно преобразует реально полученные семплы; не требует
  равенства QPC и счётчика поданных семплов. Он сохраняет фазу преобразования
  между пакетами и передаёт исходное временное смещение в timeline. Выходной
  PTS относится к первому фактически выданному семплу с учётом фазы и
  задержанных семплов, а не обязательно к началу текущего входного пакета.
  При точных непрерывных метках разбиение одного сигнала на разные пакеты
  сохраняет позиции/значения на общем обработанном интервале и не требует
  искусственной коррекции timeline. В частности, 441 + 441 входных семплов
  при 44.1 kHz дают второй выходной пакет с позиции 479, не 480, когда
  первый выдал 479 семплов. Проверяются также малые переменные пакеты.
  Начальный QPC не обязан совпадать с целым кадром источника. Normalizer
  сохраняет его полную точность, один раз округляет общий origin до 48 kHz
  и переносит только относительный остаток времени в выходную позицию.
  Число входных каналов, как и частота, неизменно для текущего normalizer.
- Timeline повторяет ограниченное правило macOS: положительное расхождение
  не более 48 кадров между последовательными пакетами без discontinuity
  соединяется линейной интерполяцией последнего/первого семпла; отрицательное
  не более 48 кадров обрезает перекрывающийся префикс нового пакета.
  Чтобы отличить новый маленький пакет от повтора округлённой метки, normalizer
  передаёт `normalizedFrameOffset` — позицию первого выданного семпла до
  коррекции часов, из своего счётчика deliveredFrames. После первого пакета
  следующий диапазон обязан точно продолжать предыдущий offset + count;
  повтор, обратный диапазон, пропуск и переполнение отвергаются независимо от
  PTS. Первый offset может быть ненулевым из-за подготовки устройств.
  Только для нового непрерывного диапазона отрицательная коррекция до 48
  допускает полную обрезку маленького пакета, в том числе при равном или
  уменьшившемся округлённом PTS. Исходный диапазон отмечается потреблённым,
  число обрезанных семплов учитывается, но AEC/writer не вызываются, конец
  канонической последовательности и последний сохранённый семпл не двигаются
  назад. Повтор такого пакета отвергается. Это не отменяет проверок raw QPC,
  device/count и флагов источника. Начало первого источника раньше второго обрезается до общего
  интервала, без накопления ненужного префикса в буфере.
- Подготовка новой сессии допускает отбрасывание только первого непустого
  пакета каждого источника с ровно DATA_DISCONTINUITY (0x1). Размер и формат
  должны быть допустимы; TIMESTAMP_ERROR, SILENT вместе с разрывом и неизвестные
  биты не получают исключения. Первый чистый пакет тоже расходует это право.
  Пакет освобождается целиком через проверенный ReleaseBuffer(count), без чтения
  звука и продвижения mapper/normalizer/timeline/writer. Начало пригодного
  сегмента задаёт следующий обычный пакет с абсолютным QPC; готовность worker
  наступает только после нормализации пригодных данных. Сохраняется таймаут
  старта 5 секунд, без повторного прогрева/переинициализации внутри записи.
  Число успешно отброшенных стартовых кадров учитывается отдельно по источнику,
  не считается записанными/восстановленными кадрами. Это правило подготовки
  приложения, не гарантия безвредности первого флага Windows.
- Расхождение больше 48 кадров, последующий DATA_DISCONTINUITY,
  TIMESTAMP_ERROR, смена clock domain/route/формата и переполнение по-прежнему
  прекращают нормальный сегмент. Коррекция не разрешает скрывать отсутствующий
  источник, повторять старый пакет или добавлять тишину по настенным часам.
- Test-first: независимые origins/старты; 44.1/48 kHz и переменные размеры;
  ±100 ppm с округлением; колебание и возврат к стабильным меткам;
  границы ±48/49, повтор/пропуск диапазона и полная обрезка нового маленького
  пакета с последующим продолжением; несовпадение
  count/device delta; startup/midstream flags. Проверять mapper → normalizer
  → timeline вместе, не только классы отдельно. Короткая синтетическая
  проверка не закрывает SC-003 и настоящую запись T084.
- Безопасная сводка завершённой сессии содержит по каждому источнику
  `*_startup_discarded_frames` (0..4800, только успешное освобождение) и
  `*_clock_fault`: none, invalid_packet, timestamp_error, discontinuity,
  non_monotonic, sample_count_mismatch или clock_drift. Отказ фиксируется
  типизированным значением; неизвестный enum выводится как unknown.
  Сводка по-прежнему <=1024 байт, без сырых меток времени, звука, путей и
  текстов ошибок устройства. Общий reason_code и v2/v5 не меняются.

`RecordingAudioTimeline` is the only alignment owner:

1. compare clock domains and route generations;
2. reject invalid/backward timestamps and gaps above the approved bound;
3. normalize both sources to 48 kHz mono float;
4. emit 480-sample pairs;
5. call AEC3 render/reference first, microphone second;
6. mix cleaned microphone with unchanged system reference;
7. send contiguous canonical chunks to the writer.

Normal output is exactly:

- `meeting-transcription.wav`: PCM signed 16-bit little-endian, 16 kHz, mono;
- `meeting-review.m4a`: AAC-LC, 48 kHz, mono;
- `manifest.json`: existing v5-compatible schema with optional Windows health
  metadata.

The package-to-server mapping is not optional. Windows MUST write the same wire
contract as the current macOS v5 client:

- manifest `schema_version`: `local-recording-manifest.v5`;
- manifest `canonical_mix_profile`: `canonical-mix.v1`;
- meeting creation `source_kind`: `initial_mixed_recording`;
- meeting creation `media_scribe_source_mode`: `single_wav_v1`;
- upload-session roles: `manifest`, `media`, `playback`;
- local `mixed_meeting_audio` maps to wire role `media` and
  `meeting-transcription.wav`;
- local `review_playback` maps to wire role `playback` and
  `meeting-review.m4a`.

The native client uses the existing endpoints and idempotency scopes: `POST
/api/v1/meetings`, `POST /api/v1/meetings/{meeting_id}/upload-sessions`, and
the existing per-track part/missing-range/finalize endpoints. The meeting and
upload-session keys are derived from the immutable local directory/session
identity. A Windows implementation MUST NOT omit `source_kind` or silently
fall back to the historical `initial_recording`/`microphone`/`system` shape.

The writer validates byte count, hash, decodable format, frame count and duration
before changing the package to normal/saved. No normal package is created from
an unprocessed raw microphone path.

## 6. Failure and degraded policy

| Failure | Native result | Normal package? |
|---|---|---:|
| microphone denied/missing | block start; show recovery | no |
| render endpoint missing | block start; show recovery | no |
| format normalization unavailable | block start or degraded prefix | no |
| AEC3 creation/process error | block or finalize cleaned prefix | no |
| endpoint invalidated/service stopped | end trusted segment; Stop remains | no |
| timestamp/gap/clock failure | end trusted segment; bounded reason | no |
| queue overflow | end trusted segment; record count | no |
| protected render content | explicit limited/degraded state | only if all required gates still pass |
| disk full/finalization failure | preserve verified prefix and ledger | no |
| WebView/network unavailable | native capture/local custody continues | yes, if audio gates pass |

Failures contain only stable reason codes, counters, durations and safe recovery
actions. Raw input is never used as a hidden fallback.

## 7. Local custody and upload

The Windows writer finalizes local package before any network call. The queue:

- uses the existing `desktop-upload-queue.v2` ledger and item identity;
- writes atomically and quarantines malformed documents;
- runs on launch, activation, auth change, network recovery, wake, scheduled
  retry and local finalization;
- reconciles server truth before upload/finalize/review/purge;
- resumes accepted ranges and does not create duplicate meeting/upload sessions;
- exposes owner/action policy, not raw transport controls, to the user;
- acknowledges local purge only after deletion, tombstone or cryptographic
  unrecoverability is verified.

The client talks only to the existing GRAF desktop upload API. No audio request
goes from Windows directly to MediaScribe, MinIO or an upstream provider.

### Уточнение 2026-09-06: принадлежность локальной записи (T083)

Очередь сохраняет подтверждённые `ownerUserId`/`ownerWorkspaceId` рядом с записью,
не учётные данные. Владелец фиксируется в момент начала записи, а не при её
завершении. Текущий пользователь и рабочее пространство подтверждаются только
существующим `GET /api/v1/auth/me` с текущей сессией. Если пространство ещё
неизвестно, клиент сначала вызывает `GET /desktop/settings/spaces` с той же
сессией в `X-Auth-Session`, без `X-Workspace-Id` и `X-Device-Id`. Это серверный
JSON вида `{"spaces":[{"id":"UUID","active":true}]}`, а не DOM.
Каждый элемент, включая неактивные, обязан быть объектом со строковым
UUID `id` и булевым `active`; неправильные типы не преобразуются.
Повторные JSON-ключи и повторные UUID отвергают весь ответ, а не пропускаются.
Дополнительные поля могут присутствовать, но не являются источником полномочий.
Нужен ровно один объект с булевым `active: true` и корректным UUID `id`;
пустой/неоднозначный/повреждённый ответ не разрешает выбирать первое пространство.
Затем `/auth/me` получает этот UUID через `X-Workspace-Id`; ответ должен
содержать совпадающий `workspace_id`, корректный `user_id` и непустой корректный
`active_session_id`; все три поля — строки UUID, не числа/null/объекты.
Все ответы ограничены 2 MiB, список — 1024 элементами;
превышение отвергается целиком. Редиректы отключены; принимается только HTTP 200.
Токен сессии не меняется между запросами и не сохраняется в очередь или журнал.
Отмена проверяется до/после каждого запроса, смена поколения входа отвергает
запоздалый результат. Успех этой проверки не даёт полномочий серверной очистки
локальных копий конкретной установки. Перед отправкой нативный
клиент повторно проверяет совпадение владельца. Смена сессии отменяет старую
отправку; ответ старого запроса не может изменить очередь новой сессии.

Старые строки v2 и запись без входа имеют неизвестного владельца. Отсутствие
полей совместимо с чтением, но не является разрешением автоматически отправить
запись в аккаунт, вошедший следующим. Для такой записи «Отправить» требует
явного нативного подтверждения отправки выбранной записи в текущий аккаунт.
Подтверждённого прежнего владельца менять нельзя: при несовпадении требуется
вход в исходный аккаунт. Недоступный `/auth/me`, ошибка сохранения принадлежности,
пустые или некорректные идентификаторы блокируют отправку, не локальную запись.

Проверки: вход A→B при ожидающей отправке; выход во время записи; повторный вход
в A с новой сессией; неизвестная старая строка; подтверждение/отмена назначения;
сбой реестра очереди; запоздалый ответ проверки аккаунта. Ни один отрицательный
сценарий не создаёт встречу и не отправляет аудио в другой аккаунт.

### Уточнение 2026-09-06: восстановление отправки без тупиков (T083/T084)

- Лимит автоматических повторов не блокирует явное «Отправить»: пользователь
  может повторить выбранную запись после восстановления сервиса. Неизвестные,
  уже отправленные и изолированные повреждённые записи не переводятся в отправку;
  принадлежность и принятые сервером диапазоны сохраняются.
- Ошибка сети, HTTP 408/429/5xx при проверке аккаунта допускает ограниченный
  автоматический повтор без события из WebView. HTTP 401/403 требует входа;
  отсутствие/несовпадение подтверждённого владельца по-прежнему запрещает отправку.
  Неправильный ответ не считается подтверждением аккаунта.
- После перезапуска сохранённый промежуточный `uploading` возобновляется через
  сверку состояния сервера: живого работника от предыдущего процесса нет.
  Полная проверка реестра предшествует восстановлению; принятые диапазоны и
  идентификаторы не теряются. Повреждённый реестр остаётся изолированным.
- Повтор после истечения серверной сессии не переиспользует ключ истёкшей
  сессии и не создаёт дубль при потерянном ответе. Сброс счётчика повторов
  пользователем не меняет идентичность записи.

Регрессии: исчерпание повторов → явная отправка; краткий сетевой отказ проверки
аккаунта → scheduled recovery; 401/403 и другой аккаунт → ни одного запроса
аудио; перезапуск между сохранением серверных диапазонов и конечного статуса;
повторное истечение upload session после ручного восстановления.

## 8. Indicator and accessibility

The shell must expose a persistent native recording strip with status, source
scope copy and Stop. When the main window is hidden/minimized, the tray item
continues to show recording state and Stop. It must support keyboard focus,
accessible name/description, high contrast and 200% DPI. Color alone cannot
convey active/degraded/paused state.

The indicator state is derived from the native session, not from WebView DOM or a
web message. A navigation failure cannot remove it.

## 9. Evidence and logging

Allowed fields include:

- app/build/OS/architecture;
- state and safe reason code;
- source class (`render_loopback`, `microphone`), format class, route generation;
- bounded counters, byte counts, durations and retry class;
- redacted device fingerprint.

Forbidden fields include raw audio, transcript text, signed URLs, authorization
headers, cookies, passwords, local absolute paths, process command lines and
private meeting identifiers.

### Уточнение 2026-09-06: доступная безопасная сводка (T081/T084)

Нативный интерфейс должен предоставлять действующую кнопку копирования
безопасной сводки последней завершённой попытки записи. Она доступна только после формирования
неизменяемого итогового снимка, когда worker и writer действительно завершены,
а не из изменяющихся данных активной сессии. Успех копирования показывается
только после фактической записи текста в буфер обмена; ошибка явно видима.

Сводка содержит только ограниченный набор метаданных из §9: итоговое состояние,
безопасную причину и измеренные значения. Число обработанных и записанных
10-мс блоков берётся раздельно из фактических результатов timeline и writer;
длительность сохранённого звука выводится из записанных блоков/семплов, не из
настенных часов. Нет измерения — поле отсутствует или явно недоступно: нули
overflow/drop и другие успешные показатели нельзя подставлять как заглушки.

Сырой идентификатор endpoint всегда хешируется перед включением в сводку,
независимо от его префикса или внешнего вида; произвольная строка не становится
доверенным fingerprint по совпадению формата. Аудио, содержимое встречи, пути
и учётные данные не копируются. Действие работает локально, не запускает
захват, отправку записи или другие сетевые запросы. Эти уточнения покрываются
существующими T081/T082 и проверками T084; наличие текста не закрывает реализацию.
