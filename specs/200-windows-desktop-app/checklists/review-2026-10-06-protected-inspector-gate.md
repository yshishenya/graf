# Round257 — независимый REQUIREMENTS review: проверка AAC и границы защищённого инспектора

Дата: 2026-10-06. Основание: конкретное ограниченное предложение Round257 и
уточнения main до начала RED/изменений кода. Это проверка требований и
согласованности, а не проверка реализации, запуск тестов или приёмка приложения.

## Решение

**NO-GO — REQUIREMENTS / scoped analyze для текущего предложения безусловно
декодировать весь AAC при каждом существующем `inspect`.** Предварительный узкий
GO, записанный до последнего causal update main, **отозван до RED/реализации**:
codec-семантика определена, но фактическое подключение не удовлетворяет
worker/admission/cancellation/lifetime границе. Причина и минимальная зависимость
ниже. Это не новая политика AAC и не требование сначала закончить весь T116.
Изолированный RED на synthetic media допустим как доказательство нынешнего
header-only дефекта, но не как разрешение изменить production helper.

**NOT GO — полный защищённый semantic inspector, его подключение и T116 целиком.**
Их готовность не следует ни из codec-предложения, ни из принятого Round256.
SOURCE/native/installed/release PASS этим отчётом не выданы. Новая реализация и
её тесты ещё не прочитаны и не выполнены. Условия ниже описывают следующую
проверку, не восстанавливают отозванный production допуск.

## Привязка к рабочему дереву и исходному состоянию

- Canonical: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
- Ветка: `codex/200-windows-followup`.
- HEAD: `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
- Рабочее дерево содержит чужие незакоммиченные изменения: они сохранены;
  один HEAD не описывает рассматриваемое состояние, поэтому ниже приведены SHA-256 файлов.
- Открытый внешний владелец всей цепочки — T116 / GitHub #7444. Задача не закрывается.
- Единственный файл, который пишет этот reviewer, — настоящий новый отчёт.

SHA-256 исходных файлов до RED:

| Файл | SHA-256 |
| --- | --- |
| `apps/windows/RecApp/Recording/LocalRecordingPackage.cpp` | `38b709c9a184ac586b1112cf934e4bfbada400815202eaad34aa463fda13b859` |
| `apps/windows/RecApp/Recording/LocalRecordingPackage.h` | `bd54424e3e9b826c3233d5a1158247ecec0ef5aff9cef34887097192c87dc698` |
| `apps/windows/Tests/GrafWindowsCoreTests/NativeHashFailureTests.cpp` | `65035b070a2ce26e10a3dca51d5af4b24c3c59d9e7d3da131b435bf96fdc4fc4` |
| `apps/windows/RecApp/Recording/V5LocalRecordingWriter.cpp` | `b890339cfc0b21d1ef3d6c2840e01e2eb5ecabbdf5444593682279f780c6c453` |
| `specs/200-windows-desktop-app/spec.md` | `b411bfb620e9d571422f9c423b0ae193ed70e87303d08e84a4b9844e32f81658` |
| `specs/200-windows-desktop-app/plan.md` | `527e660d9e1682e7a0f0a79118ea4bab38d4c174542b49c0113f571528a5b89c` |
| `specs/200-windows-desktop-app/tasks.md` | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| `specs/200-windows-desktop-app/quickstart.md` | `fc225d2ec40cc26a7fad0bc6d7adcb22d7f4d676fcdf70b2e645dbbdb06ddb8e` |
| `specs/200-windows-desktop-app/data-model.md` | `8dd54012c3bfe4003cd18db98ebc67e0b7730cbbdfb6523b881cce4cdc15ec19` |
| `specs/200-windows-desktop-app/contracts/windows-protected-local-custody.md` | `ec93d11c474cb970d57c2324518d541cd9fb3e7bb7f2f807d63d612ad878624a` |
| `specs/200-windows-desktop-app/contracts/windows-protected-packed-custody.md` | `a1dedd9d5b7ce02e4a6c200a300b0423bcada82192217e2a79f9773428c4a7b5` |
| `specs/200-windows-desktop-app/contracts/windows-desktop-contract.md` | `79a5b1870748f50f857e082d6ec5b2f99ba6a9149d846718865ef1de71cf5d2d` |

## Проверка действующих требований и согласованности

Прочитаны инструкции `speckit-implement`, `speckit-analyze`, canonical AGENTS,
указатель руководств и относящиеся к риску правила Spec Kit, worktree, product
gates, tracker, release/validation, конституция. Проверены критерии всех десяти
активных нормативных списков; из длинных feature-документов проверены относящиеся
к этой области разделы, а не объявлено повторное прочтение всей истории.

Основные нормативные основания:

- Spec FR-011/012/013/014/022; Desktop contract §5, строки 355–383:
  WAV PCM16/16 kHz/mono и playback AAC-LC/48 kHz/mono, отдельные роли,
  размер/hash/декодируемость/число кадров/длительность до normal.
- `audio-capture.md` CHK015: действующий допуск длительности не более 100 ms;
  новый порог или изменение политики этим предложением не вводятся.
- `requirements.md` CHK008/019: normal/degraded и совместимость логического v5
  нельзя переопределить успешным открытием контейнера.
- Local custody §§3, 5–6, 8–9 и packed contract §§6–7: существующий путь
  переиспользуется; отсутствие открытых временных копий, worker/lifetime,
  ограничения памяти и отдельная приёмка всего приложения сохраняются.
- `privacy-pause.md` CHK007–012: сегменты, полный manifest cap64KiB и
  protected/capture зависимости остаются самостоятельной работой.

В codec-семантике конфликта spec/plan/tasks/contracts или нового неописанного
продуктового решения не найдено. Однако ограниченность реального подключения
не доказана и отсутствует в предложении; одной проверки codec недостаточно.
Перенос исправления в новый неподключённый factory/adapter сам по себе эту
зависимость также не закрывает.

## Блокирующая зависимость: реальный scan/open/upload flow

**REQ257-B1, блокирует production adoption текущего предложения.**

- `AppMain.cpp:1940–1970`, `updateLocalRecordings`: на изменение inventory или
  refresh запускается detached scan всех локальных пакетов. Shared scan object
  удерживает результат, но не immutable file owner, cancel/context или native
  admission. Новый full decode здесь повторяется для всей коллекции; это не
  утверждение, что scan безусловно стартует на каждом UI tick.
- `AppMain.cpp:2170–2198`, действие open: отдельный detached worker на каждое
  действие повторно вызывает `inspect`; в этом пути нет общего decoder job
  admission/cancel. `alive` проверяется в UI callback после работы, не отменяет
  само чтение и не удерживает неизменные bytes между hash/decode/открытием.
- `DesktopHttpTransport.cpp:149,1009`: очередной `packageTracks` вновь проверяет
  весь playback. Длительный decode не получает через `inspect` текущие
  cancellation/context или retained immutable snapshot.
- `LocalRecordingPackage.h:31–34`: API принимает directory/root, не job/context
  или owner. Перечисленные scan/open вызовы сами по себе не гарантируют общий
  предел concurrent MF jobs. Synchronous `ReadSample` может блокировать;
  manifest-proportional лимит числа PCM-кадров не ограничивает время одного
  такого вызова или повторов для N пакетов.

Нормативное основание: local custody §5 (owned/native budgets, IO только в
worker, owner до actual terminal completion), §6 (pinned bytes и lifetime),
§7, строки 295–307 (каждая работа владеет snapshot/cancel/epoch/pin,
проверки до IO/эффекта и cancel/quiesce перед очисткой), SC-001/003.
Worker-only и `shared_ptr` результата не равны этим условиям. Из этого чтения
не следует измеренное нарушение SC-003: отказ сейчас основан на отсутствующей
границе в предложении, а не выдуманном результате испытаний производительности.

**Минимум для нового предложения:** действительный ограниченный decoder job с
retained immutable input на весь hash/config/decode, cancel/currentness перед
и после native ожиданий, owner до фактического завершения; явно ограниченное
допущение работы scan/open/upload и запрет повторного полного декодирования
коллекции ради простой metadata projection. Если projection отделяется от
semantic proof, она не возвращает normal/playback authority без этого proof.
Возможна pure codec prerequisite, но только с таким реальным input/job boundary;
её изолированный тест не означает подключение приложения.

Нельзя снять B1 тестом одного 1s AAC, одним throughput benchmark, фиктивным
cancel/flag, кэшем по изменяемому пути или предполагаемым future protected
owner. Бенчмарки коллекции/длинных файлов и отмены станут SOURCE evidence после
определения реальной границы, но не заменяют её. Производственные code/tests
на момент решения ещё не изменены main; reviewer их не исполнял.

Последнее уточнение main о `localMetadataKey`, одном активном scan и
последовательном обходе **подтверждено личным чтением**. Утверждение о full
decode «на каждом tick» не является finding этого отчёта и отвергнуто.
Однако это уточнение не передаёт cancel/immutable owner/job admission в
`inspect`, не ограничивает совокупные scan/open/upload native jobs и не
проверяет currentness в продолжительном чтении. Поэтому итоговый NO-GO для
нынешнего production предложения сохраняется; это не просто условный SOURCE
benchmark. Измерения 30s/представительной длительности полезны, но не доказывают
отсутствующую lifecycle границу. Вся crypto/queue/migration цепочка не требуется
для снятия B1: требуется конкретная минимальная безопасная граница этой работы.

## Определённые codec-условия для следующего предложения — не текущий допуск

| Условие | Что именно требуется |
| --- | --- |
| Реальный потребитель | Меняется один существующий internal `canonicalPlayback`; публичные `inspect`, профиль и API сохраняются. Его используют `DesktopHttpTransport::packageTracks` и два worker-пути AppMain: сканирование и проверка перед открытием. Это полезное исправление общего существующего пути, но не подключение protected IStream. |
| Единственный поток | Native stream 0 существует и имеет major type Audio, subtype AAC, 48 kHz, mono. `GetNativeMediaType(1,0)` должен вернуть именно `MF_E_INVALIDSTREAMNUMBER`; произвольная ошибка, `MF_E_NO_MORE_TYPES` или выбор лишь FIRST_AUDIO_STREAM не доказывают отсутствие других потоков. NEWSTREAM при чтении отвергается. |
| AAC-LC/config | Проверяется документированная native конфигурация raw AAC, а не только GUID AAC. Для известной формы 12B HEAAC extra + 2B ASC значение ASC `0x11 0x88` соответствует AOT2/48 kHz/mono и нулевым дополнительным флагам. Проверяются payload/struct/reserved и согласованность доступных атрибутов; известный HE-профиль не принимается за LC. Требовать один произвольный profile-level byte, не подтверждённый существующим writer, нельзя. |
| Неявный SBR/PS | Две ASC-байта сами по себе не доказывают отсутствие HE-AAC. Нужен фактический выход native decoder PCM16/mono/48 kHz без принудительного пересчёта частоты или сведения каналов, с проверкой выходного формата и отказом при его изменении. Неизвестная/противоречивая форма отвергается, а не «нормализуется» до normal. Нельзя считать установленный желаемый output type доказательством фактического native формата. |
| Полное декодирование | Чтение PCM идёт до настоящего ENDOFSTREAM. HRESULT/ERROR, type change, stream tick/gap, чужой stream, неизвестные флаги, пустой или некорректный sample не превращаются в успех. NULL sample без EOS не считается EOF. Данные последнего sample, если он сопровождает EOS, не теряются. |
| Ограниченность | Без накопления всей записи/копирования полного PCM. Проверки размера, block alignment, суммы PCM-кадров, timestamp/duration и арифметического переполнения предшествуют использованию/собственным выделениям памяти. Верхняя граница суммарных декодированных кадров выводится из manifest duration + существующие 100 ms, а не из нового произвольного лимита длительности. События без прогресса не допускают бесконечный цикл. |
| Длительность | Положительные container duration и duration по реально декодированным PCM-кадрам отдельно сопоставляются с manifest в пределах действующих 100 ms. Одного timestamp последнего sample недостаточно. Регрессия времени, несовместимые sample lengths/durations и обрезанный вывод не маскируются допуском или padding. Границу нельзя расширить новым округлением. |
| Lifetime/worker | IO/MF остаются в worker, не UI/WASAPI callback. Sample/buffer/type/reader освобождаются в корректном порядке до MFShutdown/CoUninitialize; собственные буферы не сохраняются для позднего эффекта. Новый protected context/cancel/job budget здесь не объявляется реализованным. |
| Никаких побочных действий | Проверка только читает. Нет новых dependency, production container parser, temp, re-encoding, plaintext fallback, миграции, repair, queue/admission/owner effects или записи в рабочий профиль. Существующий URL-путь не становится разрешённым protected playback; его устранение/миграция остаются T116/T117. |
| Результаты ветвей | Normal с недействительным AAC становится malformed; playback недоступен. Существующий degraded с корректными artifact hashes может остаться degraded по нынешней ветви, но не становится normal/upload-eligible. Усиление AAC не подтверждает trusted prefix и не меняет правила degraded/short. |

### Минимальная проверка до SOURCE GO — пока не выполнена

1. RED в существующем native test: сгенерированный writer-ом 1s AAC остаётся
   положительным примером. Повредить реальный `mdat`, сохранив контейнерные
   заголовки/длительность и пересчитав корректные manifest bytes/SHA: текущая
   проверка должна дать ложный valid, а новая — отказ. Причина отказа должна
   быть семантической, не несовпадением hash/length.
2. Через реальный `inspect`/upload подтвердить `invalidPackage` и `sends == 0`
   для такого normal-пакета; прежний положительный upload/hash baseline сохранить.
3. Проверить отсутствие/добавление потока, неправильную/неизвестную native
   config, пустой/обрезанный/испорченный вывод, фактический выходной формат,
   EOS и границу <=100 ms. Конкретные отличия decoder/priming подтверждаются
   native результатами, а не предполагаются по заголовку.
4. Последовательные focused Windows Release/Debug, затем SDK/portable checks
   выполняет main; reviewer их не запускал. Portable false не доказывает
   native AAC, generated media не доказывает физический capture/SC-003.

Полное декодирование не является обещанием обнаружить любую возможную порчу:
декодер может принять некоторые изменённые данные. Нужны конкретные примеры
отказа; нельзя назвать универсальной проверкой целостности codec success,
особенно если потеря малого числа кадров укладывается в допуск 100 ms.
Нормативный SHA отвечает за точные байты; decoder — за подтверждённую
декодируемость и фактический профиль/длительность.

## Отложенные требования полного защищённого инспектора — NOT GO

Эти условия не блокируют узкий AAC prerequisite и не отмечаются выполненными:

| Область | Следующая обязательная граница |
| --- | --- |
| Pair/batch | Оба actual slots/closures удерживаются одним owner/group весь hash/read/MF lifetime. Выбранный sealedNormal/sealedDegraded определяется проверенной metadata authority; старый LIVE сосед не обязан иметь normal-семантику. Readable refs/structural proof Round256 не заменяют member semantics. |
| Normal | Exact selected logical manifest/media/playback lengths и SHA, WAV frame/format/duration и настоящая AAC-проверка согласованы с фазой/reason. Capturing/finalizing/discardPending не возвращают semantic normal. |
| Degraded | Известная причина и положительный фактически проверенный cleaned prefix, полные 480-float/10ms кадры, точные bytes/hash/duration; отсутствие recovery или простое существование файла не доказательство. Никаких padding/re-AEC/raw recovery. Degraded не становится normal/автоматическим upload. |
| Manifest/privacy | Текущий минимальный Windows snake_case manifest не равен полному camelCase Mac manifest. Следующее предложение должно однозначно задать разрешённые формы Win + Mac `privacySegments`, trusted session identity и binding `sessionId`, до реализации парсера. Нельзя молча принять directory_id за sessionId. |
| Mac сериализация | Data-model §1, строки 45–80, и pinned Mac `c8d67ccefe7848f731798b23d72d37757ad812f5`: 11 полей сегмента, ISO dates, monotonic bounds, user/known initiator/control/treatment, optional omission OPEN и совместимость legacy absent. Не угадывать null/unknown поля, не обрезать историю и не ослаблять проверку duplicate/type/overflow. Полный manifest <=64KiB. |
| Short | Metadata bool не даёт права удалить. Нужны точные положительные кадры, normal stop, отсутствие fault и durable marker до cleanup; Win frameCount считает 10ms блоки, Mac canonicalFrameCount — 48k samples. Исключение discardPending из инспектора не означает завершённый short/discard lifecycle. |
| Owner/context/admission | Текущие account/session/epoch/cancel полномочия до/после ожиданий и перед UI/network эффектом; root bootstrap/queue authority не создаются успехом чтения. Неизвестный owner не подменяется текущим входом. |
| Worker/budgets | Protected IStream → IMFByteStream без URL/temp; удержание owner/pin до shutdown/release и фактического завершения worker. Существующие 64MiB owned memory, cache2MiB, pins32, jobs4, chunk<=256KiB остаются; MF/DPAPI внутренние выделения отдельно измеряются. Узкий legacy helper этих гейтов не закрывает. |
| Полная цепочка | Writer/manifest-last, queue/upload/readiness/playback/delete, bootstrap, T117 migration и T118 whole-pipeline/installed/100cycles по-прежнему не приняты. `parseObjectFields` может быть reuse-кандидатом, но его пригодность и конкретный manifest codec ещё требуют отдельного предложения. |

## Инвентаризация: действующие критерии отдельно от истории

Перед записью этого отчёта сверены SHA-256 всех 107 существующих `.md` в
`checklists/` с первоначальным inventory этого reviewer: **107/107 совпали**.
Ни один прежний отчёт или checkbox не изменён.

| Группа | Файлы | Checked | Open |
| --- | ---: | ---: | ---: |
| Действующие normative checklists | 10 | 154 | 0 |
| Исторические списки/отчёты, кроме двух Round256 | 95 | 256 | 10 |
| Два scoped Round256 consumer gate/source reports | 2 | 0 | 0 |

Действующие 10: `advanced-routing` (14), `audio-capture` (24),
`calendar-launcher` (5), `calendar-operation` (8), `calendar-wire` (5),
`packed-writer` (12), `privacy-pause` (12), `requirements` (22), `security` (27),
`ux` (25). Их checked означает полноту требований, не исполнение функций.
Десять historical open не переклассифицированы в новые normative obligations.
Новый отчёт не содержит checkbox и не меняет эту базовую инвентаризацию.

SHA-256 неизменного inventory всех исходных 107 файлов:
`9cc1e2c71e1e1ec735b2c6d8975396ee1fa3baa0bed0ddbfd3456dcad94816fe`.
Алгоритм: сортировка repo-relative paths, строки `path + " " + file_sha256 + "\n"`,
SHA-256 объединённых строк; настоящий новый файл исключается.

Финальная повторная сверка после записи отчёта: прежние 107 файлов по-прежнему
совпадают с baseline; `LocalRecordingPackage.cpp` сохраняет исходный SHA выше.
В параллельной работе `NativeHashFailureTests.cpp` уже имеет другой SHA-256:
`f829083dab24e046659b57d0dd18719032ef7fadee3d464886c7b9158173c6a6`.
Таблица выше фиксирует именно состояние до RED, а не одобрение этих новых тестов.
Reviewer их не изменял, не отменял и не запускал; SOURCE/native PASS не выдан.

## Проверенные первичные сведения Media Foundation

- [AAC Decoder](https://learn.microsoft.com/en-us/windows/win32/medfound/aac-decoder):
  HEAAC extra + ASC; двухбайтовая ASC возможна с неявным SBR/PS. Поэтому
  `14B + 0x1188` не достаточная самостоятельная гарантия LC. Поддержка decoder
  и принятие одного output type не заменяют фактическую проверку результата.
- [AAC Media Types](https://learn.microsoft.com/en-us/windows/win32/medfound/aac-media-types):
  для MFAudioFormat_AAC native rate/channels описывают core до SBR/PS;
  отсутствие payload-type атрибута означает raw=0, а не произвольный subtype.
- [AAC Encoder](https://learn.microsoft.com/en-us/windows/win32/medfound/aac-encoder):
  существующий Microsoft encoder кодирует LC и добавляет USER_DATA;
  жёсткое требование одного profile-level byte сверх известного writer не выводится
  из продукта. Оно должно быть подтверждено формой producer, не выбранным примером.
- [GetNativeMediaType](https://learn.microsoft.com/en-us/windows/win32/api/mfreadwrite/nf-mfreadwrite-imfsourcereader-getnativemediatype):
  invalid stream и no-more-types — разные ошибки.
- [ReadSample](https://learn.microsoft.com/en-us/windows/win32/api/mfreadwrite/nf-mfreadwrite-imfsourcereader-readsample)
  и [MF_SOURCE_READER_FLAG](https://learn.microsoft.com/en-us/windows/win32/api/mfreadwrite/ne-mfreadwrite-mf_source_reader_flag):
  NULL sample не означает EOF; flags/typechanges/errors и действительный EOS
  проверяются отдельно. Наличие ERROR запрещает продолжать работу reader.

Минимальный подход остаётся native MF: документированная конфигурация,
фактический PCM и EOS, без собственного production AAC/container parser.
Если native результаты противоречат этим условиям, SOURCE остаётся NO-GO;
ослаблять AAC-LC, допуск длительности или protected границы ради зелёного теста нельзя.
