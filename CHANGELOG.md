# История изменений

Здесь фиксируются заметные изменения продукта.

Продуктовые релизы используют календарные версии вида `vYYYY.MM.DD.N`.
Вспомогательные библиотеки и инструменты могут использовать SemVer, если это
прямо указано в их документации.

## [Unreleased]

### Добавлено
- В компактной нативной панели главного окна появились прямые действия
  `Начать запись` и `Стоп`; во время активной записи отдельные
  `Пауза`/`Продолжить` и `Стоп` остаются доступны в нативном индикаторе.

### Изменено
- Feature `104-essential-interface-polish`: главное окно стало
  meeting-first — оставлены только рабочие `Мои встречи`, `Настройки`, поиск,
  фильтры, сортировка, загрузка и контекстные действия со встречами.
- Список встреч использует человеческие названия, русские длительности и
  итоговые состояния без бессмысленных завершённых `100%`-индикаторов.
- Навигация, toolbar, строки и нативная панель уплотнены для окон
  `1040×680` и `1280×760`; добавлены явный focus, Reduce Motion и
  responsive-collapse без потери доступных имён.
- После объединения с feature `098-calendar-auto-context-match` безопасный
  календарный контекст сохраняется, а блок `Ближайшие` появляется только для
  реальной доступной будущей встречи серии — без пустого placeholder и
  повторного предложения подключить календарь на главном экране.
- Поиск, статус, доступ и сортировка остаются доступны в компактном embedded-
  окне; счётчик активных фильтров учитывает только выбранные статус и доступ,
  а пользовательские группы `В обработке` и `Нужна помощь` включают все
  соответствующие внутренние состояния. Публичный API при этом сохраняет
  точную фильтрацию по запрошенному enum-статусу.
- Поиск сопоставляется с названием, которое видно в строке встречи;
  подтверждённые пользователем, календарные и вручную заданные названия не
  переписываются эвристиками для системных записей и имён файлов. SQL-
  предфильтр отсекает заведомо неподходящие строки до access/media-проекций,
  а browser/embedded-интерфейс не находит скрытые технические ID. Поиск по
  видимым дню и времени учитывает часовой пояс записи; публичный API сохраняет
  совместимость с техническим поиском.

### Исправлено
- Выбор строк, удаление, фильтры и сортировка сохраняют keyboard focus и
  корректно закрываются по Escape/клику снаружи; неуспешное массовое удаление
  повторяет только строки с ошибкой, а успешное не возвращает фокус в уже
  скрытую панель выбранных записей.
- Начало записи больше не раскрывает инспектор автоматически и не меняет
  ширину списка встреч; idle-состояние не показывает уровни записи.
- В компактном окне кнопка загрузки больше не растягивает toolbar при открытой
  нативной панели управления записью.
- При недоступном кабинете показываются центрированное человеческое сообщение,
  безопасная кнопка `Повторить` и отдельно доступное VoiceOver-действие без
  технических упоминаний сервера или данных доступа к календарю.
- В нативной панели полностью видны `Начать запись`, `Пауза`, `Продолжить` и
  `Остановить`; статус и действия больше не конкурируют за одну строку, а
  уровни микрофона и встречи не выходят за границы компактного инспектора.
- Убраны повторяющиеся idle/local-save/meeting-detected статусы и повторный
  `Стоп` во время сохранения; сохранённая запись получает понятный success-
  индикатор и единое VoiceOver-описание без ложного состояния выбора.
- Пользовательские состояния больше не показывают внутренние ID, локальные
  пути, телеметрию, Apple/WebRTC-названия, отладочную диагностику и формы
  технического отчёта.
- Названия вручную загруженных записей очищаются от расширений всех разрешённых
  аудио- и видеоформатов; из навигации и стилей удалены недостижимые состояния
  и селекторы прежнего интерфейса.
- Скрытая нижняя часть свёрнутого sidebar больше не попадает в клавиатурный
  порядок до явного раскрытия меню.
- Компактное действие записи не обходит активный календарный prompt: выбор
  встречи и явный старт без контекста остаются внутри одного decision flow.
- Нативный inspector показывает требующие реакции состояния и предупреждения
  о сроке локального хранения независимо от того, отвечает за следующий шаг
  владелец встречи, администратор, поддержка или политика хранения.
- Свёрнутый нативный inspector снова раскрывается, когда проблема локальной
  сохранности меняется или становится серьёзнее, даже если число затронутых
  записей осталось прежним.

### Безопасность
- Удаление технической информации относится только к presentation-слою:
  metadata-only диагностика, redaction и явная отправка безопасного запроса в
  поддержку сохранены; приватные данные встречи не добавлены в UI/evidence.

### Документы
- Добавлены спецификация, clean-room visual target, UX checklist и validation
  evidence фичи 104.

### Операции
- _Пока нет записей._

## [2026.07.13.3] - 2026-07-13


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- Production smoke cleanup удаляет calendar audit/context/match-attempt строки
  feature `098` до удаления синтетической встречи, поэтому FK-связи больше не
  прерывают финальный deploy gate и не оставляют smoke-остатки.

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.07.13.2] - 2026-07-13


### Добавлено
- Feature `098-calendar-auto-context-match` добавляет неблокирующее
  сопоставление начала записи с одним подходящим календарным событием,
  безопасный выбор при неоднозначности, явное продолжение без контекста и
  указатель на предыдущую доступную встречу той же серии.
- В web- и embedded-review появился единый блок `Контекст встречи` с
  неизменяемым snapshot названия, времени и состава приглашённых; roster явно
  отделён от подтверждённых спикеров.

### Изменено
- Безопасное календарное название применяется только к заменяемым app/generic
  названиям. Пользовательские, upload/file и legacy-названия не
  перезаписываются, а уже показанное название остаётся стабильным после
  исправления или очистки контекста.
- Desktop upload queue сохраняет только server-issued match attempt и выбранный
  event ID через retry; decision intent остаётся единственной серверной
  истиной внутри attempt. Capture, создание встречи, upload и processing
  остаются работоспособными при сбое или отсутствии календаря.

### Исправлено
- _Пока нет записей._

### Безопасность
- Calendar match/context в feature `098` ограничен owner/workspace/space,
  хранит только bounded snapshot и metadata-only audit, не выдаёт private
  event details/raw email и не создаёт attendee access, share, recipient,
  delivery или speaker-name side effects. Обычные acceptance-тесты этого
  среза не заменяют отдельно отложенный Codex Security scan.

### Документы
- Добавлены Spec Kit artifacts, requirement/scenario matrix и synthetic-only
  validation receipts для feature `098`; calendar/contact speaker naming
  оставлен отдельной будущей capability с собственными consent, confidence,
  correction, privacy и speaker-truth требованиями.

### Операции
- Миграция `0021_calendar_auto_context_match` добавляет одноразовые попытки
  сопоставления, единый context snapshot и title provenance; локальные SQLite
  upgrade/downgrade и disposable PostgreSQL/RLS проверки проходят. Feature
  слита через PR #3270; выпуск и production-развёртывание остаются отдельными
  release-gates.

## [2026.07.13.1] - 2026-07-13


### Добавлено
- _Пока нет записей._

### Изменено
- macOS recording architecture оставлена в единственном поддерживаемом виде:
  ScreenCaptureKit/system audio и app-owned microphone source явно передаются
  в локальный dual-track writer; отдельная legacy audio-routing реализация,
  shared-memory bridge, runtime orchestration и setup/repair UI удалены.
- Локальный installer теперь содержит только GRAF.app и не устанавливает,
  обновляет, восстанавливает или удаляет привилегированный audio component.

### Исправлено
- Streaming manual media upload снова публикует обязательный multipart OpenAPI
  contract и возвращает `422` для отсутствующих обязательных form-полей;
  macOS regression coverage для desktop cabinet снова компилируется и
  проверяет изоляцию identity headers по scheme, host и port.

### Безопасность
- App-only uninstaller больше не принимает переопределяемые через environment
  пути удаления и действует только на точные `/Applications/GRAF.app` и
  `/Applications/2brain Rec.app`.
- macOS desktop cabinet больше не прикрепляет Authorization и desktop identity headers к первому WebView-запросу на внешний HTTPS origin auth-provider при восстановлении входа.
- Support incident reports теперь редактируют клиентские строки по строгим metadata-схемам и ограничивают `local_purge_tasks` безопасными enum-значениями, чтобы encoded private content не уходил в GitHub issue.
- Browser OAuth-вход через Yandex/VK теперь привязывает callback провайдера к браузеру, начавшему вход, через короткоживущую `__Host-` nonce cookie и не позволяет захваченным callback URL закрепить браузер жертвы за чужим аккаунтом.
- Manual media upload endpoints теперь читают multipart body потоково после auth/CSRF checks, отклоняют oversized bodies до framework form spooling и больше не загружают весь media file в память.

### Документы
- Активные product/architecture/QA документы переведены на app-owned
  system-audio-first flow; исторический runtime proof сохранен только как
  audit evidence, а для ранее установленного proof component добавлена
  отдельная ручная и узко ограниченная cleanup-инструкция.

## [2026.07.11.1] - 2026-07-11


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- macOS desktop теперь надежнее запускает системный звук после prompt в
  автоопределенной встрече: ScreenCaptureKit стартует с audio+screen output,
  запись видео при этом не ведется, а startup timeout больше не обрывает
  рабочий Telemost-сценарий.
- Feature `090-manual-media-upload-ui`: security closeout и исправление
  production migration `0020_user_scoped_recording_ids` теперь находятся в
  `master`, поэтому исходный код, release tag и production runtime снова имеют
  проверяемую общую историю.

### Безопасность
- Повторный security review feature `090` не выявил новых подтвержденных
  exploitable findings в auth, CSRF, tenant isolation, upload/finalize,
  storage и egress diff после слияния с актуальным `master`.

### Документы
- Closeout evidence feature `090` обновлен фактическими PR, release и
  validation результатами; specs `097-101` остаются draft и не считаются
  реализованными этим релизом.

### Операции
- Релиз подготовлен от merge SHA PR #3040 после focused server validation,
  macOS validation и полного local CI. Публичный notarized macOS installer
  остается недоступен без Developer ID Application/Installer identities.

## [2026.07.10.2] - 2026-07-10


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- Production migration `0020_user_scoped_recording_ids` теперь распознает
  legacy unique constraints по фактическим колонкам, а не только по ожидаемым
  именам, поэтому обновление проходит на базах с исторически отличающимся
  именованием constraints.

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.07.10.1] - 2026-07-10


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- Manual upload/finalize path больше не собирает multipart track в памяти:
  accepted parts читаются/пишутся потоково, persistence failure не оставляет
  ложного finalized state, а materialized objects чистятся при конфликте.
- Review playback/download теперь использует только stored
  `meeting-review.m4a`; legacy mic/system artifacts больше не показывают audio
  download как доступный без canonical playback artifact.
- Streaming audio playback/download audit больше не называет подготовленный
  HTTP stream `completed`: новые события `playback_stream_prepared` и
  `download_stream_prepared` сохраняют post-egress deletion truth без
  overclaim полного client receipt.
- Transcript/review speaker labels канонизируются как `SPEAKER_00`,
  `SPEAKER_01`, выбираются по временному пересечению с diarization и не
  подменяются source-role или calendar roster labels.

### Безопасность
- Email signup и provider callback paths теперь уважают workspace enrollment
  policy; прямой provider-link endpoint безопасно отклоняет raw
  client-supplied provider subject до отдельного verified callback flow.
- Auth, calendar, processing, support, admin/cabinet mutating routes закрыты от
  ambient browser-cookie CSRF там, где действие меняет состояние; explicit
  bearer/session-header and device-header clients остаются совместимыми, а
  пустой session header не отключает CSRF для cookie-сессии.
- Поиск записи по `local_recording_id` теперь ограничен пользователем внутри workspace,
  поэтому один пользователь больше не раскрывает состояние записи другого.
- Processing pickup и retention run теперь требуют роль owner/admin workspace
  вместо доступа обычного member.
- Rate limit support incident теперь устойчив к смене dedupe key: новый
  fingerprint отчета не обходит throttle.

### Документы
- Добавлены future feature specs `097-101` для workspace onboarding,
  calendar auto-context matching, canonical review m4a normalization, verified
  provider-link callback flow и streaming egress audit semantics.

### Операции
- _Пока нет записей._

## [2026.07.09.16] - 2026-07-09


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- macOS desktop больше не берет meeting target registry из Foundation HTTP
  cache; registry fetch всегда идет к серверу с нашим `If-None-Match` и
  last-good cache, чтобы старый `macos_sensor_indicators_mic` не ломал
  автоопределение после server-published registry update.
- macOS desktop явно прикладывает bridged owner-session cookie к native desktop
  API requests на тот же origin, чтобы WebView-login и native registry/upload
  client использовали одну production auth session.
- Лог `meeting_detection.registry_refresh_failed` теперь показывает безопасный
  remote error и fallback-cache error отдельно, чтобы не маскировать причину
  refresh failure старым локальным cache decode.

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- Обновлен public static installer package для `/download`; SHA-256 package:
  `1cd58b09355fff51baf01169c29e97ffdf36eb2bc155cc0e79225b6d30da2318`.

## [2026.07.09.8] - 2026-07-09


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- Production Docker image больше не ссылается на удаленный локальный
  `meeting-target-registry.seed.json`; registry публикуется серверной
  миграцией, а не копируется из macOS bundle.

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- Добавлен CI guard, который проверяет, что локальные `COPY`-source в
  `infra/server/Dockerfile` существуют в репозитории до remote deploy.
- Обновлен public static installer package для `/download`; SHA-256 package:
  `76fa3d12393265bf020f42963972067f099a42cc13066b1dd46cfc3d57ab80aa`.

## [2026.07.09.7] - 2026-07-09


### Добавлено
- Feature `092-automatic-meeting-detection`: macOS desktop теперь обновляет
  meeting target registry не только на старте/active/auth, но и после wake и
  периодически в фоне через `If-None-Match`, чтобы долгоживущие клиенты
  подтягивали server-published allowlist без перезапуска.

### Изменено
- Feature `092-automatic-meeting-detection`: target registry теперь полностью
  server-published; macOS app bundle больше не содержит локальную копию, а
  клиент использует remote fetch и last-good cache.
- Feature `092-automatic-meeting-detection`: prompt/auto-record eligibility
  теперь проходит через общий `RecordingPrerequisiteGate`, а floating prompt
  показывает безопасные строки про режим записи, источники, workspace policy
  state и причину детекта без приватных meeting metadata.
- Feature `092-automatic-meeting-detection`: `AudioHAL` unified-log stream
  теперь сужен до RunningBoard-процесса перед матчингом `AudioHAL`; 10-минутный
  local resource gate после изменения дал CPU p95 `0.0%`, CPU max `0.6%`,
  RSS p95 `5.17 MB`.

### Исправлено
- Feature `092-automatic-meeting-detection`: свежая macOS установка без
  сохраненного registry cache больше не останавливает auto-detection до remote
  fetch; клиент запускает detector shell и сразу подтягивает registry с сервера.
- Feature `092-automatic-meeting-detection`: rollback миграции registry больше
  не оставляет сервер без published global registry, если до upgrade уже была
  опубликованная версия.

### Безопасность
- _Пока нет записей._

### Документы
- Feature `092-automatic-meeting-detection`: closeout evidence обновлен для
  Microsoft Teams diagnostic-only решения, Firefox/non-Chromium browser
  manual-only решения, resource gate и manual admin smoke ограничения.

### Операции
- Обновлен public static installer package для `/download`; SHA-256 package:
  `3e1f8b30481d8706be75a3d82465e21df782e576b3cd1b8829815318cff521bb`.

## [2026.07.09.6] - 2026-07-09


### Добавлено
- Feature `095-macos-permission-retention`: добавлен локальный self-signed
  signing path для owner-machine проверки сохранения macOS microphone и
  Screen/System Audio permissions после переустановки GRAF.

### Изменено
- _Пока нет записей._

### Исправлено
- Feature `095-macos-permission-retention`: permission onboarding и другие
  desktop prompts больше не должны блокировать macOS quit/relaunch; termination
  path закрывает modal state перед bounded cleanup reply.

### Безопасность
- _Пока нет записей._

### Документы
- Feature `095-macos-permission-retention`: добавлены Spec Kit artifacts,
  local signing runbook, metadata-only validation quickstart и явная граница,
  что local self-signed package не является Developer ID/notarized public
  release.

### Операции
- Feature `095-macos-permission-retention`: публичный download package
  `graf-local.pkg` обновлен сборкой `2026.07.09.6` для локального
  self-signed release path без Apple Developer ID/notarization.

## [2026.07.09.5] - 2026-07-09


### Добавлено
- Feature `091-mediascribe-result-contract`: добавлены безопасные диагностические
  признаки результата MediaScribe (`transcript_status`, `transcript_reason`,
  `error_code`, `error_origin`, `failure_reason`, `failure_source`) для
  различения `processed_no_transcript`, `input_audio_problem` и
  `mediascribe_service_problem`.

### Изменено
- Интеграция MediaScribe теперь использует `result.transcript_status` как
  главный индикатор наличия транскрипта. Готовая обработка без распознаваемой
  речи сохраняется как terminal business outcome, блокирует meeting outcomes с
  `failure_source=input_audio` и не запускает summary.

### Исправлено
- `invalid_audio_payload` от MediaScribe с `error_origin=input_audio` больше не
  считается сбоем сервиса транскрибации: GRAF показывает понятную причину про
  недекодируемый или поврежденный аудиофайл.
- Failed poll ответы MediaScribe теперь читают `error_code` и `error_origin`
  как на верхнем уровне, так и внутри `job`, чтобы `invalid_audio_payload`
  не превращался в ложный service outage из-за формы payload.
- `processing_results.transcript_status` теперь сохраняется из
  `result.transcript_status`, а не выводится из количества строк; явный
  `transcript_status="unavailable"` остается авторитетным даже если payload
  содержит лишние transcript-like rows.
- Endpoint статуса обработки больше не считает контент доступным только по
  `transcript_status="available"` / `diarization_status="available"`: для
  `content_available` теперь также нужны сохраненные строки сегментов.
- Для записи без распознаваемой речи UI показывает: "MediaScribe обработал
  запись, но транскрипт не создан: распознаваемая речь не найдена."
- Кнопка скачивания transcript не появляется, если сохраненного доступного
  транскрипта нет.

### Безопасность
- `transcript_status` и `transcript_reason` ограничены безопасными машинными
  значениями нового контракта; произвольные значения от внешнего сервиса не
  восстанавливаются из redaction в audit metadata и считаются malformed
  MediaScribe response без раскрытия текста.

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.07.09.4] - 2026-07-09


### Добавлено
- Feature `094-product-activation-analytics`: добавлен безопасный
  implementation scaffold продуктовой аналитики: disabled-by-default config,
  stable event catalog, forbidden-field validator, telemetry gate model,
  pseudonymous identity helpers, provider-disabled PostHog/Yandex wrappers,
  server-mediated API, macOS payload/client shell, env propagation, focused
  tests, smoke scripts и rollout/dashboard documentation без прод-запуска.

### Изменено
- _Пока нет записей._

### Исправлено
- _Пока нет записей._

### Безопасность
- Feature `094-product-activation-analytics`: product analytics запрещает raw
  identity, meeting content, transcript/audio/calendar text, local paths,
  signed URLs, tokens, secrets, device names и private free text; direct desktop
  provider egress закрыт без явных legal/security/QA/provider approval.

### Документы
- _Пока нет записей._

### Операции
- Feature `094-product-activation-analytics`: production env example и compose
  получили disabled-by-default product analytics placeholders только для
  `rec-api`; live PostHog/Yandex provider setup, production deploy и paid
  campaign launch остаются отдельными approvals.

## [2026.07.09.3] - 2026-07-09


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- Feature `092-automatic-meeting-detection`: native macOS meeting detection
  now uses `AudioHAL` app-ownership assertions as the primary Gilb-style signal
  instead of `sensor-indicators` mic-attribution; Yandex
  Telemost emits this ownership signal during an active meeting.
- Feature `092-automatic-meeting-detection`: the local macOS installer now
  packages the SwiftPM app resource bundle required by the installed `.app`.

### Безопасность
- _Пока нет записей._

### Документы
- Feature `092-automatic-meeting-detection`: refreshed allowlist,
  fingerprint, telemetry, quickstart, and Spec Kit language to describe
  `AudioHAL` ownership as the native-app detector signal and keep browser
  meetings on the metadata + calendar/join-intent path.

### Операции
- _Пока нет записей._

## [2026.07.09.2] - 2026-07-09


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- _Пока нет записей._

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- Обновлен публичный установщик GRAF для `/download` и GitHub Release assets,
  чтобы сайт отдавал macOS package той же релизной линии, что и установленное
  локальное приложение.

## [2026.07.09.1] - 2026-07-09


### Добавлено
- Feature `093-public-landing-analytics`: добавлена публичная аналитика
  лендинга и `/download` на Yandex Metrica с disabled-by-default runtime,
  UTM attribution, стабильными событиями воронки, consent UI на
  CookieConsent v3.1.0, legal pages и локальными assets без CDN.
- Feature `094-product-activation-analytics`: зафиксирован backlog/SDD prompt
  для следующей высокорисковой продуктовой аналитики после 093 с контекстом
  Yandex/PostHog, attribution bridge, masking/replay gates и production smoke
  lessons learned из public analytics closeout.
- Feature `092-automatic-meeting-detection`: заложен серверный и desktop
  фундамент для registry-driven определения встреч: metadata-only telemetry,
  admin review кандидатов и server-published target registry без production
  rollout.
- На macOS добавлены registry cache/fallback, VKS-candidate filter,
  telemetry rollups/uploader, primary `AudioHAL` app-ownership parser,
  detector debounce/end state, policy gates для prompt/target-scoped
  auto-record, local settings и metadata-only detector diagnostics.
- Заложен первый browser foundation без расширения: browser metadata
  классифицируется только вместе с calendar/join intent, а landing/new/join,
  settings/device-test/media/voice-search и missing metadata остаются
  manual-only/detect-only.

### Изменено
- _Пока нет записей._

### Исправлено
- Feature `093-public-landing-analytics`: production compose теперь передает
  runtime public analytics env в `rec-api`; post-deploy smoke поймал случай,
  когда `.env` на сервере был обновлен, но контейнер продолжал работать с
  disabled defaults.
- Feature `092-automatic-meeting-detection`: после критического review
  исправлен runtime path macOS detector: primary `AudioHAL` app-ownership
  stream подключен к detector decisioning/prompt/auto-record path, parser
  читает реальные `AudioHAL` ownership assertions,
  unknown short-duration candidates могут переоцениваться, а native browser
  audio ownership подавляется до browser metadata + calendar/join intent path.
- Feature `092-automatic-meeting-detection`: усилены серверные safety gates для
  registry/admin/telemetry: browser targets обязаны иметь browser metadata и
  calendar/join intent, merge в неизвестный target id отклоняется, добавлены
  uniqueness constraints для candidates/non-target rules, workspace draft stale
  guard не блокирует публикацию registry, desktop uploader уважает
  `next_upload_after`.

### Безопасность
- Feature `093-public-landing-analytics`: provider scripts не загружаются до
  согласия на analytics; Webvisor/replay ограничен публичными страницами и
  отдельной категорией `behavior_replay`; public analytics отсутствует на
  login, cabinet, admin, API, legal и product/content-bearing surfaces.
- Feature `092-automatic-meeting-detection`: telemetry/admin/diagnostics остаются
  metadata-only; low-score unknown apps redacted locally, Krisp/audio utilities
  and generic browser audio ownership suppressed, remote registry cannot enable
  behavior beyond compiled safety gates.
- Feature `092-automatic-meeting-detection`: local telemetry rollups теперь
  принудительно очищаются по retention cap `14 days / 1 MB` при записи и перед
  upload early-return path, включая disabled upload и backoff.

### Документы
- Feature `093-public-landing-analytics`: добавлены provider setup, Phase 2
  activation contract guardrails, implementation evidence, legal-readiness
  notes и campaign-readiness boundary с явным deferral для Google/GA4/GTM и
  PostHog/product analytics.
- Feature `092-automatic-meeting-detection`: добавлены Spec Kit artifacts,
  allowlist/fingerprint research, telemetry contracts и high-risk validation
  plan для первого detect-and-ask релиза.

### Операции
- Feature `093-public-landing-analytics`: production env example получил
  безопасные public analytics variables без live IDs; Yandex counter/goals,
  dashboard access, production deploy и provider smoke завершены для `/` и
  `/download`; paid campaign launch остается blocked до legal/campaign-
  readiness approval.
- Feature `092-automatic-meeting-detection`: focused validation passed server
  `48 passed`, macOS `124 tests`, forbidden-content source scan, and full
  `infra/scripts/ci-local.sh` with `1136 passed, 4 skipped, 1 warning`.

## [2026.07.08.7] - 2026-07-08


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- В приложении embedded WebView теперь открывает системный выбор файла для
  ручной загрузки записи, а кнопка `Загрузить` в кабинете остаётся
  серверной модалкой внутри списка встреч.

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.07.08.6] - 2026-07-08


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- Ручные однодорожечные расшифровки и speaker overview больше не показывают
  `Входящий звук` или `UNKNOWN` как участника: когда MediaScribe вернул
  diarization, review показывает строки из diarization с labels вида
  `SPEAKER_XX`; если diarization нет, ручной upload получает fallback
  `SPEAKER_00`. Если diarization пришла без текста, review не показывает
  пустые реплики и возвращается к transcript rows с `SPEAKER_XX` по таймингам.

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.07.08.5] - 2026-07-08


### Добавлено
- Добавлен операторский dry-run/execute скрипт для повторной обработки уже
  принятых ручных медиафайлов, которые упали до создания задания MediaScribe.

### Изменено
- Если пользователь не указал название при ручной загрузке, встреча получает
  название из имени выбранного файла; введённое пользователем название остаётся
  приоритетным.
- Сообщение о сбое `mediascribe_validation_failed` теперь честно говорит, что
  сервис расшифровки не принял медиафайл, а не что результат не удалось
  импортировать.

### Исправлено
- Однодорожечная ручная загрузка теперь отправляется в MediaScribe с безопасным
  синтетическим именем файла и корректным MIME-типом/расширением вместо
  безымянного `application/octet-stream`, чтобы валидные `m4a/mp4/wav/webm`
  файлы не отклонялись на submit.

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.07.08.4] - 2026-07-08


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- Встроенный macOS-кабинет больше не блокирует кнопку `Выйти` как внешний
  маршрут: выход теперь отправляется через разрешенный embedded-путь и сразу
  возвращает пользователя на вход.

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.07.08.3] - 2026-07-08


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- Иконка GRAF в macOS app bundle, favicon, apple-touch icon и локальных
  web static assets выровнена с последней иконкой из `2brain Rec.app`.
- Удалены старые черновые и backup-экспорты логотипа GRAF; в репозитории
  оставлены текущие `final-symbol`, favicon и handoff-метаданные.

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.07.08.2] - 2026-07-08


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- В ручной загрузке убран ручной ввод длительности: длительность остается
  справочной информацией из файла и отправляется технически после чтения
  метаданных.

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.07.08.1] - 2026-07-08


### Добавлено
- _Пока нет записей._

### Изменено
- Ручная загрузка теперь закрывает модалку после нажатия `Загрузить`;
  прогресс, статус и действия `Отменить`, `Повторить`, `Продолжить` и
  `Открыть` показываются в общем списке записей.

### Исправлено
- _Пока нет записей._

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.07.07.4] - 2026-07-07


### Добавлено
- _Пока нет записей._

### Изменено
- Ручная загрузка в кабинете получила короткую кнопку `Загрузить`, более
  понятную модалку с drag/drop-зоной, выбором файла, карточкой выбранного файла,
  процентом прогресса и аккуратным состоянием принятого файла.

### Исправлено
- _Пока нет записей._

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.07.07.3] - 2026-07-07


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- В кабинете появилась кнопка `Выйти`: она завершает текущую browser session,
  очищает session cookie и возвращает пользователя на страницу входа для
  повторной авторизации.

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.07.07.2] - 2026-07-07


### Добавлено
- Feature `087-own-media-upload-processing`: добавлен серверный путь
  `POST /api/v1/media-uploads` для загрузки одного пользовательского
  медиафайла как обычной встречи GRAF с пакетом `manifest + media`.
- Feature `090-manual-media-upload-ui`: в веб-кабинете и встроенном кабинете
  macOS добавлена ручная загрузка одного медиафайла с выбором файла,
  длительностью, прогрессом передачи, отменой до принятия сервером и переходом
  в обычную встречу.

### Изменено
- Обработка теперь различает обычные двухдорожечные записи с компьютера и
  однодорожечные ручные загрузки: ручные загрузки отправляются в серверный
  MediaScribe путь `POST /v1/audio/transcriptions`, а записи с компьютера
  продолжают использовать прежний двухдорожечный путь.
- Ручные загрузки теперь отображаются в списке и карточке встречи как обычные
  встречи с техническим source `manual_upload`, русской меткой происхождения
  `медиа` и теми же статусами отправки, обработки и готовности.

### Исправлено
- _Пока нет записей._

### Безопасность
- Feature `090-manual-media-upload-ui`: для загрузки из кабинета с пользовательской
  сессией добавлен отдельный CSRF-защищенный путь
  `POST /api/v1/cabinet/media-uploads`; старый встроенный контекст только с
  заголовками получает безопасное состояние входа или недоступности и не
  используется как граница небезопасной загрузки.

### Документы
- _Пока нет записей._

### Операции
- Для выпуска выполнены focused server/macOS сценарии, скан на запрещенное
  содержимое и полный локальный gate `infra/scripts/ci-local.sh`.

## [2026.07.07.1] - 2026-07-07


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- Записи одного пользователя больше не блокируются старым `device_id` после
  пересборки приложения или повторного входа: новый зарегистрированный device
  может продолжить серверную отправку своей записи, а активные upload sessions
  остаются device-bound.

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.07.04.1] - 2026-07-04

### Добавлено
- Серверный список `Записи встреч` теперь показывает активную отправку записи:
  статус `Отправляем`, процент, прогресс-бар и автообновление строки без
  ручного обновления страницы.

### Изменено
- _Пока нет записей._

### Исправлено
- Активная отправка больше не отображается как `Загружено`, пока серверный
  upload session еще находится в состоянии `uploading`.

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.07.03.5] - 2026-07-03


### Добавлено
- Публичная главная страница `rec.2brain.pro`: B2C-лендинг GRAF с прямым
  скачиванием приложения, product visuals и блоком готовых итогов встречи без
  demo/pilot flow.
- Добавлен путь `/download`: он отдает текущий установщик GRAF и показывает
  короткий путь первого запуска.

### Изменено
- Главная страница теперь выводит `Скачать GRAF` как основной CTA, а вход
  оставляет вторичным действием.
- Страница входа и первый пустой экран кабинета теперь ведут пользователя к
  скачиванию приложения перед подключением календарей.
- Feature `089-upload-transport-boundary`: upload part-number calculation в
  macOS upload client перенесен в единый lower-level `uploadPart`; endpoint,
  idempotency, missing-range retry и finalize semantics не менялись.
- Feature `088-upload-queue-boundary`: общий helper сохраняет persisted
  queue/server/support state при desktop upload re-scan/re-enqueue; поведение
  очереди и upload custody contracts не менялись.
- Feature `078-dead-code-batch-5`: удалены три доказанно неиспользуемых Swift
  `Foundation` import из shared macOS buffering/routing surface; batch
  уменьшает tracked Swift-код на 6 строк без новых зависимостей и без
  deploy-изменений.
- Feature `079-cabinet-calendar-route-helpers`: calendar cabinet route handlers
  отделены от redirect/result/audit helper-логики move-only split; поведение
  calendar settings не менялось, новых зависимостей нет.
- Feature `080-readiness-evidence-split`: readiness evidence matrix вынесен из
  `readiness/matrix.py` в отдельный module без изменения публичного
  `build_default_evidence` import-контракта.
- Feature `081-cabinet-auth-route-helpers`: browser email-login flow helpers
  вынесены из cabinet `auth.py` в отдельный module; route order и
  auth/session/device semantics не менялись.
- Feature `082-cabinet-auth-rendering-split`: auth/login/signup page rendering
  вынесен из общего cabinet `rendering.py` в `auth_rendering.py`; templates,
  route order и egress behavior не менялись.
- Feature `083-cabinet-deletion-rendering-split`: deletion report/feedback
  rendering и общий shell/path/text helper вынесены из cabinet `rendering.py`;
  deletion service, route order и lifecycle copy не менялись.
- Feature `084-cabinet-review-policy-rendering-split`: access/share/artifact
  policy widgets meeting detail вынесены из cabinet `rendering.py` в отдельный
  renderer без изменения routes, templates, egress API или deletion copy.

### Исправлено
- _Пока нет записей._

### Безопасность
- _Пока нет записей._

### Документы
- Добавлен B2C brief публичного лендинга с self-serve путем
  `лендинг -> скачать приложение -> вход -> кабинет`.
- Feature `072-deep-architecture-audit`: обновлен read-only architecture audit
  под текущий `origin/master`; roadmap исправлен с повторного split
  `cabinet/web.py` на реальные текущие hotspots cabinet route/view/render/egress,
  readiness, macOS upload/app/diagnostics/models и capture scripts.

### Операции
- _Пока нет записей._

## [2026.07.01.9] - 2026-07-01


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- _Пока нет записей._

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- Production checkout hygiene: `infra/secrets` теперь игнорируется и как
  symlink, чтобы runtime-secret mount не оставлял untracked след в `git status`.

## [2026.07.01.8] - 2026-07-01


### Добавлено
- macOS: при первом запуске без нужных доступов GRAF показывает стартовый
  экран настройки macOS-разрешений для микрофона и системного звука с быстрым
  переходом в System Settings.

### Изменено
- _Пока нет записей._

### Исправлено
- _Пока нет записей._

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.07.01.7] - 2026-07-01


### Добавлено
- _Пока нет записей._

### Изменено
- Feature `077-dead-code-batch-4`: удалены восемь доказанно неиспользуемых
  Swift `Foundation` import из macOS audio/capture/shared model surface; batch
  уменьшает Swift-код на 11 строк без новых зависимостей и без deploy-изменений.

### Исправлено
- _Пока нет записей._

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.07.01.6] - 2026-07-01


### Добавлено
- _Пока нет записей._

### Изменено
- Feature `076-dead-code-batch-3`: удалены три доказанно неиспользуемых Swift
  import из macOS capture/audio UI surface; batch уменьшает Swift-код на 4
  строки без новых зависимостей и без deploy-изменений.

### Исправлено
- Feature `069-universal-sidebar`: общий sidebar shell теперь явно помечает
  contained-scroll контракт, удерживает правую панель внутри viewport, оставляет
  admin mobile на page-scroll и не рендерит disabled sidebar/auth placeholders
  как `href="#"`.

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.07.01.5] - 2026-07-01


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- Production startup больше не падает, если optional URL-настройка передана
  пустой строкой при выключенной связанной функции; такие значения снова
  трактуются как не заданные.

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.07.01.4] - 2026-07-01


### Добавлено
- _Пока нет записей._

### Изменено
- Feature `075-dead-code-batch-2`: удалены два доказанно неиспользуемых Swift
  helper из macOS runtime/test surface; batch уменьшает Swift-код на 20 строк
  без новых зависимостей и без deploy-изменений.

### Исправлено
- Подключение календарей больше не зависит от calendar-only имени
  `TWOBRAIN_CALENDAR_CREDENTIAL_KEY_FILE`: GRAF использует общий
  `GRAF_CREDENTIAL_ENCRYPTION_KEY_FILE` для server-owned provider credentials и
  монтирует Docker secret `graf_credential_encryption_key` в `rec-api`.

### Безопасность
- Старое имя `TWOBRAIN_CALENDAR_CREDENTIAL_KEY_FILE` оставлено как
  совместимый alias, но canonical имя теперь описывает реальную границу:
  устойчивый envelope-encryption key для внешних credentials GRAF, а не пароль
  пользователя и не провайдерский secret.

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.07.01.3] - 2026-07-01


### Добавлено
- _Пока нет записей._

### Изменено
- Feature `074-code-optimization`: удалены три доказанно неиспользуемых
  private helper из server runtime; первый cleanup batch уменьшает Python
  runtime на 23 строки без новых зависимостей и без deploy-изменений.

### Исправлено
- macOS: активный индикатор записи в верхней части окна теперь закреплен через
  native titlebar accessory и не обрезается в неполноэкранном окне; правая
  панель управления прокручивается и не режет кнопки записи.

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.07.01.2] - 2026-07-01


### Добавлено
- _Пока нет записей._

### Изменено
- Feature `073-cabinet-web-split`: серверный cabinet router разрезан на
  небольшие route-family modules без изменения публичного `cabinet.web.router`
  контракта и без deploy-изменений.

### Исправлено
- Feature `069-universal-sidebar`: web-кабинет теперь держит общий sidebar и
  правую detail-панель в том же viewport shell, что и desktop embedded
  кабинет; прокручивается только область содержимого страницы.

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.07.01.1] - 2026-07-01


### Добавлено
- _Пока нет записей._

### Изменено
- Feature `063-calendar-settings-ui`: экран календарных интеграций в кабинете
  упрощен до продуктового пути: короткие кнопки “Подключить календарь” по
  провайдерам, ввод реквизитов в отдельном окне, выбор календарей внутри
  источника и свернутые privacy/sync-подсказки.

### Исправлено
- _Пока нет записей._

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.06.30.10] - 2026-06-30


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- macOS: в неполноэкранном окне embedded-кабинет больше не сворачивает левое
  меню в rail при обычной рабочей ширине; compact rail остается только для
  совсем тесной WebView, а активная запись не раскрывает правый inspector сама.

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.06.30.9] - 2026-06-30


### Добавлено
- _Пока нет записей._

### Изменено
- Feature `071-ponytail-refactor`: серверный Ponytail cleanup удаляет только
  доказанно неиспользуемые внутренние параметры, лишние вызовы и локальные
  избыточные выражения без изменения поведения; проверка зависимостей
  подтверждает, что `structlog`, `httpx2`, `httpcore2` и `truststore` не
  используются активным серверным кодом.

### Исправлено
- _Пока нет записей._

### Безопасность
- _Пока нет записей._

### Документы
- Feature `071-ponytail-refactor`: добавлены Spec Kit audit artifacts,
  evidence по зависимостям, retained-candidate notes и validation evidence для
  Ponytail cleanup batches.

### Операции
- Feature `071-ponytail-refactor`: release-branch проверка прошла без deploy:
  точечные серверные regression tests `104 passed`, `infra/scripts/ci-local.sh`
  `989 passed, 4 skipped` с `deployment_evidence_scan=pass` и
  `ci_local_result=pass`, полный macOS `swift test` `708 tests, 0 failures`,
  Ruff/Vulture/lock/diff checks прошли.

## [2026.06.30.8] - 2026-06-30


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- Support incident reports: backend теперь читает GitHub labels постранично, поэтому
  production repo с большим количеством labels не блокирует отправку отчета
  ошибкой `support_incident.configuration_invalid`.

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.06.30.7] - 2026-06-30


### Добавлено
- _Пока нет записей._

### Изменено
- Feature `069-universal-sidebar`: внутренние web-шаблоны кабинета и админки
  используют общий Jinja/HTML helper; поведение единой боковой панели и
  cache-busted CSS/JavaScript кабинета сохранены.

### Исправлено
- _Пока нет записей._

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- Closeout cleanup для Feature `069-universal-sidebar` прошел полный
  `infra/scripts/ci-local.sh`: `988 passed, 4 skipped`,
  `ci_local_result=pass`; локальная RLS-проверка ожидаемо осталась заблокирована
  без тестовой Postgres DB.

## [2026.06.30.6] - 2026-06-30


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- Cabinet login/web shell: CSS и JavaScript кабинета теперь подключаются с
  content-hash версией, чтобы веб и desktop WebView сразу получали свежий вид и
  поведение после production deploy.

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.06.30.5] - 2026-06-30


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- macOS: верхняя фиолетовая строка локальной записи больше не смещает таймер
  в свернутом окне; в этой же строке доступны понятные кнопки
  `Пауза`/`Продолжить` и `Стоп`.

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.06.30.3] - 2026-06-30


### Добавлено
- _Пока нет записей._

### Изменено
- Feature `070-cabinet-login-polish`: login, sign-up and email code
  confirmation pages now use a narrower shared auth panel so provider tiles
  no longer stretch across oversized desktop/app windows.

### Исправлено
- Feature `070-cabinet-login-polish`: embedded macOS cabinet login now keeps
  the web-auth path inside the app for HTTPS provider authorization legs and
  safe provider callbacks during active auth continuation, while external
  navigation outside login remains blocked.
- Feature `070-cabinet-login-polish`: six-digit email codes now auto-submit
  once after typing or pasting the full code.

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- Feature `070-cabinet-login-polish`: local validation passed focused macOS
  auth route/workspace checks, focused server auth asset checks, and full
  `infra/scripts/ci-local.sh` with `992 passed, 4 skipped` and
  `ci_local_result=pass`; the local RLS probe remained blocked without a test
  Postgres database as expected.

## [2026.06.30.2] - 2026-06-30


### Добавлено
- _Пока нет записей._

### Изменено
- Feature `063-calendar-settings-ui`: экран календарных настроек упрощен под
  короткий рабочий путь подключения, переиспользует общий cabinet shell/sidebar
  и показывает счетчики источников/календарей с корректными русскими формами.

### Исправлено
- _Пока нет записей._

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.06.30.1] - 2026-06-30


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- Feature `061-support-incident-reporting`: production `rec-api` теперь получает
  GitHub token как Docker secret file, поэтому действие `Отправить отчет`
  может создавать private support issue и возвращать пользователю `CUST-*`.

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- Добавлены regression checks, которые не дают снова выкатить support incident
  endpoint без GitHub token secret wiring в production compose/env contract.

## [2026.06.28.8] - 2026-06-28


### Добавлено
- _Пока нет записей._

### Изменено
- Feature `069-universal-sidebar`: пользовательский cabinet теперь собирает
  левую навигацию через один server-owned shell/sidebar contract для web и
  desktop embedded поверхностей; страницы владеют только content region, а
  fragments остаются content-only и не дублируют sidebar.

### Исправлено
- _Пока нет записей._

### Безопасность
- _Пока нет записей._

### Документы
- Feature `069-universal-sidebar`: добавлены Spec Kit артефакты, quickstart,
  shell contract и GitHub issue sync для архитектурного среза единой sidebar.

### Операции
- _Пока нет записей._

## [2026.06.28.7] - 2026-06-28


### Добавлено
- Feature `067-dual-audio-formats`: macOS recording package now writes a local
  `meeting-review.m4a` playback derivative from the capture-rate writer queue
  while preserving `mic.wav` and `incoming.wav` for transcription; desktop
  upload now sends the optional playback artifact, and cabinet playback,
  shared review access, and audio download prefer the stored M4A with WAV-mix
  fallback.

### Изменено
- Feature `068-dependency-refresh`: backend runtime and validation toolchain
  dependencies refreshed to latest stable versions resolved by `uv`; production
  `constraints.txt` now comes from the lockfile so Docker installs the validated
  runtime package set.

### Исправлено
- Feature `068-dependency-refresh`: server tests no longer emit Python 3.14
  deprecation warnings from old async test tooling or deprecated per-request
  cookie usage.

### Безопасность
- _Пока нет записей._

### Документы
- Feature `067-dual-audio-formats`: добавлены недостающие Spec Kit артефакты
  для high-risk audio/storage slice: plan, data model, contracts, quickstart,
  checklists, tasks и analyze evidence.
- Feature `068-dependency-refresh`: release/validation guidance now requires
  latest stable dependencies by default and keeps `pyproject.toml`, `uv.lock`,
  and production constraints in sync.

### Операции
- Feature `068-dependency-refresh`: local CI passed on the refreshed dependency
  set with `983 passed, 4 skipped`, Ruff pass, compile pass, production compose
  config pass, deployment evidence scan pass, and expected local RLS boundary
  `postgres_test_database_required`.

## [2026.06.28.6] - 2026-06-28


### Добавлено
- Feature `063-calendar-settings-ui`: добавлен рабочий экран
  `Настройки -> Интеграции -> Календари` для web cabinet и embedded macOS
  cabinet. Экран показывает read-only границу, поддерживаемых провайдеров,
  подключенные источники, выбор календарей внутри источника, sync health,
  manual sync, disconnect confirmation, preview ближайших встреч, настройки
  prompt-поведения и явное решение для пересекающихся событий.

### Изменено
- Calendar settings теперь сохраняют пользовательские prompt/preference
  настройки отдельно от backend calendar context: календарь после подключения
  не становится активным автоматически, пока пользователь явно не выберет
  конкретные календари.
- Feature `063-calendar-settings-ui`: неподдерживаемые записи убраны из
  пользовательского provider catalog; экран показывает только app-password,
  CalDAV и provider-limited варианты.

### Исправлено
- Feature `063-calendar-settings-ui`: embedded macOS cabinet теперь пропускает
  только известные child routes настроек календаря и переустанавливает desktop
  headers для GET-навигации настроек.
- Feature `063-calendar-settings-ui`: upcoming/preview события теперь
  фильтруются по пользовательским категориям до применения лимита; события с
  участниками, но без ссылки, входят в дефолт как meeting-like.
- Feature `063-calendar-settings-ui`: provider-result больше не показывает
  ложный success без созданного источника, app-password flow сохраняет логин в
  server-owned sealed payload, а preview уважает настройки скрытия времени и
  названия.

### Безопасность
- Feature `063-calendar-settings-ui`: UI и measurement contract закрепляют, что
  календарный доступ остается read-only; desktop app не хранит provider
  credentials; private/free-busy события показывают только безопасный минимум;
  участники календаря не становятся получателями саммари или share grants; 063
  не включает auto-record, bot join, calendar mutation, отправку сообщений или
  retrospective matching.

### Документы
- Обновлены Spec Kit evidence для `063-calendar-settings-ui`: quickstart,
  measurement, design QA и текущий статус продукта фиксируют проверенный scope,
  ограничения и validation evidence.

### Операции
- Local validation для `063-calendar-settings-ui` на 2026-06-28: focused server
  calendar settings checks passed `77 passed`; server Ruff passed; focused
  macOS calendar/cabinet checks passed `97 tests`; full macOS suite passed
  `693 tests`; forbidden-content scan found only safe `contains_passcode`
  source-code detector references; removed-provider catalog scan found no
  matches in the calendar feature surface; full local CI passed `968 passed, 4
  skipped, 148 warnings` with `ci_local_result=pass`.
  Release and production deploy evidence is recorded in the GitHub Release
  notes for `v2026.06.28.6`.

## [2026.06.28.5] - 2026-06-28


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- В web cabinet sidebar оставлен только логотип `ГРАФ`: убраны отдельная
  пиктограмма и подпись `Бесплатный план` из верхнего бренд-блока.

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.06.28.4] - 2026-06-28


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- В browser admin UI убран лишний правый logo lockup: основной логотип теперь
  находится слева в sidebar.

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.06.28.3] - 2026-06-28


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- Локальная custody-защита файлов macOS использует устойчивый для macOS режим
  `completeUntilFirstUserAuthentication` с правами `0600`, чтобы защищенные
  временные пакеты оставались читаемыми для владельца после записи.
- Старый `graf-logo.svg` заменен на выбранный `ГРАФ`-брендинг: web/sidebar и
  admin используют wordmark, а favicon, apple-touch icon и macOS app icon
  пересобраны из компактной `Ф`-пиктограммы с микрофоном.

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.06.28.2] - 2026-06-28


### Добавлено
- _Пока нет записей._

### Изменено
- Техническая идентичность macOS-приложения переведена на `GRAF`: app bundle
  `GRAF.app`, bundle id `pro.2brain.graf`, HAL-драйвер `GrafProof.driver`,
  виртуальные устройства `GRAF Microphone`/`GRAF Speaker` и новые runtime
  paths/logs/shared-memory names.
- В web/auth и macOS sidebar добавлен выбранный кириллический wordmark
  `ГРАФ` из `i-1-cyrillic-mic.png`; подготовлены светлая и темная PNG-версии
  нужного размера.

### Исправлено
- _Пока нет записей._

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.06.28.1] - 2026-06-28


### Добавлено
- Набор вариантов кириллического `ГРАФ` logo lockup с микрофоном для темной
  темы browser admin UI.

### Изменено
- Шапка browser admin UI теперь использует выбранный инвертированный PNG
  `ГРАФ` вместо текстового wordmark.

### Исправлено
- _Пока нет записей._

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.06.27.17] - 2026-06-27


### Добавлено
- _Пока нет записей._

### Изменено
- Email-вход, admin shell и macOS предупреждения доочищены под бренд `GRAF`;
  favicon/app icon остаются пиктограммой, а письмо использует текстовый
  wordmark без внешних изображений.

### Исправлено
- _Пока нет записей._

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.06.27.16] - 2026-06-27


### Добавлено
- _Пока нет записей._

### Изменено
- В шапке browser admin UI теперь показывается wordmark `GRAF` с надписью,
  без переиспользования обычной app-icon из кабинета.

### Исправлено
- _Пока нет записей._

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.06.27.15] - 2026-06-27


### Добавлено
- _Пока нет записей._

### Изменено
- Browser admin UI теперь использует основной `2brain Rec` cabinet shell,
  темную тему, sidebar-навигацию и плотность элементов приложения.

### Исправлено
- _Пока нет записей._

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.06.27.14] - 2026-06-27


### Добавлено
- _Пока нет записей._

### Изменено
- Видимый бренд macOS-приложения, web-кабинета, писем входа, favicon/app
  icon и installer copy обновлен на `GRAF`; технические пути, bundle id и
  virtual audio device names оставлены совместимыми.

### Исправлено
- _Пока нет записей._

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.06.27.13] - 2026-06-27


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- Browser `/admin` без активной сессии теперь ведет на `/login?next=/admin`,
  а не показывает JSON-ошибку авторизации.

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.06.27.12] - 2026-06-27


### Добавлено
- Feature `064-workspace-admin-panel`: добавлена browser-owned workspace
  admin-панель без support/Analyst/billing ролей: обзор, пользователи и
  приглашения, файлы/встречи, read-only баланс/usage/quotas, продуктовые
  метрики и metadata-only audit journal.
- Feature `064-workspace-admin-panel`: добавлены admin API routes под
  `/api/v1/admin` и отдельный server-rendered `/admin` shell, не завязанный на
  `cabinet/web.py`.

### Изменено
- Desktop cabinet route policy открывает `/admin` во внешнем браузере и не
  встраивает админку в native recorder shell.

### Исправлено
- Feature `064-workspace-admin-panel`: исправлены admin deletion source/audit
  path, invite completion RLS для audit event, truthful file unavailable states,
  file type filtering и role/reason controls в browser admin UI.

### Безопасность
- Feature `064-workspace-admin-panel`: добавлены RLS-покрытые таблицы
  `workspace_invitations`, `workspace_quota_policies`,
  `workspace_usage_daily`, `user_usage_daily`, `admin_audit_events`; Owner/Admin
  доступ проверяется поверх активного workspace membership.
- Feature `064-workspace-admin-panel`: sensitive admin actions пишут
  metadata-only audit evidence; API/HTML тесты запрещают storage keys, signed
  URLs, transcript/raw audio/private content и secret markers.
- Feature `064-workspace-admin-panel`: last active Owner нельзя downgrade,
  block, revoke, deactivate или убрать; Admin может управлять только Members.

### Документы
- _Пока нет записей._

### Операции
- Feature `064-workspace-admin-panel`: добавлены focused unit/contract/
  integration проверки для admin permissions, invitations, RLS inventory,
  browser UX, workspace access, file governance, usage/quota, metrics/audit и
  desktop handoff policy.

## [2026.06.27.11] - 2026-06-27


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- Страница авторизации сохраняет двухколоночный список способов входа в узком
  окне браузера, чтобы соответствовать выбранному макету.

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.06.27.10] - 2026-06-27


### Добавлено
- _Пока нет записей._

### Изменено
- Web-cabinet обновил страницу авторизации: способы входа показываются в
  компактной двухколоночной сетке, будущие провайдеры отображаются неактивными,
  а Telegram скрыт с экрана до готовности.

### Исправлено
- _Пока нет записей._

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.06.27.9] - 2026-06-27


### Добавлено
- Feature `066-vk-id-web-login`: web-cabinet показывает активный вход через
  VK ID и ведет `/login/vk/start` в существующий provider flow.
- Feature `066-vk-id-web-login`: web-cabinet добавляет вход через Mail.ru и
  Одноклассники как VK ID provider hints, без отдельных backend OAuth
  провайдеров.

### Изменено
- _Пока нет записей._

### Исправлено
- _Пока нет записей._

### Безопасность
- Feature `066-vk-id-web-login`: VK callback обновлен на OAuth VK ID 2.1 с
  PKCE, `device_id` и серверной проверкой `state` при обмене кода.

### Документы
- _Пока нет записей._

### Операции
- Feature `066-vk-id-web-login`: production compose прокидывает
  `TWOBRAIN_VK_CLIENT_ID` и монтирует `twobrain_vk_client_secret` только в
  `rec-api`.

## [2026.06.27.8] - 2026-06-27


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- Production compose монтирует Yandex OAuth secret file с uid/gid runtime
  пользователя `rec-api`, чтобы контейнер мог прочитать секрет при smoke.

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.06.27.7] - 2026-06-27


### Добавлено
- Feature `065-yandex-id-web-login`: web-cabinet теперь показывает активный
  вход через Яндекс ID и ведет `/login/yandex/start` в реальный provider flow,
  а не в заглушку `скоро`.

### Изменено
- _Пока нет записей._

### Исправлено
- _Пока нет записей._

### Безопасность
- Feature `065-yandex-id-web-login`: callback `redirect_uri` для провайдеров
  использует публичный `TWOBRAIN_AUTH_BASE_URL`, когда он настроен, чтобы
  self-hosted reverse proxy не подставлял внутренний host в OAuth-flow.
- Feature `065-yandex-id-web-login`: production compose передает Yandex
  `client_secret` только через Docker secret file и падает на пустом
  provider-secret файле.

### Документы
- _Пока нет записей._

### Операции
- Feature `065-yandex-id-web-login`: production compose прокидывает
  `TWOBRAIN_YANDEX_CLIENT_ID` и монтирует
  `twobrain_yandex_client_secret` только в `rec-api`.

## [2026.06.27.6] - 2026-06-27


### Добавлено
- Web-cabinet получил точку входа в настройки календарей: из блока
  "Ближайшие" можно перейти в секцию подключения календарей.

### Изменено
- Web-cabinet унифицировал compact action controls: toolbar/list actions
  используют 32px hit target и lucide-style 16px icons.

### Исправлено
- Web-cabinet больше не показывает захардкоженные будущие встречи; до
  подключения календаря отображается честное empty state.

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.06.27.5] - 2026-06-27


### Добавлено
- Feature `061-support-incident-reporting`: в native custody UI добавлено
  действие `Отправить отчет` для локальных записей, которые больше не могут
  отправиться автоматически; успешная отправка показывает пользователю номер
  вида `CUST-*`, а `Скопировать отчет` остается fallback-действием.
- Feature `061-support-incident-reporting`: backend принимает desktop
  metadata-only support incidents, сохраняет redacted incident и создает или
  обновляет deduped private GitHub issue через серверный токен.

### Изменено
- _Пока нет записей._

### Исправлено
- Embedded web-cabinet держит левый sidebar неподвижным, а вертикальную
  прокрутку списка/detail переносит в правую рабочую область.
- Embedded web-cabinet в оконном режиме больше не сжимает рабочую область до
  скрытой колонки sidebar на узком breakpoint.
- Embedded web-cabinet на узком окне показывает compact rail левого меню с
  lucide-иконками и доступной кнопкой раскрытия, вместо бесследного скрытия
  навигации.

### Безопасность
- Feature `061-support-incident-reporting`: support incident payload и GitHub
  issue body проходят server-side redaction validation; аудио, transcript text,
  raw local paths, tokens, signed URLs и private meeting content запрещены в
  payload, storage, logs и evidence.

### Документы
- _Пока нет записей._

### Операции
- Feature `061-support-incident-reporting`: одинаковые пользовательские
  custody-проблемы агрегируются через dedupe key, `affected_count` и bounded
  safe affected identities, чтобы support/agent разбирал один incident вместо
  пачки дублей.

## [2026.06.27.4] - 2026-06-27


### Добавлено
- _Пока нет записей._

### Изменено
- Feature `060-calendar-context-ingestion`: календарный ingest теперь сохраняет
  больше доступного provider context: описание, локацию, free/busy transparency,
  attachment metadata, source created/updated timestamps и recurrence identity.

### Исправлено
- Feature `060-calendar-context-ingestion`: запись, запущенная из календарного
  prompt, теперь передает calendar event id в upload queue, поэтому сервер
  может связать запись с событием календаря.
- Feature `060-calendar-context-ingestion`: CalDAV/iCalendar recurrence
  instances теперь различаются по `RECURRENCE-ID`/`original_start`, чтобы
  разные встречи одной серии не перетирали друг друга.

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- Зафиксирован post-deploy closeout для `060-calendar-context-ingestion`:
  release `v2026.06.27.2`, GitHub Release, production deploy
  `deploy_result=pass`, production smoke `smoke_result=pass`, readiness
  `infra_smoke_ready`, и local macOS installer build версии `2026.06.27.2`.

## [2026.06.27.3] - 2026-06-27


### Добавлено
- _Пока нет записей._

### Изменено
- Feature `059-recording-date-title`: recording display timezone теперь
  проходит из macOS metadata через create-meeting и хранится на сервере, чтобы
  дата записи в кабинете совпадала с локальным днем записи, а не съезжала на
  UTC-границах.

### Исправлено
- Feature `059-recording-date-title`: сортировка "По названию" теперь идет по
  видимому безопасному названию, включая legacy-записи без title.
- Idempotent create-meeting retry для legacy-записи с уже сохраненным unsafe
  title снова возвращает существующую встречу, а не ломает повторную отправку.
- Повторный create-meeting для того же `local_recording_id` теперь отклоняет
  попытку незаметно поменять дату записи, конец записи или timezone offset.

### Безопасность
- Unsafe fallback values вроде URL/email/token-like `local_recording_id` больше
  не показываются как название встречи; кабинет использует безопасный
  `Untitled meeting`.

### Документы
- _Пока нет записей._

### Операции
- Post-merge fixes 059 подняты поверх `v2026.06.27.2`, а миграция timezone
  стала `0011_recording_display_timezone` после календарной миграции `0010`,
  чтобы production upgrade шел одной линейной Alembic-цепочкой.

## [2026.06.27.2] - 2026-06-27

### Добавлено
- Feature `060-calendar-context-ingestion`: добавлен первый слой календарного
  контекста. Сервер хранит read-only подключения календарей, выбранные
  календари, будущие события, участников, conference-link metadata,
  recording-time context links и safe recipient-candidate counts; macOS
  получает one-minute join prompt и event-start record prompt без
  auto-record/auto-join.

### Изменено
- Названия новых записей теперь могут получать `calendar` title source только
  при явной recording-time связи с текущим/выбранным событием; пользовательское
  название остается главным, а прошлые события не подтягиваются задним числом.

### Исправлено
- Desktop WebView больше не блокирует переход "Мои встречи" из web-sidebar:
  embedded cabinet navigation теперь ведет на `/desktop/meetings`, а не на
  browser route `/meetings`.
- Левый web-sidebar кабинета закреплен на высоту окна и больше не получает
  собственный скроллбар при прокрутке списка встреч.

### Безопасность
- Календарные credentials остаются server-owned и sealed; committed fixtures,
  logs и evidence не содержат raw provider payloads, refresh tokens, app
  passwords, attendee email dumps, passcodes, signed links или private event
  text. Calendar attendees не создают share/access grants и не становятся
  получателями сообщений в 060.
- В production credential-bearing calendar connect требует устойчивый Fernet key
  через `TWOBRAIN_CALENDAR_CREDENTIAL_KEY_FILE`; без него API fail-closed до
  принятия app passwords/OAuth-refresh-like материала.

### Документы
- Зафиксированы provider deep dive, quickstart, metadata-only evidence,
  supported provider families, known limitations и явная граница: отправка
  summary/transcript/report будет отдельным слоем после 060.

### Операции
- Local validation для 060 на 2026-06-27: focused backend
  calendar/cabinet/ingest checks passed `134 passed`; macOS prompt/upload/
  recording-metadata checks passed `155 tests`; full macOS suite passed
  `666 tests, 0 failures`; forbidden-content scan returned no matches; after
  refreshing from `origin/master` `94ffcb6`, final `infra/scripts/ci-local.sh`
  passed with server `782 passed, 4 skipped, 103 warnings`, Ruff, compile,
  production compose config, deployment evidence scan, and
  `ci_local_result=pass`. PR #2286 и closeout PR #2287 смержены в `master`;
  production deploy/smoke и desktop installer/app build остаются release
  execution gates, а не implementation evidence 060.

## [2026.06.27.1] - 2026-06-27


### Добавлено
- Feature `058-web-cabinet-htmx-shell`: добавлен серверный Jinja shell для
  web/desktop кабинета, reusable cabinet component catalog, локальный
  `htmx-2.0.10`, bounded HTMX fragments для списка/detail/delete feedback,
  deletion-report и metadata-safe runtime checker.
- Feature `059-recording-date-title`: новые записи получают дату фактической
  записи из local manifest и минимальное безопасное название из уже
  разрешенного app/platform context или generic date fallback.

### Изменено
- Список и detail кабинета теперь рендерятся через общий server-owned shell,
  чтобы будущие online-страницы не дублировали продуктовое меню в macOS shell.
- Desktop WebView получает online cabinet navigation, а native Record/Stop,
  active capture, upload truth, permission recovery и local diagnostics
  остаются native-only.
- Create-meeting payload теперь передает persisted `title`, `started_at` и
  `ended_at`, а список кабинета может сортировать записи по времени записи,
  а не по времени загрузки или обновления.

### Исправлено
- Deletion-report web routes теперь возвращают bounded HTMX fragment при
  `HX-Request`, а не полный shell.
- MacOS WebView boundary tests теперь закрепляют текущую online/local границу:
  online cabinet rows остаются web-owned, а local/offline custody rows остаются
  native-only.

### Безопасность
- Unsafe cookie-authenticated cabinet actions защищены CSRF proof, HTMX-запросы
  передают `X-CSRF-Token`, а template tests закрепляют autoescape/trusted HTML
  guard и отсутствие private evidence markers.
- CSRF contract отдельно закрепляет все unsafe cabinet API routes, чтобы новые
  POST/PATCH/DELETE действия не обходили web-session защиту.
- Private cabinet shell теперь просит поисковые роботы не индексировать кабинет
  и отключает HTMX eval/script-tag handling для authenticated surface.
- Feature `059` не собирает календарь, window/browser title, transcript-derived
  title или raw contextual candidates; diagnostics остаются metadata-only, а
  unsafe title-like values подавляются локально и отклоняются server ingest.
- Request validation errors теперь возвращают metadata-only problem response и
  не эхоят raw invalid input вроде control-character title.

### Документы
- Зафиксированы architecture/component/HTMX/WebView boundary decisions,
  rollback rules и validation evidence для feature `058`.
- Зафиксированы scope/evidence для feature `059`: календарная интеграция
  перенесена в `060`, window-title collection оставлен отдельной будущей
  privacy-sensitive slice.

### Операции
- Feature `059` прошел локальный gate `infra/scripts/ci-local.sh` с
  `ci_local_result=pass`, а полный macOS SwiftPM suite прошел
  `653 tests, 0 failures`; production RLS/deploy truth остается отдельным
  release/deploy evidence.

## [2026.06.26.12] - 2026-06-26


### Добавлено
- Feature `057-local-upload-custody`: desktop upload queue now behaves as
  product custody, not as a user task list. Local recordings remain accounted
  for, retry automatically when safe, and expose calm aggregate native custody
  status outside the server-owned WebView meeting list.
- Structured custody read-model fields for feature `058`: server-known
  recordings expose machine-readable custody, upload, processing, owner,
  retry-class, action, copy-key, review availability, and metadata-safety truth.

### Изменено
- Normal users no longer get transport-level Retry or Stop retry controls for
  local recording upload. The UI shows only meaningful actions such as sign-in,
  safe report, diagnostics, review when available, or explicit local deletion.
- Local upload, server processing, server deletion, and local purge truth are
  separated so an uploaded recording with failed processing is not shown as a
  failed local upload.

### Исправлено
- _Пока нет записей._

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.06.26.11] - 2026-06-26


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- Чекбоксы выбора записей больше не рисуют галочку и частичный выбор вручную:
  верхний контрол и строки используют нативный checkbox с единым системным
  стилем.

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.06.26.10] - 2026-06-26


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- Верхний элемент выбора записей теперь использует тот же checkbox-контрол,
  что и строки списка, поэтому его размер и позиция совпадают с чекбоксами.

### Безопасность
- _Пока нет записей._

### Документы
- Уточнен рабочий процесс Spec Kit: каждая правка выбирает risk/validation
  lane, маленькие low-risk изменения проходят scoped-проверки, а high-risk и
  релизные изменения сохраняют полный набор gate.

### Операции
- PR template теперь требует указать risk/validation lane, выполненные проверки
  и почему более широкие gate не запускались.

## [2026.06.26.9] - 2026-06-26


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- Кнопка выбора записей в верхней панели теперь такого же размера, как
  чекбоксы строк, и выровнена с ними по левому краю.

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.06.26.8] - 2026-06-26


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- Кнопка раскрытия/сворачивания правой панели desktop shell снова закреплена
  в одном правом верхнем слоте и использует двойной шеврон.
- Узкая верстка списка записей больше не схлопывает название, дату и кнопку
  удаления в одну колонку.
- Верхняя кнопка выбора записей больше не наследует общий размер обычных
  кнопок и остаётся компактным квадратом в панели выбора.
- Иконка типа записи в списке теперь различает `аудио`, `видео`,
  `транскрипт` и `upload` на базе консистентных Lucide SVG.

### Безопасность
- Local custody ledger/artifacts are written with stronger local file
  protection where this slice touches them, malformed queue documents are
  quarantined metadata-safely, and safe incident reports exclude audio,
  transcript text, private paths, tokens, and signed URLs.
- Local purge acknowledgements now fail closed: desktop sends successful
  acknowledgement only after verified local deletion, tombstone, or
  cryptographic unrecoverability; unverified purge is reported as a safe
  failure.

### Документы
- Added feature `057` specification, contracts, quickstart, validation notes,
  and explicit `057`/`058` boundary guidance.

### Операции
- _Пока нет записей._

## [2026.06.26.7] - 2026-06-26


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- Верхний элемент выбора в списке записей теперь работает как toggle: при
  частичном выборе выбирает все видимые записи, а при полном выборе снимает
  выделение и прячет панель выбора.

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.06.26.6] - 2026-06-26


### Добавлено
- _Пока нет записей._

### Изменено
- Успешные ingest write routes теперь фиксируют изменения одной транзакцией на
  границе API, вместо промежуточных commit внутри helper-функций.

### Исправлено
- Неверный email login code теперь сжигает callback state, поэтому одноразовый
  код нельзя переиспользовать после failed attempt.
- Deletion request теперь реально удаляет server-owned audio objects,
  temporary upload objects и stored outcome content, а отчёт показывает
  `purged` для очищенных controlled artifacts.
- Upload create/part/finalize больше не полагаются на устаревший in-memory
  snapshot, когда БД уже пометила meeting deleting или session terminal.
- Finalize принимает contiguous multipart tracks, собирает их в финальный
  track artifact и проверяет aggregate checksum/length.
- Processing submit блокирует слишком крупную пару аудиодорожек до чтения
  object bytes в память.

### Безопасность
- В production отключен legacy header-only auth без session token; session-bound
  device headers продолжают проходить через проверку trusted binding.

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.06.26.5] - 2026-06-26


### Добавлено
- _Пока нет записей._

### Изменено
- Встречи в desktop-кабинете стали шире и читабельнее: список записей
  использует больше экрана, строки больше не выглядят слишком мелкими, а правая
  панель управления очищена от декоративных переключателей и держит кнопку
  сворачивания на одном месте. См. feature `054`.

### Исправлено
- Панель выбора записей в кабинете выровнена как в референсе: иконки
  скачивания и удаления стали понятными SVG, скачивание осталось заблокированным
  и показывает tooltip вместо запуска действия.

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.06.26.4] - 2026-06-26


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- В списке записей кабинета снова можно выбирать одну или несколько записей
  и удалять их после русского подтверждения. Кнопка скачивания в режиме выбора
  пока отключена и честно сообщает, что появится позже.

### Безопасность
- _Пока нет записей._

### Документы
- Зафиксирован условный лимит MediaScribe для очень больших аудио-запросов:
  это не блокирует 1 GiB upload contract на Rec, потому что MediaScribe получает
  только аудиодорожки, а не весь пакет или видеофайл.
- Обновлен статус `052`: свежая запись из установленного приложения дошла до
  upload, finalize и processing, но не дала транскрипт, диаризацию и итоги.
  Поэтому две P1-задачи 052 остаются открытыми.

### Операции
- _Пока нет записей._

## [2026.06.26.3] - 2026-06-26


### Добавлено
- _Пока нет записей._

### Изменено
- Контракт загрузки одной части аудиодорожки увеличен до 1 GiB на сервере и
  в macOS-клиенте. Это позволяет обычным длинным WAV-записям уходить одним
  файлом на дорожку без дробления на мелкие части.

### Исправлено
- macOS-клиент больше не дробит обычные записи на части по 5 MB, из-за чего
  сервер мог вернуть `ambiguous_track_parts` при финализации.

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.06.26.2] - 2026-06-26


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- Экран входа в кабинет теперь остается видимым внутри macOS-приложения после
  перехода на login-route. Это закрывает случай, когда приложение видело
  истекшую сессию и снова показывало заглушку вместо формы входа.

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.06.26.1] - 2026-06-26


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- Вход в кабинет из macOS-приложения теперь открывается внутри приложения, а
  не во внешнем браузере. После входа сессия остается доступна приложению.

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.06.25.14] - 2026-06-25


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- Исправлен cleanup production smoke/timing записей: попытки генерации итогов
  удаляются до наборов итогов, поэтому уборка не останавливается на FK.

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.06.25.13] - 2026-06-25


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- Исправлен cleanup production smoke: временные итоги встречи удаляются до
  результата обработки, поэтому уборка тестовых записей не упирается в FK.

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.06.25.12] - 2026-06-25


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- Исправлено форматирование readiness-теста `052`, из-за которого lint
  останавливал production deploy gate после успешного набора серверных тестов.

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.06.25.11] - 2026-06-25


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- _Пока нет записей._

### Безопасность
- _Пока нет записей._

### Документы
- Для `052` добавлена production-safe проверка скорости: синтетическая
  часовая запись обработалась быстрее лимита 3 минуты на час аудио. MVP все
  еще `pilot_blocked`, пока не доказан свежий путь из установленного приложения
  и итоги на таком production-кандидате.

### Операции
- _Пока нет записей._

## [2026.06.25.10] - 2026-06-25


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- Исправлен production-запуск `rec-api`: API больше не требует и не монтирует
  секрет MediaScribe. API только запускает обработку в Temporal, а ключ
  MediaScribe остается у `rec-processing-worker`, где он реально используется.

### Безопасность
- Секрет MediaScribe убран из окружения и Docker secrets `rec-api`; его читает
  только processing worker.

### Документы
- _Пока нет записей._

### Операции
- Production health должен вернуться из `502`: readiness теперь честно
  показывает `mediascribe=dispatcher_only` для API без серверного ключа.

## [2026.06.25.9] - 2026-06-25


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- В `052` найден и исправлен production-блокер обработки: `rec-api` теперь
  получает настройки запуска задач в Temporal и доступ к секрету MediaScribe,
  чтобы после завершения загрузки запускать обработку, а не оставлять записи в
  `not_submitted`.

### Безопасность
- _Пока нет записей._

### Документы
- Завершена фича `052`: финальная доказательная проверка MVP-пути после `051`.
  Срез проверяет свежий путь от установленного приложения до production-кабинета,
  сохраненные итоги, нижнюю шкалу спикеров, веб- и desktop-интерфейс и скорость
  обработки на длинной записи, либо честно оставляет статус
  `pilot_blocked`.
- Зафиксирован текущий итог `052`: локальные web/mobile/embedded проверки
  подтверждают воспроизведение, переход по времени, нижнюю шкалу спикеров и
  строки итогов; macOS приложение честно показывает состояние `Нужен вход`.
  Просмотр встречи в production, production-итоги и замер скорости на длинной
  записи остаются открытыми P1-проверками, поэтому MVP все еще `pilot_blocked`.

### Операции
- _Пока нет записей._

## [2026.06.25.8] - 2026-06-25


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- _Пока нет записей._

### Безопасность
- _Пока нет записей._

### Документы
- Зафиксирован post-deploy closeout для `051`: PR, release, deployed SHA,
  production health и итоговый статус `pilot_blocked` записаны в evidence и
  текущий статус продукта.

### Операции
- Production deploy `051` прошел с `deploy_result=pass` и
  `readiness_verdict=infra_smoke_ready`.

## [2026.06.25.7] - 2026-06-25


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- _Пока нет записей._

### Безопасность
- _Пока нет записей._

### Документы
- Завершена подготовка `051`: проверен текущий путь к MVP-решению без
  завышения статуса. Установленное приложение, production health, локальный
  web/embedded playback, seek, нижняя шкала спикеров, stored outcomes runtime и
  macOS-защита от ложного зеленого статуса подтверждены. MVP остается
  `pilot_blocked`, пока не пройдут свежий owner journey, stored outcomes на
  текущем production-кандидате и timing на близкой к часу записи.

### Операции
- _Пока нет записей._

## [2026.06.25.6] - 2026-06-25


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- _Пока нет записей._

### Безопасность
- _Пока нет записей._

### Документы
- Зафиксирован post-deploy closeout для `050`: PR, release, deployed SHA,
  production health и итоговый статус `pilot_blocked` записаны в evidence и
  текущий статус продукта.

### Операции
- Production deploy `050` прошел с `deploy_result=pass` и
  `readiness_verdict=infra_smoke_ready`.

## [2026.06.25.5] - 2026-06-25


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- _Пока нет записей._

### Безопасность
- _Пока нет записей._

### Документы
- Завершена фича `050`: единая проверка MVP-пути, интерфейса приложения,
  веб-кабинета и текущей продуктовой правды перед заявлением о готовности.
- Зафиксирован результат фичи `050`: текущий продукт остается в статусе
  `pilot_blocked`. Прослушивание, таймкоды, нижняя шкала спикеров, совпадение
  веба и встроенного окна macOS, честный статус macOS-кабинета и документы
  готовности проверены. Еще не закрыты: живое доказательство пользовательского
  production-пути, свежий путь от записи до просмотра, сохраненные итоги на
  текущем production-кандидате и замер скорости на часовой записи.

### Операции
- _Пока нет записей._

## [2026.06.25.4] - 2026-06-25


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- В просмотре встречи активный таб `Запись и расшифровка` теперь показывает
  саму расшифровку, а не блок итогов. Нижняя шкала записи яснее показывает
  строки спикеров и интервалы, когда каждый говорил (`feature:049`).

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.06.25.3] - 2026-06-25


### Добавлено
- В продукт добавлены сохраненные итоги встречи для MVP. Веб-кабинет и
  встроенное окно macOS показывают краткое резюме, ключевые пункты, решения,
  действия, follow-up, риски, вопросы и ссылки на таймкоды только когда это
  подтверждается расшифровкой (`feature:049`).

### Изменено
- _Пока нет записей._

### Исправлено
- _Пока нет записей._

### Безопасность
- _Пока нет записей._

### Документы
- Уточнена текущая продуктовая правда после closeout `feature:048`: playback
  больше не описан как локальная незакрытая работа, а связан с опубликованным
  релизом и production smoke.
- Обновлена readiness-правда для `feature:049`: blocker
  `notes-action-output` закрывается stored outcomes, но production rollout
  остается отдельным gate до финального пользовательского доказательства.

### Операции
- _Пока нет записей._

## [2026.06.25.2] - 2026-06-25


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- В macOS-приложении статус кабинета теперь не считается успешным только
  потому, что задан адрес сервера. Пока сервер проверяется, приложение показывает
  проверку; если сервер недоступен, показывает недоступность; если нужен вход,
  показывает это отдельно (`feature:047`).

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.06.25.1] - 2026-06-25


### Добавлено
- Прослушивание результата теперь должно быть видно на обычной обработанной
  записи без ручного включения скачивания аудио. Пользователь слушает запись
  прямо в просмотре встречи, а скачивание и экспорт остаются отдельными
  настройками доступа (`feature:048`).
- Серверный маршрут прослушивания поддерживает частичную отдачу аудио, чтобы
  браузер мог быстро начинать воспроизведение и перематывать запись без прямых
  ссылок на хранилище (`feature:048`).

### Изменено
- Экран результата стал удобнее для проверки встречи: расшифровка остается
  главным содержимым, проигрыватель закреплен внизу, таймкоды ведут к нужному
  месту записи, а дорожки говорящих помогают быстро понять, где кто говорит
  (`feature:048`).

### Исправлено
- Исправляется разрыв после `046`: раньше проигрыватель был доказан на
  тестовой встрече с вручную включенной политикой аудио, но мог не появляться
  на реальных записях пользователя (`feature:048`).

### Безопасность
- Прослушивание остается через сервер: ответы не содержат подписанные ссылки,
  ключи файлов в хранилище, приватные пути, сырой текст встречи или
  диагностический звук (`feature:048`).

### Документы
- Обновлен текущий статус продукта и evidence 046/048: 046 оставлена как
  основа playback-пути, а 048 зафиксирована как исправление видимости для
  обычной записи (`feature:048`).

### Операции
- _Пока нет записей._

## [2026.06.24.2] - 2026-06-24


### Добавлено
- Встречу теперь можно слушать прямо на странице результата: сервер отдает
  безопасный звук для проверки, а не прямую ссылку на файл в хранилище
  (`feature:046`).
- Таймкоды в расшифровке стали кликабельными: пользователь может перейти в
  нужное место записи и быстро проверить конкретную реплику (`feature:046`).
- Веб-кабинет и встроенное окно macOS-приложения показывают одинаковое
  состояние прослушивания и одинаковые переходы по таймкодам (`feature:046`).

### Изменено
- Для записей с двумя дорожками звук для проверки должен включать и локальный
  микрофон, и входящий звук. Если сервер не может безопасно собрать оба источника,
  плеер не притворяется готовым (`feature:046`).

### Исправлено
- _Пока нет записей._

### Безопасность
- Прослушивание результата теперь закрыто теми же правилами доступа, удаления,
  обработки и наличия аудио. Для чужих, удаляемых, неготовых, ошибочных или
  неполных встреч сервер не отдает аудио (`feature:046`).
- Логи и evidence по прослушиванию остаются metadata-only: без сырого аудио,
  текста встреч, ключей хранения, signed URL и приватных путей (`feature:046`).

### Документы
- Обновлен текущий MVP-статус: прослушивание по таймкодам закрыто локальной
  реализацией 046, но общий MVP еще требует финальных проверок, релиза и
  доказательств на проде.

### Операции
- _Пока нет записей._

## [2026.06.24.1] - 2026-06-24


### Добавлено
- Запись теперь проходит весь путь до результата: приложение загружает запись,
  сервер запускает обработку, а в кабинете появляются расшифровка и разделение
  говорящих (`feature:045`).
- Сервер сам стартует обработку после успешной загрузки. Если обработка уже
  идет, второй запуск не создается (`feature:045`).
- В веб-кабинете и во встроенном окне приложения показано, что уже готово:
  загрузка, обработка, расшифровка, говорящие, заметки и ограничения доступа
  (`feature:045`).
- В macOS-приложении появилась более надежная связка записи, очереди загрузки
  и серверного результата. Приложение может подтянуть готовый результат позже,
  даже если запись была загружена раньше (`feature:042`, `feature:045`).
- Проведены отдельные проверки микрофона, Apple Voice Processing и WebRTC AEC3
  для будущей работы над чистым звуком (`feature:037`, `feature:038`,
  `feature:039`).

### Изменено
- Проверка шума, тишины, эха и утечки звука из динамиков в микрофон больше не
  блокирует отправку записи, если сама запись целая и в ней есть нужные файлы
  (`feature:045`).
- Жесткие блокеры остались жесткими: запись не отправляется без разрешений, без
  нужных дорожек, с поврежденными файлами или с ошибками целостности
  (`feature:045`).
- Состояния в приложении стали честнее: отдельно видны локальная запись,
  загрузка, обработка, ошибка, конфликт и готовность результата (`feature:042`).

### Исправлено
- Исправлено обновление уже загруженных записей: если сервер обработал запись
  позже, приложение больше не должно оставлять ее в старом локальном статусе
  (`feature:045`).
- Исправлено сопоставление строк расшифровки и говорящих в кабинете, чтобы
  локальный микрофон и входящий звук не менялись местами в интерфейсе
  (`feature:045`).
- Исправлены русские тексты в кабинете и во встроенном окне приложения: меньше
  технических слов, понятнее состояния доступа, удаления, результата и заметок
  (`feature:045`).
- Исправлены несколько случаев, когда встроенный кабинет в приложении мог
  показать ложное состояние входа или недоступности после переходов внутри
  встроенного браузера (`feature:042`).

### Безопасность
- Диагностика и доказательства проверок остаются без приватного содержимого:
  без сырого аудио, текста расшифровок, ключей, токенов, приватных путей,
  подписанных ссылок и содержимого встреч (`feature:037`, `feature:038`,
  `feature:039`, `feature:042`, `feature:045`).
- Приложение по-прежнему не отправляет аудио напрямую в MediaScribe и не хранит
  ключи MediaScribe на Mac (`feature:045`).

### Документы
- Зафиксировано, что полноценное прослушивание по таймкодам еще не закрыто и
  должно идти отдельной фичей (`feature:045`).
- Зафиксировано, что настоящее эхоподавление и шумоподавление не входят в этот
  релиз и остаются отдельной работой (`feature:044`).
- Зафиксированы оставшиеся MVP-блокеры: чистый звук или честное ограничение,
  прослушивание по таймкодам, заметки/действия или явное отложенное решение,
  финальная проверка владельцем и подписанный установщик.

### Операции
- Серверная часть выпущена на прод как `v2026.06.24.1`.
- Перед выкаткой прошли локальные проверки, сборка продовой конфигурации,
  резервное копирование, проверка восстановления, запуск сервиса и проверка
  работоспособности.
- К релизу приложен локальный пакет macOS для внутренней проверки. Он не
  подписан сертификатом Apple Developer ID и не заверен Apple для внешнего
  распространения.

## [2026.06.18.1] - 2026-06-18


### Added
- _No entries yet._

### Changed
- _No entries yet._

### Fixed
- _No entries yet._

### Security
- _No entries yet._

### Docs
- Добавлены правила release/versioning: CalVer `vYYYY.MM.DD.N` для
  продуктовых apps/services, SemVer `vMAJOR.MINOR.PATCH` для tooling,
  extensions и bootstrap, а человекочитаемый postfix теперь должен жить в
  GitHub Release title, не в stable tag.

### Ops
- _No entries yet._

## [0.1.0] - 2026-06-18


### Added

- Добавлены macOS shortcuts масштаба embedded meeting workspace:
  `Command-Plus` / `Command-Equals` увеличивают масштаб, `Command-Minus`
  уменьшает, `Command-0` сбрасывает к 100%; настройка хранится локально,
  применяется к `WKWebView.pageZoom` без route reload и оставляет native
  Record/Stop/upload truth/local readiness вне масштабируемой поверхности
  (`feature:043`, `T001-T017`).
- Добавлена production-доставка browser-login email-кодов через server-side
  Postal API: отдельные `.env` настройки для Rec, Docker secret для API key,
  fail-closed состояние при недоступной почтовой доставке и подключение
  `rec-api` к внешней сети Postal (`feature:036`).
- Добавлен browser-login по email-коду для web cabinet: `/login`,
  `/login/email/start`, `/login/email/verify`, HttpOnly/Secure owner-session
  cookie, browser-device binding, redirect protected web routes to login, and
  visible OAuth/provider stubs for later implementation (`feature:036`).
- Добавлена browser-регистрация по email-коду без видимого Workspace ID:
  `/sign-up`, `/sign-up/email/start`, `/sign-up/email/verify`, автоматическое
  создание пользователя и membership в серверно заданном workspace, русская
  страница ввода 6-значного кода и Krisp-like HTML-письмо через Postal
  (`feature:036`).
- Добавлен product-owned слой meeting-app mute truth для macOS: `Pause`/`Resume`
  рядом с постоянным `Stop`, подавление локального микрофона во время паузы,
  metadata-only `privacySegments`, target capability matrix, fail-closed
  `meetingMuteTruth` decisions, fixture validator и QA evidence templates без
  claims о third-party meeting-app mute support (`feature:022`, `T001-T048`).
- Добавлен launch-readiness gate `034-mvp-loop-readiness`: metadata-only
  readiness JSON/Markdown report, launch gap register, clean-room reference
  comparison, desktop/web/policy lifecycle evidence notes, bounded claim rules,
  and evidence-backed next-slice recommendation (`feature:034`, `T001-T059`).
- Добавлен validation-only evidence pack `035-mvp-loop-live-evidence`: proof
  установленного `/Applications/2brain Rec.app` Record/Pause/Resume/Stop loop,
  metadata-safe desktop screenshots, latest local artifact validation,
  production route check for `rec.2brain.pro/meetings`, fixture-backed web
  list/detail/governance evidence, and generated readiness/gap outputs
  (`feature:035`, `T001-T032`).
- Добавлен server-owned слой retention/deletion execution: whole-meeting
  deletion requests, immediate access blocking for deleting/deleted meetings,
  metadata-only verification reports, retention policy snapshots and scans,
  local desktop purge task/ack flow, backup expiry truth, dependency truth for
  MediaScribe/Langfuse/workflow/temp/diagnostics, post-egress copy limits,
  lifecycle activity rows, safe retry guidance, and RLS coverage for deletion
  lifecycle tables (`feature:018`, `T001-T066`).
- Добавлен browser/server-owned слой доступа, шаринга, скачивания и экспорта
  встреч: owner/team/shared/denied access states, login-required share grants
  and revoke, server-mediated artifact downloads, policy-filtered export
  packages, metadata-only access/egress activity и truthful post-egress deletion
  copy (`feature:017`, `T001-T045`).
- Добавлен macOS desktop cabinet embedding: приложение открывает `Встречи`
  внутри native shell, встраивает server-owned list/detail route classes,
  сохраняет native Record/Stop/upload truth вне WebKit surface, показывает
  bounded unavailable state и связывает uploaded queue items с review только
  при наличии server meeting identity (`feature:033`, `T001-T042`).
- Добавлен server-owned web cabinet для review встреч: авторизованный список,
  ready/partial/processing/failed detail states, transcript/speaker timeline,
  truthful unavailable notes, gated governance/future slots и desktop-embedded
  routes без native capture controls (`feature:016`, `T001-T048`).
- Добавлена обязанность вести Changelog в репозитории для всех значимых изменений.
- Добавлена macOS desktop upload queue: durable local queue, truthful retry/upload states,
  server-mediated ingest mapping and compact queue UI (`feature:014`, `T001-T030`).
- Добавлен server-side MediaScribe processing pipeline: durable workflow/job/result
  state, idempotent Temporal workflow identity, server-side dual-track submit,
  poll/import, content-safe status API, failure classification, restart-safe job
  reuse, and dependency truth for future deletion (`feature:015`, `T001-T087`).
- Добавлен backend tenant-isolation RLS hardening слой: PostgreSQL policies,
  request/worker/auth bootstrap/session lookup/callback lookup/maintenance DB
  contexts, rollout validation helper, and future-table ADR (`feature:031`,
  `T001-T052`).
- Добавлен MVP experience/design handoff для `2brain Rec`: clean-room audit,
  native/web route boundaries, status matrices, screen specs, embedded
  server-owned speaker assignment для desktop shell и активный Figma v8 clean
  Russian implementation baseline с 98 валидными click reactions
  (`feature:030`, `T001-T085`).

### Changed

- GitHub issue and pull request workflow now follows the Russian-only issue
  canon: issue forms use Russian sections, PR descriptions must be written in
  Russian, `Fixes`/`Closes`/`Resolves` are reserved for issues fully closed by
  a PR, partial work must use `Refs`/`Part of`, and every closed issue requires
  a detailed Russian closure comment that explains what changed, why it
  matters, how it was checked, what is out of scope, and which PR/Spec Kit task
  it closes. The project also now ships a PR template and a synced
  `github-issue-canon` extension `v0.2.0` copy for future task-to-issue syncs.
- `docs/current-product-status.md` and the MVP readiness report now record
  `022-meeting-mute-truth` as closed, remove stale `018`/`022` next-slice
  guidance, and recommend validation-only `035-mvp-loop-live-evidence` while
  keeping live desktop/web evidence, notes/action truth, and production
  user-journey proof as launch gates (`feature:022`, `feature:034`,
  `T045-T051`).
- `docs/current-product-status.md` and the 035 readiness report now close the
  stale installed-desktop evidence gap, keep production owner review blocked on
  `401 missing_auth_context`, and recommend `036-owner-review-live-polish` as
  the next launch slice (`feature:035`, `T026-T032`).
- Web cabinet and auth pages now follow the Krisp reference more closely while
  staying clean-room: Russian copy, centered dark auth cards, email/signup mode
  transitions, six-slot verification input, denser meetings list, upcoming
  events card, floating assistant input, and future-control slots for provider,
  sharing, filters, sorting and upload (`feature:036`).
- Desktop owner-review shell now follows the reference layout more closely:
  slimmer sidebar, embedded meetings surface without duplicate native cards,
  compact collapsible right rail, denser web meeting workspace, and a
  profile/settings menu with Russian clean-room copy (`feature:036`).
- Native desktop shell and embedded web cabinet now share the same Krisp-like
  warm dark palette and SF/system typography tokens: sidebar/right rail
  `#202224`, native/WebView background `#191a1c`, cards `#242629`, and a
  shared violet accent for compact rail states and web controls (`feature:036`).
- Desktop sidebar width now adapts to its Russian labels and pending-action
  badge with min/max bounds, so normal windows show the full menu text while
  narrow resolutions fall back to the compact width (`feature:036`).
- Синхронизирован Speckit workflow с обязательными этапами `clarify`,
  `checklist`, `analyze`, `taskstoissues`, чтобы требования и контроль качества
  были сквозными.
- RLS validation wording now separates destructive test/disposable probes from
  production read-only RLS state truth (`feature:032`, `T001-T014`).

### Fixed

- Dev MinIO policy now includes bucket metadata and multipart permissions
  required by local readiness/upload checks, so `docker-compose.dev.yml`
  can reach `ready` after the local stack is rebuilt (`feature:043`).
- Desktop sidebar navigation now uses native clickable rows, tracks embedded
  WebKit route changes, and lets `Мои встречи` return from a meeting detail
  route back to the recordings list inside the app (`feature:042`).
- Desktop meetings shell now keeps local-only queued/blocked recordings visible
  above the embedded server cabinet until a server meeting identity exists, so
  a saved recording no longer disappears from the app when upload is blocked by
  local quality/privacy truth (`feature:042`).
- Desktop recording upload now uses the packaged production origin when no
  shell environment is present, reuses the embedded web owner session cookie for
  native upload requests, refreshes stale local queue eligibility, and uploads
  safe degraded recording packages so saved recordings can appear in web and
  desktop review instead of remaining local-only blocked items (`feature:042`).
- Desktop embedded cabinet now preserves desktop auth headers across WebKit
  link navigations to `/desktop/meetings` and meeting detail routes, so clicking
  a recording row no longer falls back to a false login/unavailable state
  (`feature:042`).
- Desktop embedded cabinet now ignores non-main-frame WebKit response failures,
  so favicon/apple-touch icon probes cannot replace a valid login/meetings
  surface with a false unavailable state; production web cabinet also answers
  standard icon probes without `404` noise (`feature:042`).
- Local macOS install now force-registers the copied `2brain Rec.app` bundle with
  LaunchServices, reducing stale Dock/Spotlight launches after rebuilding the
  desktop app (`feature:042`).
- Desktop app now installs standard macOS `Edit`/`Window` menus, so embedded
  cabinet fields receive `Cmd+V`, `Cmd+A`, copy, cut, paste and related
  responder-chain commands in `/Applications/2brain Rec.app` (`feature:036`).
- Desktop embedded cabinet now allows production `/login` routes, ignores
  WebKit `about:blank` navigation noise, and sends expired-session recovery to
  `/login?next=/desktop/meetings`, so the installed `/Applications/2brain Rec.app`
  renders browser-login instead of a false blocked-route state (`feature:036`).
- В `.github` и процессе разработки зафиксирован порядок этапов и коммитов для
  Spec Kit.
- MediaScribe client now follows the live production contract for polling and
  result import via `/jobs/{job_id}` and normalizes `start`/`end`/`speaker`
  fields into persisted processing rows (`feature:015`).
- Исправлены имена unique constraints для MediaScribe processing migration,
  чтобы production PostgreSQL migration не падала на конфликте имен
  (`feature:015`).
- Укорочен Alembic revision id для `0004`, чтобы он помещался в стандартный
  `alembic_version.version_num`, и Temporal production wrapper теперь читает
  local-file secrets с корректными правами (`feature:015`).
- Production env template больше не рассылает service-specific secret-file
  paths во все app containers, а ошибки production secret validation называют
  конкретное field name без раскрытия secret values (`feature:015`).
- Malformed successful MediaScribe submit/result payloads now map to safe
  retryable `mediascribe_malformed_response` processing state instead of
  escaping as unmanaged validation exceptions (`feature:015`).
- Missing or unreadable MediaScribe API key files now map to safe
  `blocked_config` instead of unmanaged file-system exceptions (`feature:015`).
- Production `rec-api` no longer mounts the MediaScribe API key Docker secret;
  only `rec-processing-worker` receives that secret (`feature:015`).

### Security

- Postal API key for browser-login delivery is mounted only as a Docker secret;
  deploy/runtime scans now reject accidental `TWOBRAIN_POSTAL_API_KEY`
  environment exposure, and desktop clients never receive Postal settings
  (`feature:036`).
- Browser cabinet content stays behind an email-issued owner session: protected
  web routes redirect HTML requests to login, email-code failures do not reveal
  whether an address exists, and browser OAuth provider routes are explicit
  future stubs instead of partially enabled auth paths (`feature:036`).
- Meeting-app mute truth remains fail-closed: diagnostics/redaction allow only
  metadata fields, fixture validation rejects raw audio/transcripts/meeting
  content/credentials/signed URLs, unsupported targets never become
  `mute_respecting`, and upload queue completeness is not reinterpreted by
  mute-truth metadata (`feature:022`, `T006-T011`, `T022-T042`).
- Readiness evidence for `034` is metadata-only by contract: unsafe screenshots
  are rejected, reference-comparison evidence IDs are validated, committed
  evidence cannot include private Krisp screenshots or private meeting content,
  and production claims stay bounded to `infra_smoke_ready` until stronger
  evidence exists (`feature:034`, `T005-T014`, `T028`, `T055`).
- Readiness evidence for `035` keeps live web owner review metadata-only:
  private Chrome session data, account identifiers, screenshots, cookies,
  tokens, transcript text, audio, and production destructive governance actions
  are not committed (`feature:035`, `T020-T025`, `T039`).
- Retention/deletion reports and lifecycle activity are metadata-only by
  default: they do not expose raw audio, transcript text, summaries, local
  paths, object-store keys, signed URLs, provider payloads, dependency job IDs,
  bearer tokens, credentials, or private desktop proof payloads. Deletion
  requests fail closed when audit/report evidence cannot be written before
  lifecycle mutation, and desktop local purge acknowledgements reject private
  path/content payloads (`feature:018`, `T011-T015`, `T020-T028`,
  `T037-T045`, `T053-T059`).
- Access/sharing/download/export routes now re-check effective viewer access,
  never expose object-store keys, signed URLs, raw local paths, bearer tokens,
  MediaScribe identifiers, or private artifact content in egress responses, and
  fail closed when metadata-only audit cannot be written before share/revoke/
  download/export actions (`feature:017`, `T008`, `T020-T024`, `T028-T039`).
- RLS coverage now includes meeting share grants, artifact policies, egress
  audit events, and export packages via `0006_access_sharing_downloads`
  (`feature:017`, `T004-T006`).
- Desktop cabinet embedding adds an explicit embedded route allowlist for
  `/desktop/meetings` and meeting detail routes, blocks native capture/local
  diagnostics/share/export/download/delete destinations inside the embedded
  surface, and records sanitized screenshot evidence without Krisp private
  captures, account identifiers, transcript text, raw audio, signed URLs, or
  live local paths (`feature:033`, `T005`, `T008`, `T034-T041`).
- Cabinet API и web routes используют существующий tenant/device auth context,
  скрывают foreign meeting existence через privacy-preserving 404 и не отдают
  transcript text в list responses, storage keys, signed URLs, workflow/run ids
  или MediaScribe external ids (`feature:016`, `T011`, `T029`, `T030`).
- MediaScribe credentials remain server-side through secret-file configuration;
  processing status, audit metadata, logs, and evidence must not expose raw
  audio, transcript text, signed URLs, API keys, bearer tokens, passwords, or
  live secret paths (`feature:015`, `T040`, `T065-T071`, `T086`).
- RLS hardening adds database-level tenant isolation coverage for accepted
  identity, auth/session/device, ingest, meeting, processing, transcript, audit,
  and dependency tables, while keeping product/admin bypass out of scope
  (`feature:031`, `T016-T037`).
- RLS post-review hardening now requires explicit auth-session lookup context,
  complete maintenance actor/reason/feature metadata, and fail-closed worker
  tenant scope before tenant-owned processing DB operations (`feature:031`,
  `CR-003`, `CR-005`, `CR-006`).
- RLS post-review hardening now preserves controlled auth/link conflict outcomes
  for globally unique provider identities, requires membership or bounded auth
  bootstrap guards for organization-scoped policies, and rejects unknown tenant
  context kinds at runtime (`feature:031`, `CR-004`, `CR-007`, `CR-008`).
- Provider link conflict/rejected paths now commit metadata-only auth audit
  evidence before returning controlled error responses (`feature:031`, `CR-009`).
- RLS validation now blocks before migrations or probes when
  `RLS_TEST_DATABASE_URL` points at the live `twobrain_rec` database
  (`feature:031`, `#734`, `#735`).
- Production RLS enforcement is now recorded as verified enabled and forced
  through read-only PostgreSQL catalog metadata: production Alembic
  `0005_rls_hardening` and all covered tables report RLS enabled/forced
  (`feature:032`, `T015-T020`).

### Docs

- Added feature `022` evidence scaffold, target matrix, manual validation
  template, and current-product-status update for the boundary between
  product-owned Pause truth and future meeting-app mute adapters (`feature:022`,
  `T041-T044`).
- Reorganized Codex/Spec Kit operating guidance: root `AGENTS.md` now acts as
  a concise router, detailed rules live under `docs/agent-guidance/`, GitHub
  issue canon moved to `docs/agent-guidance/github-issue-canon.md`, and active
  guidance now treats Linear as retired workflow residue.
- Added sanitized feature `017` evidence index and refreshed current product
  status so access, login-required sharing, server-mediated downloads, and safe
  exports are no longer listed as deferred launch gaps (`feature:017`,
  `T040-T045`).
- Обновлены feature `033` implementation evidence, clean-room screenshot notes,
  and current product status so `016` is no longer treated as the next product
  slice after desktop cabinet embedding (`feature:033`, `T034-T037`).
- Обновлён `AGENTS.md`:
  - добавлен раздел `Versioning And Changelog`;
  - закреплён процесс обязательного обновления `CHANGELOG.md`;
  - закреплён системный подход к SemVer и git-тегам релизов.
- Обновлены server README и current product status для границ `015`, fake
  dependency flow, и разделения будущих `016/017/018` поверхностей.
- Зафиксированы production deployment и real-recording e2e evidence для
  `015` без сохранения transcript text в tracked docs.
- Добавлены RLS rollout runbook, ADR `003-tenant-isolation-rls`, and current
  product-status notes for RLS rollout gates (`feature:031`, `T043`,
  `T049-T052`).
- Corrected stale `031` RLS rollout wording in product status, ADR, runbook,
  and quickstart so current docs reflect verified production enabled/forced
  state while preserving test-only destructive probe boundaries
  (`feature:032`, `T021-T027`).

### Ops

- `017` развернут на `2brain.dev` (`master` at `39b8c5f`) и проверен
  production infra smoke: `rec-api` healthy, Alembic
  `0006_access_sharing_downloads`, `/health/live` ok и `/health/ready` ready
  (`feature:017`).
- Production smoke для desktop upload queue теперь выпускает временную Rec
  `AuthSession` вместо использования инфраструктурного smoke secret как bearer
  (`feature:014`, `T036-T038`).
- Добавлены production/dev Compose placeholders для Temporal и processing
  worker без live secrets (`feature:015`, `T010`, `T071`, `T085`).
- Remote CD теперь запускает Temporal и processing worker, которые нужны для
  production-проверки обработки (`feature:015`).
- Production Temporal теперь запускается на Postgres backend через Docker
  secret wrapper, а CD блокирует статический `POSTGRES_PWD` в compose config
  (`feature:015`).
- Production processing worker теперь может читать local-file Docker secrets,
  включая MediaScribe API key, при запуске из Compose (`feature:015`).
- Production processing worker больше не наследует smoke/awareness credential
  file settings, которые не нужны для MediaScribe processing (`feature:015`).
- Production smoke cleanup теперь удаляет 015 processing rows перед meeting
  cleanup, чтобы real processing e2e не оставлял residue в Postgres (`feature:015`).
- `015` развернут на `2brain.dev` (`master` at `4cda38c`) и проверен полным
  production e2e на реальной записи приложения: upload, pickup, Temporal
  worker, live MediaScribe, result import, content-safe status и cleanup
  прошли успешно (`feature:015`).
- Local CI and migration verification now reference RLS validation without
  using destructive live production probes (`feature:031`, `T041-T045`).
- RLS migration verification now blocks when the validation helper returns a
  blocked verdict, and the helper delegates to a real PostgreSQL policy suite
  when `RLS_TEST_DATABASE_URL` is supplied (`feature:031`, `CR-001`, `CR-002`).
- PostgreSQL RLS probes now use a non-owner probe role and a SQL-only UUID GUC
  helper, so validation checks enforced RLS behavior without superuser/owner
  bypass and avoids PL/pgSQL migration hangs observed on local PostgreSQL 14
  (`feature:031`, `CR-001`).
- Added production read-only RLS state verification output for covered-table
  counts, enabled/forced counts, failed tables, deployed commit, and Alembic
  revision (`feature:032`, `T015-T020`, `T028-T037`).

## [Unreleased Template]

### Added
### Changed
### Fixed
### Security
### Docs
### Ops
